"""
Controlador de Arraste e Redimensionamento de Janela para SM0 (Windows).
Permite mover e redimensionar a janela do espelhamento (mesmo no modo sem bordas):
- Ctrl + Botão Esquerdo do Mouse: Mover janela livremente pela tela.
- Ctrl + Botão Direito do Mouse: Redimensionar proporcionalmente (arrastando para cima ou para baixo).
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import Optional, Callable
import subprocess

user32 = ctypes.windll.user32

# Constantes Win32
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
VK_CONTROL = 0x11
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]

def find_hwnd_by_pid(pid: int) -> Optional[int]:
    """Encontra a HWND da janela principal de um processo dado seu PID."""
    target_hwnd = None
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_windows_callback(hwnd, lparam):
        nonlocal target_hwnd
        if not user32.IsWindowVisible(hwnd):
            return True
        lpdw_process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
        if lpdw_process_id.value == pid:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                target_hwnd = hwnd
                return False
            elif not target_hwnd:
                target_hwnd = hwnd
        return True

    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    return target_hwnd


class WindowDragResizeController:
    def __init__(self, get_process_fn: Callable[[], Optional[subprocess.Popen]]):
        self.get_process_fn = get_process_fn
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia o monitoramento em segundo plano."""
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self):
        """Para o monitoramento."""
        self.stop_event.set()

    def _worker(self):
        is_dragging = False
        drag_start_cursor = (0, 0)
        drag_start_win_pos = (0, 0)

        is_resizing = False
        resize_start_cursor = (0, 0)
        resize_start_w = 0
        resize_start_h = 0
        resize_aspect_ratio = 1.0
        cached_hwnd = None
        last_pid = None

        while not self.stop_event.is_set():
            time.sleep(0.012)  # ~80Hz para movimento fluido

            proc = self.get_process_fn()
            if not proc or proc.poll() is not None:
                is_dragging = False
                is_resizing = False
                cached_hwnd = None
                time.sleep(0.1)
                continue

            current_pid = proc.pid
            if cached_hwnd is None or last_pid != current_pid or not user32.IsWindow(cached_hwnd):
                cached_hwnd = find_hwnd_by_pid(current_pid)
                last_pid = current_pid
                if not cached_hwnd:
                    time.sleep(0.1)
                    continue

            # Verificar teclas e botões do mouse
            ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
            lbutton_down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            rbutton_down = bool(user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000)

            # Se Ctrl não estiver pressionado, interromper qualquer arraste/redimensionamento
            if not ctrl_down:
                is_dragging = False
                is_resizing = False
                continue

            # Coordenadas do cursor
            cur_pt = POINT()
            user32.GetCursorPos(ctypes.byref(cur_pt))

            # Retângulo da janela do scrcpy
            win_rect = RECT()
            if not user32.GetWindowRect(cached_hwnd, ctypes.byref(win_rect)):
                continue

            win_w = win_rect.right - win_rect.left
            win_h = win_rect.bottom - win_rect.top
            cursor_inside = (win_rect.left <= cur_pt.x <= win_rect.right and win_rect.top <= cur_pt.y <= win_rect.bottom)

            # === 1. MOVER JANELA: CTRL + BOTÃO ESQUERDO ===
            if lbutton_down:
                if not is_dragging:
                    if cursor_inside:
                        is_dragging = True
                        drag_start_cursor = (cur_pt.x, cur_pt.y)
                        drag_start_win_pos = (win_rect.left, win_rect.top)
                else:
                    dx = cur_pt.x - drag_start_cursor[0]
                    dy = cur_pt.y - drag_start_cursor[1]
                    new_x = drag_start_win_pos[0] + dx
                    new_y = drag_start_win_pos[1] + dy
                    user32.SetWindowPos(
                        cached_hwnd,
                        0,
                        new_x,
                        new_y,
                        0,
                        0,
                        SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
                    )
            else:
                is_dragging = False

            # === 2. REDIMENSIONAR JANELA: CTRL + BOTÃO DIREITO ===
            if rbutton_down:
                if not is_resizing:
                    if cursor_inside:
                        is_resizing = True
                        resize_start_cursor = (cur_pt.x, cur_pt.y)
                        resize_start_w = win_w
                        resize_start_h = win_h
                        resize_aspect_ratio = resize_start_w / max(1, resize_start_h)
                else:
                    dy = cur_pt.y - resize_start_cursor[1]
                    # Arrastar para baixo aumenta, para cima diminui
                    new_h = int(resize_start_h + dy * 1.5)
                    new_h = max(240, min(2560, new_h))
                    new_w = int(new_h * resize_aspect_ratio)
                    user32.SetWindowPos(
                        cached_hwnd,
                        0,
                        win_rect.left,
                        win_rect.top,
                        new_w,
                        new_h,
                        SWP_NOZORDER | SWP_NOACTIVATE,
                    )
            else:
                is_resizing = False
