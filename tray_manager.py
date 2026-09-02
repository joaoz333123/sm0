"""
Gerenciador da Bandeja do Sistema (System Tray) para SM0 no Windows.
Permite minimizar a interface gráfica para a área de notificação da barra de tarefas
e restaurá-la com um clique ou através do menu de contexto.
"""

import threading
import time
from typing import Callable, Optional
from PIL import Image
import pystray


class TrayManager:
    def __init__(
        self,
        icon_path: str = "scrcpy/icon.png",
        on_restore: Optional[Callable[[], None]] = None,
        on_reopen_mirror: Optional[Callable[[], None]] = None,
        on_stop_mirror: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        self.icon_path = icon_path
        self.on_restore = on_restore or (lambda: None)
        self.on_reopen_mirror = on_reopen_mirror or (lambda: None)
        self.on_stop_mirror = on_stop_mirror or (lambda: None)
        self.on_exit = on_exit or (lambda: None)

        self.icon: Optional[pystray.Icon] = None
        self.thread: Optional[threading.Thread] = None

    def _create_image(self):
        try:
            return Image.open(self.icon_path)
        except Exception:
            # Fallback caso a imagem falhe
            return Image.new("RGBA", (64, 64), color=(31, 111, 235, 255))

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                "📱 Mostrar Painel SM0",
                lambda icon, item: self.on_restore(),
                default=True  # Ação padrão no duplo clique / clique
            ),
            pystray.MenuItem(
                "📺 Reabrir Espelhamento",
                lambda icon, item: self.on_reopen_mirror()
            ),
            pystray.MenuItem(
                "⏹ Encerrar Espelhamento",
                lambda icon, item: self.on_stop_mirror()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "❌ Sair do SM0",
                lambda icon, item: self.on_exit()
            ),
        )

    def start(self):
        """Inicia o ícone da bandeja em uma thread dedicada em segundo plano."""
        if self.icon:
            return

        def _run():
            try:
                img = self._create_image()
                menu = self._build_menu()
                self.icon = pystray.Icon("SM0", img, "SM0 - Espelhamento Android", menu)
                self.icon.run()
            except Exception as e:
                print(f"Erro no System Tray: {e}")

        self.thread = threading.Thread(target=_run, daemon=True)
        self.thread.start()

    def notify(self, title: str, message: str):
        """Dispara uma notificação nativa do Windows a partir do ícone da bandeja."""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def stop(self):
        """Remove o ícone da bandeja do sistema."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
