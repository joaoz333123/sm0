import customtkinter as ctk
import json
import subprocess
import threading
import time
import os
import re
from pathlib import Path
from PIL import Image
from adb_qr_pair import (
    ADBQRPairer,
    get_active_adb_devices,
    get_mdns_connect_services,
    quick_connect_adb
)

# Configuração do tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SM0App:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("SM0 - Utilitário de Espelhamento Android")
        self.root.geometry("680x860")
        self.root.resizable(True, True)
        self.root.minsize(560, 720)
        
        # Variáveis de controle
        self.scrcpy_process = None
        self.is_connected = False
        self.reconnect_thread = None
        self.should_reconnect = False
        self.qr_pairer = None
        self.qr_image_tk = None
        
        # Carregar configurações
        self.settings_file = Path("settings.json")
        self.load_settings()
        
        # Criar interface
        self.create_widgets()
        
        # Configurar fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Atualizar status dos dispositivos na inicialização
        self.root.after(300, self.refresh_devices_async)
        
        # Iniciar autodescoberta e QR Code automaticamente
        self.root.after(200, self.start_auto_discovery_and_qr)
        
    def load_settings(self):
        """Carrega as configurações salvas ou usa padrões"""
        default_settings = {
            "resolution": "Original",
            "fps": "60",
            "bitrate": "12",
            "enable_audio": True,
            "turn_off_screen": False,
            "stay_awake": True,
            "force_desktop": False,
            "auto_mirror_on_connect": True,
            "last_ip": "192.168.3.83",
            "last_pair_port": "",
            "last_pair_code": "",
            "last_connect_port": "38171"
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                for key, value in default_settings.items():
                    if key not in self.settings:
                        self.settings[key] = value
            except Exception:
                self.settings = default_settings
        else:
            self.settings = default_settings
    
    def save_settings(self):
        """Salva as configurações atuais a partir dos campos da tela"""
        try:
            self.settings["resolution"] = self.resolution_var.get()
            self.settings["fps"] = self.fps_var.get()
            self.settings["bitrate"] = self.bitrate_entry.get().strip()
            self.settings["enable_audio"] = self.audio_var.get()
            self.settings["turn_off_screen"] = self.turn_off_var.get()
            self.settings["stay_awake"] = self.stay_awake_var.get()
            self.settings["force_desktop"] = self.desktop_var.get()
            self.settings["auto_mirror_on_connect"] = self.auto_mirror_var.get()
            self.settings["last_ip"] = self.ip_entry.get().strip()
            self.settings["last_pair_port"] = self.pair_port_entry.get().strip()
            self.settings["last_pair_code"] = self.pair_code_entry.get().strip()
            self.settings["last_connect_port"] = self.connect_port_entry.get().strip()
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")
    
    def create_widgets(self):
        """Cria todos os widgets da interface"""
        # Header principal
        title_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        title_frame.pack(pady=(12, 4), fill="x", padx=20)
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="📱 SM0 - Espelhamento Android",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(side="left")
        
        btn_header_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        btn_header_frame.pack(side="right")
        
        # Botão Resetar ADB
        reset_btn = ctk.CTkButton(
            btn_header_frame,
            text="🧹 Resetar ADB",
            width=100,
            fg_color="#444C56",
            hover_color="#57606A",
            command=self.reset_adb
        )
        reset_btn.pack(side="right", padx=(5, 0))
        
        # Botão Atualizar
        refresh_btn = ctk.CTkButton(
            btn_header_frame,
            text="🔄 Detectar",
            width=90,
            command=self.refresh_devices_async
        )
        refresh_btn.pack(side="right")
        
        # Scrollable frame principal
        scrollable_frame = ctk.CTkScrollableFrame(self.root)
        scrollable_frame.pack(padx=15, pady=4, fill="both", expand=True)
        
        # === SEÇÃO 1: STATUS DO ADB ===
        dev_frame = ctk.CTkFrame(scrollable_frame)
        dev_frame.pack(padx=10, pady=5, fill="x")
        
        dev_title = ctk.CTkLabel(
            dev_frame, 
            text="Dispositivos Ativos no ADB:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        dev_title.pack(anchor="w", padx=10, pady=(6, 2))
        
        self.device_status_label = ctk.CTkLabel(
            dev_frame,
            text="Procurando dispositivos...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.device_status_label.pack(anchor="w", padx=10, pady=(0, 6))

        # === SEÇÃO 2: PAREAMENTO POR QR CODE E RECONEXÃO AUTOMÁTICA ===
        self.qr_box = ctk.CTkFrame(scrollable_frame, fg_color="#1E2228", border_width=1, border_color="#30363D")
        self.qr_box.pack(padx=10, pady=6, fill="x")

        qr_header_frame = ctk.CTkFrame(self.qr_box, fg_color="transparent")
        qr_header_frame.pack(padx=10, pady=(8, 4), fill="x")

        qr_title = ctk.CTkLabel(
            qr_header_frame,
            text="📷 Conexão Automática & Pareamento QR Code",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#58A6FF"
        )
        qr_title.pack(side="left")

        # Botão Regenerar QR
        self.btn_new_qr = ctk.CTkButton(
            qr_header_frame,
            text="🔄 Novo QR",
            width=80,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#30363D",
            hover_color="#484F58",
            command=lambda: self.start_qr_auto_pairing(force_new=True)
        )
        self.btn_new_qr.pack(side="right")

        # Área de exibição do QR Code e instruções
        qr_content_frame = ctk.CTkFrame(self.qr_box, fg_color="transparent")
        qr_content_frame.pack(padx=10, pady=(2, 10), fill="x")

        # Container do QR Code
        self.qr_label = ctk.CTkLabel(qr_content_frame, text="Gerando QR Code...", width=190, height=190)
        self.qr_label.pack(side="left", padx=(10, 15), pady=5)

        # Instruções e status do QR Code
        qr_info_frame = ctk.CTkFrame(qr_content_frame, fg_color="transparent")
        qr_info_frame.pack(side="left", fill="both", expand=True, pady=5)

        instrucoes_texto = (
            "⚡ Se o celular já foi pareado, o SM0 conecta e espelha sozinho!\n\n"
            "📱 Para parear um novo celular pela primeira vez:\n"
            "1. No celular, abra Configurações > Opções do desenvolvedor.\n"
            "2. Ative Depuração sem fio.\n"
            "3. Toque em 'Parear dispositivo com código QR'.\n"
            "4. Aponte a câmera para o QR Code ao lado.\n"
            "👉 O espelhamento iniciará automaticamente!"
        )
        self.qr_instructions_label = ctk.CTkLabel(
            qr_info_frame,
            text=instrucoes_texto,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            text_color="#C9D1D9"
        )
        self.qr_instructions_label.pack(anchor="w", pady=(0, 6))

        self.qr_status_badge = ctk.CTkLabel(
            qr_info_frame,
            text="⏳ Buscando celular pareado na rede Wi-Fi...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#F0883E",
            anchor="w"
        )
        self.qr_status_badge.pack(anchor="w", pady=(2, 0))

        # === SEÇÃO 3: CONEXÃO MANUAL (IP E PORTAS) ===
        connection_frame = ctk.CTkFrame(scrollable_frame)
        connection_frame.pack(padx=10, pady=6, fill="x")
        
        connection_title = ctk.CTkLabel(
            connection_frame, 
            text="Conexão Manual por IP (Opcional)",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        connection_title.pack(anchor="w", padx=10, pady=(8, 4))
        
        # IP do Celular
        ip_frame = ctk.CTkFrame(connection_frame, fg_color="transparent")
        ip_frame.pack(padx=10, pady=3, fill="x")
        ctk.CTkLabel(ip_frame, text="IP do Celular:", width=160, anchor="w").pack(side="left")
        self.ip_entry = ctk.CTkEntry(ip_frame, placeholder_text="Ex: 192.168.3.83")
        self.ip_entry.pack(side="right", fill="x", expand=True)
        self.ip_entry.insert(0, self.settings.get("last_ip", "192.168.3.83"))
        
        # Porta de Conexão Principal
        connect_port_frame = ctk.CTkFrame(connection_frame, fg_color="transparent")
        connect_port_frame.pack(padx=10, pady=3, fill="x")
        ctk.CTkLabel(connect_port_frame, text="Porta Conexão (Principal):", width=160, anchor="w").pack(side="left")
        self.connect_port_entry = ctk.CTkEntry(connect_port_frame, placeholder_text="Ex: 38171")
        self.connect_port_entry.pack(side="right", fill="x", expand=True)
        if self.settings.get("last_connect_port"):
            self.connect_port_entry.insert(0, str(self.settings["last_connect_port"]))
            
        # Pareamento com PIN Manual
        pair_box = ctk.CTkFrame(connection_frame)
        pair_box.pack(padx=10, pady=6, fill="x")
        
        pair_hint = ctk.CTkLabel(
            pair_box,
            text="Pareamento com PIN (Deixe em branco se já pareou por QR Code):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#8B949E"
        )
        pair_hint.pack(anchor="w", padx=8, pady=(4, 2))
        
        pair_inputs_frame = ctk.CTkFrame(pair_box, fg_color="transparent")
        pair_inputs_frame.pack(padx=5, pady=3, fill="x")
        
        # Porta de Pareamento
        ctk.CTkLabel(pair_inputs_frame, text="Porta Parear:").pack(side="left", padx=4)
        self.pair_port_entry = ctk.CTkEntry(pair_inputs_frame, placeholder_text="Ex: 33179", width=95)
        self.pair_port_entry.pack(side="left", padx=4)
        if self.settings.get("last_pair_port"):
            self.pair_port_entry.insert(0, str(self.settings["last_pair_port"]))
            
        # Código de Pareamento
        ctk.CTkLabel(pair_inputs_frame, text="PIN:").pack(side="left", padx=(10, 4))
        self.pair_code_entry = ctk.CTkEntry(pair_inputs_frame, placeholder_text="Ex: 759166", width=95)
        self.pair_code_entry.pack(side="left", padx=4)
        if self.settings.get("last_pair_code"):
            self.pair_code_entry.insert(0, str(self.settings["last_pair_code"]))
            
        # === SEÇÃO 4: OPÇÕES DE VÍDEO E PERFORMANCE ===
        config_frame = ctk.CTkFrame(scrollable_frame)
        config_frame.pack(padx=10, pady=6, fill="x")
        
        config_title = ctk.CTkLabel(
            config_frame, 
            text="Configurações de Transmissão",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        config_title.pack(anchor="w", padx=10, pady=(8, 5))
        
        grid_row1 = ctk.CTkFrame(config_frame, fg_color="transparent")
        grid_row1.pack(padx=10, pady=3, fill="x")
        
        # Resolução
        ctk.CTkLabel(grid_row1, text="Resolução:").pack(side="left", padx=(0, 5))
        self.resolution_var = ctk.StringVar(value=self.settings.get("resolution", "Original"))
        self.resolution_menu = ctk.CTkOptionMenu(
            grid_row1,
            values=["720p", "1080p", "1440p", "Original"],
            variable=self.resolution_var,
            width=100
        )
        self.resolution_menu.pack(side="left", padx=(0, 20))
        
        # FPS
        ctk.CTkLabel(grid_row1, text="FPS:").pack(side="left", padx=(0, 5))
        self.fps_var = ctk.StringVar(value=self.settings.get("fps", "60"))
        self.fps_menu = ctk.CTkOptionMenu(
            grid_row1,
            values=["30", "60", "Max"],
            variable=self.fps_var,
            width=80
        )
        self.fps_menu.pack(side="left", padx=(0, 20))
        
        # Bitrate
        ctk.CTkLabel(grid_row1, text="Bitrate (Mbps):").pack(side="left", padx=(0, 5))
        self.bitrate_entry = ctk.CTkEntry(grid_row1, placeholder_text="12", width=60)
        self.bitrate_entry.pack(side="left")
        self.bitrate_entry.insert(0, str(self.settings.get("bitrate", "12")))
        
        # Toggles adicionais
        toggles_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        toggles_frame.pack(padx=10, pady=5, fill="x")
        
        self.auto_mirror_var = ctk.BooleanVar(value=self.settings.get("auto_mirror_on_connect", True))
        self.auto_mirror_checkbox = ctk.CTkCheckBox(
            toggles_frame,
            text="Auto-espelhar",
            variable=self.auto_mirror_var
        )
        self.auto_mirror_checkbox.pack(side="left", padx=(0, 15))

        self.audio_var = ctk.BooleanVar(value=self.settings.get("enable_audio", True))
        self.audio_checkbox = ctk.CTkCheckBox(
            toggles_frame, 
            text="Áudio Nativo",
            variable=self.audio_var
        )
        self.audio_checkbox.pack(side="left", padx=(0, 15))
        
        self.turn_off_var = ctk.BooleanVar(value=self.settings.get("turn_off_screen", False))
        self.turn_off_checkbox = ctk.CTkCheckBox(
            toggles_frame, 
            text="Apagar tela celular",
            variable=self.turn_off_var
        )
        self.turn_off_checkbox.pack(side="left", padx=(0, 15))
        
        self.stay_awake_var = ctk.BooleanVar(value=self.settings.get("stay_awake", True))
        self.stay_awake_checkbox = ctk.CTkCheckBox(
            toggles_frame, 
            text="Manter ativo",
            variable=self.stay_awake_var
        )
        self.stay_awake_checkbox.pack(side="left", padx=(0, 15))
        
        self.desktop_var = ctk.BooleanVar(value=self.settings.get("force_desktop", False))
        self.desktop_checkbox = ctk.CTkCheckBox(
            toggles_frame, 
            text="Modo DeX",
            variable=self.desktop_var
        )
        self.desktop_checkbox.pack(side="left")
        
        # === SEÇÃO 5: BOTÕES DE AÇÃO E LOG ===
        control_frame = ctk.CTkFrame(self.root)
        control_frame.pack(padx=15, pady=(4, 12), fill="x")
        
        button_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_frame.pack(padx=10, pady=8, fill="x")
        
        self.connect_button = ctk.CTkButton(
            button_frame,
            text="▶ Conectar e Espelhar",
            command=self.connect_device,
            fg_color="#2EA043",
            hover_color="#238636",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=38
        )
        self.connect_button.pack(side="left", padx=5, fill="x", expand=True)
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹ Desconectar",
            command=self.stop_connection,
            fg_color="#DA3633",
            hover_color="#B62324",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            height=38
        )
        self.stop_button.pack(side="right", padx=5, fill="x", expand=True)
        
        # Status Box
        status_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        status_frame.pack(padx=10, pady=(0, 8), fill="both", expand=True)
        
        ctk.CTkLabel(status_frame, text="Log de Status:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        
        self.status_text = ctk.CTkTextbox(status_frame, height=80, font=ctk.CTkFont(family="Consolas", size=11))
        self.status_text.pack(fill="both", expand=True)
        self.status_text.insert("1.0", "Iniciando SM0. Procurando celular pareado na rede...")
        self.status_text.configure(state="disabled")
    
    def start_auto_discovery_and_qr(self):
        """Inicia a escuta por mDNS e rotina em background para reconexão imediata."""
        self.start_qr_auto_pairing(force_new=False)
        threading.Thread(target=self._auto_reconnect_worker, daemon=True).start()

    def start_qr_auto_pairing(self, force_new: bool = False):
        """Inicializa e exibe o QR Code na interface e escuta mDNS."""
        try:
            if self.qr_pairer:
                self.qr_pairer.stop()

            self.qr_pairer = ADBQRPairer(
                adb_path="scrcpy/adb.exe",
                on_status=self._on_qr_status_update,
                on_success=self._on_qr_success,
                on_error=self._on_qr_error
            )
            
            # Gerar imagem do QR Code
            pil_image = self.qr_pairer.get_qr_image(size=180)
            self.qr_image_tk = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(180, 180))
            self.qr_label.configure(image=self.qr_image_tk, text="")
            
            self.qr_status_badge.configure(
                text="⏳ Procurando celular pareado na rede Wi-Fi...",
                text_color="#F0883E"
            )
            
            # Iniciar escuta mDNS (pareamento + conexão automática)
            self.qr_pairer.start_listening(listen_for_autoconnect=True)
        except Exception as e:
            self.qr_status_badge.configure(text=f"Erro no serviço de pareamento: {e}", text_color="#F85149")

    def _auto_reconnect_worker(self):
        """Verifica imediatamente dispositivos já pareados via active devices, mDNS cache e último IP."""
        time.sleep(0.3)
        if self.is_connected or (self.scrcpy_process and self.scrcpy_process.poll() is None):
            return

        # 1. Checar se já há dispositivo autorizado em adb devices
        active_devices = self.get_adb_devices()
        if active_devices:
            best_device = active_devices[0]
            target_serial = best_device["serial"]
            model = best_device["model"]

            def _notify_active():
                self.qr_status_badge.configure(
                    text=f"🟢 Aparelho pareado detectado ({model})!",
                    text_color="#3FB950"
                )
                self.update_status(f"🎉 Celular {model} já está pareado e pronto ({target_serial})!")
                if ":" in target_serial and not target_serial.startswith("adb-"):
                    parts = target_serial.split(":")
                    self.ip_entry.delete(0, "end")
                    self.ip_entry.insert(0, parts[0])
                    self.connect_port_entry.delete(0, "end")
                    self.connect_port_entry.insert(0, parts[1])
                self.refresh_devices_async()

                if self.auto_mirror_var.get() and not self.is_connected:
                    threading.Thread(target=self.start_mirroring, args=(target_serial,), daemon=True).start()

            self.root.after(0, _notify_active)
            return

        # 2. Consultar 'adb mdns services' para encontrar celulares com depuração ativa
        mdns_services = get_mdns_connect_services("scrcpy/adb.exe")
        for s in mdns_services:
            endpoint = s["endpoint"]
            self._on_qr_status_update(f"⚡ Celular pareado encontrado em {endpoint}! Conectando...")
            if quick_connect_adb("scrcpy/adb.exe", endpoint, timeout=4):
                time.sleep(0.5)
                devs = self.get_adb_devices()
                target = devs[0]["serial"] if devs else endpoint
                model = devs[0]["model"] if devs else "Android"

                def _notify_mdns(ip=s["ip"], port=s["port"], target_serial=target, dev_model=model):
                    self.ip_entry.delete(0, "end")
                    self.ip_entry.insert(0, ip)
                    self.connect_port_entry.delete(0, "end")
                    self.connect_port_entry.insert(0, str(port))
                    self.save_settings()
                    self.qr_status_badge.configure(
                        text=f"🟢 Conectado automaticamente ({dev_model})!",
                        text_color="#3FB950"
                    )
                    self.update_status(f"🎉 Celular {dev_model} reconectado automaticamente em {target_serial}!")
                    self.refresh_devices_async()
                    if self.auto_mirror_var.get() and not self.is_connected:
                        threading.Thread(target=self.start_mirroring, args=(target_serial,), daemon=True).start()

                self.root.after(0, _notify_mdns)
                return

        # 3. Tentar reconexão rápida no último IP e porta salvos
        last_ip = self.settings.get("last_ip", "").strip()
        last_port = str(self.settings.get("last_connect_port", "")).strip()
        if last_ip and last_port:
            endpoint = f"{last_ip}:{last_port}"
            self._on_qr_status_update(f"Tentando reconectar ao último endereço ({endpoint})...")
            if quick_connect_adb("scrcpy/adb.exe", endpoint, timeout=3):
                time.sleep(0.5)
                devs = self.get_adb_devices()
                target = devs[0]["serial"] if devs else endpoint
                model = devs[0]["model"] if devs else "Android"

                def _notify_last(ip=last_ip, port=last_port, target_serial=target, dev_model=model):
                    self.qr_status_badge.configure(
                        text=f"🟢 Reconectado com sucesso ({dev_model})!",
                        text_color="#3FB950"
                    )
                    self.update_status(f"🎉 Reconectado ao último endereço ({target_serial})!")
                    self.refresh_devices_async()
                    if self.auto_mirror_var.get() and not self.is_connected:
                        threading.Thread(target=self.start_mirroring, args=(target_serial,), daemon=True).start()

                self.root.after(0, _notify_last)
                return

        self._on_qr_status_update("🔍 Aguardando celular pareado na rede ou leitura do QR Code...")

    def _on_qr_status_update(self, message: str):
        """Callback thread-safe para atualizar o status do QR Code na GUI."""
        def _update():
            self.qr_status_badge.configure(text=message, text_color="#58A6FF")
            self.update_status(message)
        self.root.after(0, _update)

    def _on_qr_success(self, ip: str, port: int, serial: str):
        """Callback thread-safe quando o pareamento e conexão são concluídos com sucesso."""
        def _success():
            self.qr_status_badge.configure(
                text="✅ Conectado! Iniciando espelhamento...",
                text_color="#3FB950"
            )
            self.update_status(f"🎉 Aparelho conectado com sucesso em {serial or ip}!")
            
            # Atualizar campos na UI e limpar campos de pareamento antigo
            if ip:
                self.ip_entry.delete(0, "end")
                self.ip_entry.insert(0, ip)
            
            if port:
                self.connect_port_entry.delete(0, "end")
                self.connect_port_entry.insert(0, str(port))
            
            self.pair_port_entry.delete(0, "end")
            self.pair_code_entry.delete(0, "end")
            
            self.save_settings()
            self.refresh_devices_async()
            
            # INICIAR ESPELHAMENTO AUTOMATICAMENTE!
            target = serial if serial else (f"{ip}:{port}" if port else ip)
            if self.auto_mirror_var.get() and not self.is_connected:
                threading.Thread(target=self.start_mirroring, args=(target,), daemon=True).start()
            
        self.root.after(0, _success)

    def _on_qr_error(self, err_msg: str):
        """Callback thread-safe para reportar erros no fluxo do QR Code."""
        def _error():
            self.qr_status_badge.configure(text=f"⚠️ {err_msg}", text_color="#F85149")
            self.update_status(f"Erro: {err_msg}")
        self.root.after(0, _error)

    def update_status(self, message):
        """Atualiza a mensagem de status no painel"""
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", f"[{time.strftime('%H:%M:%S')}] {message}")
        self.status_text.configure(state="disabled")
        self.root.update_idletasks()
    
    def get_adb_devices(self):
        """Retorna lista de dispositivos ADB disponíveis, preferindo endpoints diretos."""
        raw_devices = get_active_adb_devices("scrcpy/adb.exe")
        # Se houver dispositivos IP:porta e também nome mDNS longo, preferir IP:porta
        sorted_devices = sorted(
            raw_devices,
            key=lambda d: (1 if d["serial"].startswith("adb-") and "_adb-tls-connect" in d["serial"] else 0)
        )
        return sorted_devices
            
    def refresh_devices_async(self):
        """Atualiza a lista de dispositivos no label"""
        def _task():
            devices = self.get_adb_devices()
            if devices:
                dev_names = ", ".join([f"{d['model']} ({d['serial']})" for d in devices])
                self.device_status_label.configure(
                    text=f"🟢 Conectado: {dev_names}",
                    text_color="#3FB950"
                )
                if not self.is_connected:
                    self.connect_button.configure(state="normal", text="▶ Iniciar Espelhamento (Dispositivo Pronto)")
            else:
                self.device_status_label.configure(
                    text="⚪ Nenhum dispositivo conectado ao ADB.",
                    text_color="gray"
                )
                if not self.is_connected:
                    self.connect_button.configure(state="normal", text="▶ Conectar e Espelhar")
        threading.Thread(target=_task, daemon=True).start()

    def reset_adb(self):
        """Limpa conexões travadas no ADB"""
        def _reset_task():
            self.update_status("Resetando conexões do ADB...")
            try:
                subprocess.run(["scrcpy/adb.exe", "disconnect"], capture_output=True, timeout=5)
                subprocess.run(["scrcpy/adb.exe", "kill-server"], capture_output=True, timeout=5)
                subprocess.run(["scrcpy/adb.exe", "start-server"], capture_output=True, timeout=5)
                self.update_status("ADB reiniciado com sucesso!")
                self.refresh_devices_async()
                # Reiniciar descoberta e escuta
                self.root.after(500, self.start_auto_discovery_and_qr)
            except Exception as e:
                self.update_status(f"Erro ao reiniciar ADB: {e}")
        threading.Thread(target=_reset_task, daemon=True).start()

    def get_scrcpy_command(self, serial):
        """Constrói o comando scrcpy baseado nas configurações e no serial selecionado"""
        base_cmd = ["scrcpy/scrcpy.exe", "-s", serial]
        
        # Resolução
        resolution = self.resolution_var.get()
        if resolution == "720p":
            base_cmd.extend(["--max-size", "720"])
        elif resolution == "1080p":
            base_cmd.extend(["--max-size", "1080"])
        elif resolution == "1440p":
            base_cmd.extend(["--max-size", "1440"])
        
        # FPS
        fps = self.fps_var.get()
        if fps != "Max":
            base_cmd.extend(["--max-fps", fps])
        
        # Bitrate
        bitrate = self.bitrate_entry.get().strip()
        if bitrate:
            base_cmd.extend(["--video-bit-rate", f"{bitrate}M"])
            
        # Áudio nativo
        if not self.audio_var.get():
            base_cmd.append("--no-audio")
            
        # Opções de tela
        if self.turn_off_var.get():
            base_cmd.append("--turn-screen-off")
        if self.stay_awake_var.get():
            base_cmd.append("--stay-awake")
        
        return base_cmd
    
    def connect_device(self):
        """Inicia o processo manual de conexão usando os dados preenchidos"""
        self.connect_button.configure(state="disabled", text="▶ Conectando...")
        self.save_settings()
        threading.Thread(target=self._connect_thread, daemon=True).start()
    
    def _connect_thread(self):
        """Thread manual que executa conexão/espelhamento com os dados da UI"""
        try:
            ip = self.ip_entry.get().strip()
            connect_port = self.connect_port_entry.get().strip()
            pair_port = self.pair_port_entry.get().strip()
            pair_code = self.pair_code_entry.get().strip()
            
            # Verificar se já temos dispositivos conectados no ADB
            devices = self.get_adb_devices()
            target_serial = None
            
            # Se já há algum dispositivo conectado com este IP ou serial, usar direto
            for d in devices:
                if ip and (ip in d["serial"]):
                    target_serial = d["serial"]
                    break
            
            if not target_serial and not ip and devices:
                target_serial = devices[0]["serial"]
                
            if not target_serial:
                if not ip:
                    self.update_status("Erro: Aponte a câmera para o QR Code ou digite o IP do celular!")
                    self.connect_button.configure(state="normal", text="▶ Conectar e Espelhar")
                    return

                # Se o usuário preencheu explicitamente campos de pareamento com PIN manual
                if pair_port and pair_code:
                    self.update_status(f"Pareando com {ip}:{pair_port}...")
                    pair_cmd = ["scrcpy/adb.exe", "pair", f"{ip}:{pair_port}", pair_code]
                    pair_res = subprocess.run(
                        pair_cmd,
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    if pair_res.returncode != 0 and "successfully paired" not in (pair_res.stdout + pair_res.stderr).lower():
                        err_msg = pair_res.stderr.strip() or pair_res.stdout.strip()
                        self.update_status(f"Erro no pareamento manual: {err_msg}")
                        self.connect_button.configure(state="normal", text="▶ Conectar e Espelhar")
                        return
                    self.update_status("Pareamento manual realizado!")
                
                # Conectar à porta informada
                target_endpoint = f"{ip}:{connect_port}" if connect_port else ip
                self.update_status(f"Conectando ao celular em {target_endpoint}...")
                
                conn_res = subprocess.run(
                    ["scrcpy/adb.exe", "connect", target_endpoint],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                conn_output = (conn_res.stdout + conn_res.stderr).lower()
                time.sleep(1)
                
                devices = self.get_adb_devices()
                matching_dev = [d for d in devices if ip in d["serial"] or target_endpoint in d["serial"]]
                if matching_dev:
                    target_serial = matching_dev[0]["serial"]
                elif "connected" in conn_output or "already" in conn_output:
                    target_serial = target_endpoint
                else:
                    self.update_status(f"Erro ao conectar em {target_endpoint}: {conn_res.stdout.strip() or conn_res.stderr.strip()}")
                    self.connect_button.configure(state="normal", text="▶ Conectar e Espelhar")
                    return

            self.start_mirroring(target_serial)
                
        except Exception as e:
            self.update_status(f"Erro inesperado: {str(e)}")
            self.connect_button.configure(state="normal", text="▶ Conectar e Espelhar")

    def start_mirroring(self, target_serial: str):
        """Inicia a sessão de espelhamento com o scrcpy para o serial indicado."""
        try:
            self.update_status(f"Conectado a {target_serial}! Abrindo espelhamento...")
            
            # 1. Modo desktop se habilitado
            if self.desktop_var.get():
                try:
                    desktop_commands = [
                        ["scrcpy/adb.exe", "-s", target_serial, "shell", "settings", "put", "global", "force_desktop_mode_on_external_displays", "1"],
                        ["scrcpy/adb.exe", "-s", target_serial, "shell", "settings", "put", "global", "force_resizable_activities", "1"],
                        ["scrcpy/adb.exe", "-s", target_serial, "shell", "settings", "put", "global", "enable_freeform_support", "1"]
                    ]
                    for cmd in desktop_commands:
                        subprocess.run(cmd, capture_output=True, timeout=5)
                except Exception:
                    pass

            # 2. Iniciar scrcpy
            scrcpy_cmd = self.get_scrcpy_command(serial=target_serial)
            
            # Encerrar processo scrcpy anterior se existente
            if self.scrcpy_process and self.scrcpy_process.poll() is None:
                self.scrcpy_process.terminate()
            
            self.scrcpy_process = subprocess.Popen(
                scrcpy_cmd,
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(1.2)
            
            if self.scrcpy_process.poll() is None:
                self.update_status(f"✅ Espelhamento ativo em {target_serial}!")
                self.is_connected = True
                self.should_reconnect = True
                self.connect_button.configure(state="disabled", text="▶ Espelhamento Ativo")
                self.stop_button.configure(state="normal")
                self.refresh_devices_async()
                
                # Iniciar monitoramento de encerramento
                self.reconnect_thread = threading.Thread(target=self._monitor_session, daemon=True)
                self.reconnect_thread.start()
            else:
                stdout, stderr = self.scrcpy_process.communicate()
                err = stderr.decode('utf-8', errors='ignore') if stderr else stdout.decode('utf-8', errors='ignore')
                self.update_status(f"Erro ao iniciar scrcpy: {err.strip()}")
                self.connect_button.configure(state="normal", text="▶ Conectar e Espelhar")
        except Exception as e:
            self.update_status(f"Erro ao iniciar espelhamento: {str(e)}")
            self.connect_button.configure(state="normal", text="▶ Conectar e Espelhar")
    
    def _monitor_session(self):
        """Monitora se a janela do scrcpy foi fechada pelo usuário"""
        while self.should_reconnect and self.is_connected:
            time.sleep(2)
            if self.scrcpy_process and self.scrcpy_process.poll() is not None:
                self.update_status("Janela de espelhamento fechada. Pronto para reconectar.")
                self.is_connected = False
                self.should_reconnect = False
                self.connect_button.configure(state="normal", text="▶ Iniciar Espelhamento (Dispositivo Pronto)")
                self.stop_button.configure(state="disabled")
                self.refresh_devices_async()
                break

    def stop_connection(self):
        """Encerra a sessão de espelhamento"""
        try:
            self.should_reconnect = False
            if self.scrcpy_process:
                self.scrcpy_process.terminate()
                self.scrcpy_process = None
            
            self.is_connected = False
            self.update_status("Espelhamento encerrado.")
            self.connect_button.configure(state="normal", text="▶ Iniciar Espelhamento")
            self.stop_button.configure(state="disabled")
            self.refresh_devices_async()
        except Exception as e:
            self.update_status(f"Erro ao encerrar: {str(e)}")
            
    def on_closing(self):
        """Salva configurações e limpa processos ao sair"""
        self.save_settings()
        if self.qr_pairer:
            self.qr_pairer.stop()
        if self.is_connected:
            self.stop_connection()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SM0App()
    app.run()
