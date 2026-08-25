import customtkinter as ctk
import json
import subprocess
import threading
import time
import os
import re
from pathlib import Path

# Configuração do tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SM0App:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("SM0 - Utilitário de Espelhamento Android")
        self.root.geometry("640x780")
        self.root.resizable(True, True)
        self.root.minsize(520, 650)
        
        # Variáveis de controle
        self.scrcpy_process = None
        self.is_connected = False
        self.reconnect_thread = None
        self.should_reconnect = False
        
        # Carregar configurações
        self.settings_file = Path("settings.json")
        self.load_settings()
        
        # Criar interface
        self.create_widgets()
        
        # Configurar fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Atualizar status dos dispositivos na inicialização
        self.root.after(500, self.refresh_devices_async)
        
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
        title_frame.pack(pady=(15, 5), fill="x", padx=20)
        
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
        scrollable_frame.pack(padx=15, pady=5, fill="both", expand=True)
        
        # === SEÇÃO 1: STATUS DO ADB ===
        dev_frame = ctk.CTkFrame(scrollable_frame)
        dev_frame.pack(padx=10, pady=6, fill="x")
        
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
        
        # === SEÇÃO 2: CONEXÃO COM O IP E PORTA DIGITADOS ===
        connection_frame = ctk.CTkFrame(scrollable_frame)
        connection_frame.pack(padx=10, pady=6, fill="x")
        
        connection_title = ctk.CTkLabel(
            connection_frame, 
            text="Dados de Conexão (Insira o IP e Porta do Celular)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        connection_title.pack(anchor="w", padx=10, pady=(8, 5))
        
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
            
        # Pareamento (Opcional - somente para novo pareamento)
        pair_box = ctk.CTkFrame(connection_frame)
        pair_box.pack(padx=10, pady=6, fill="x")
        
        pair_hint = ctk.CTkLabel(
            pair_box,
            text="Pareamento com PIN (Preencha somente se for parear novo aparelho):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#58A6FF"
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
        ctk.CTkLabel(pair_inputs_frame, text="PIN (6 dígitos):").pack(side="left", padx=(10, 4))
        self.pair_code_entry = ctk.CTkEntry(pair_inputs_frame, placeholder_text="Ex: 759166", width=95)
        self.pair_code_entry.pack(side="left", padx=4)
        if self.settings.get("last_pair_code"):
            self.pair_code_entry.insert(0, str(self.settings["last_pair_code"]))
            
        # === SEÇÃO 3: OPÇÕES DE VÍDEO E PERFORMANCE ===
        config_frame = ctk.CTkFrame(scrollable_frame)
        config_frame.pack(padx=10, pady=6, fill="x")
        
        config_title = ctk.CTkLabel(
            config_frame, 
            text="Configurações de Transmissão",
            font=ctk.CTkFont(size=14, weight="bold")
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
        
        # === SEÇÃO 4: BOTÕES E STATUS ===
        control_frame = ctk.CTkFrame(self.root)
        control_frame.pack(padx=15, pady=(5, 15), fill="x")
        
        button_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_frame.pack(padx=10, pady=10, fill="x")
        
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
        status_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        
        ctk.CTkLabel(status_frame, text="Log de Status:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        
        self.status_text = ctk.CTkTextbox(status_frame, height=90, font=ctk.CTkFont(family="Consolas", size=11))
        self.status_text.pack(fill="both", expand=True)
        self.status_text.insert("1.0", "Pronto. Insira o IP e a Porta de conexão do celular e clique em 'Conectar e Espelhar'.")
        self.status_text.configure(state="disabled")
    
    def update_status(self, message):
        """Atualiza a mensagem de status no painel"""
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", f"[{time.strftime('%H:%M:%S')}] {message}")
        self.status_text.configure(state="disabled")
        self.root.update_idletasks()
    
    def get_adb_devices(self):
        """Retorna lista de dispositivos ADB disponíveis"""
        try:
            result = subprocess.run(
                ["scrcpy/adb.exe", "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            devices = []
            for line in result.stdout.strip().split("\n")[1:]:
                line = line.strip()
                if line and "device" in line and not line.startswith("List"):
                    parts = line.split()
                    serial = parts[0]
                    model_match = re.search(r"model:(\S+)", line)
                    model = model_match.group(1) if model_match else "Android"
                    devices.append({"serial": serial, "model": model, "raw": line})
            return devices
        except Exception:
            return []
            
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
            else:
                self.device_status_label.configure(
                    text="⚪ Nenhum dispositivo conectado ao ADB.",
                    text_color="gray"
                )
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
        """Inicia o processo de conexão usando exatamente os dados preenchidos"""
        self.connect_button.configure(state="disabled")
        self.save_settings()
        threading.Thread(target=self._connect_thread, daemon=True).start()
    
    def _connect_thread(self):
        """Thread que executa o pareamento/conexão estritamente com os dados da UI"""
        try:
            ip = self.ip_entry.get().strip()
            connect_port = self.connect_port_entry.get().strip()
            pair_port = self.pair_port_entry.get().strip()
            pair_code = self.pair_code_entry.get().strip()
            
            if not ip:
                self.update_status("Erro: Digite o IP do celular!")
                self.connect_button.configure(state="normal")
                return

            # 1. Se o usuário forneceu dados de pareamento, executar 'adb pair'
            if pair_port and pair_code:
                self.update_status(f"Pareando com {ip}:{pair_port}...")
                pair_cmd = ["scrcpy/adb.exe", "pair", f"{ip}:{pair_port}"]
                pair_res = subprocess.run(
                    pair_cmd,
                    input=f"{pair_code}\n",
                    text=True,
                    capture_output=True,
                    timeout=20
                )
                if pair_res.returncode != 0:
                    err_msg = pair_res.stderr.strip() or pair_res.stdout.strip()
                    self.update_status(f"Erro no pareamento: {err_msg}")
                    self.connect_button.configure(state="normal")
                    return
                self.update_status("Pareamento com PIN realizado com sucesso!")
            
            # 2. Conectar à porta principal informada
            target_endpoint = f"{ip}:{connect_port}" if connect_port else ip
            self.update_status(f"Conectando ao celular em {target_endpoint}...")
            
            conn_res = subprocess.run(
                ["scrcpy/adb.exe", "connect", target_endpoint],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            conn_output = (conn_res.stdout + conn_res.stderr).lower()
            if "failed" in conn_output or "cannot connect" in conn_output or conn_res.returncode != 0:
                # Se falhar a conexão direta, checar se já há dispositivo ativo correspondente
                devices = self.get_adb_devices()
                matching_dev = [d for d in devices if ip in d["serial"] or target_endpoint in d["serial"]]
                if matching_dev:
                    target_serial = matching_dev[0]["serial"]
                    self.update_status(f"Usando conexão ativa existente: {target_serial}")
                else:
                    self.update_status(f"Erro ao conectar em {target_endpoint}: {conn_res.stdout.strip() or conn_res.stderr.strip()}")
                    self.connect_button.configure(state="normal")
                    return
            else:
                target_serial = target_endpoint
            
            self.update_status(f"Conexão ADB estabelecida com {target_serial}! Iniciando espelhamento...")
            
            # 3. Aplicar modo desktop se solicitado
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
            
            # 4. Iniciar scrcpy com o serial correto
            scrcpy_cmd = self.get_scrcpy_command(serial=target_serial)
            
            self.scrcpy_process = subprocess.Popen(
                scrcpy_cmd,
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(1.5)
            
            if self.scrcpy_process.poll() is None:
                self.update_status(f"✅ Espelhamento ativo em {target_serial}!")
                self.is_connected = True
                self.should_reconnect = True
                self.stop_button.configure(state="normal")
                self.refresh_devices_async()
                
                # Iniciar monitoramento de encerramento
                self.reconnect_thread = threading.Thread(target=self._monitor_session, daemon=True)
                self.reconnect_thread.start()
            else:
                stdout, stderr = self.scrcpy_process.communicate()
                err = stderr.decode('utf-8', errors='ignore') if stderr else stdout.decode('utf-8', errors='ignore')
                self.update_status(f"Erro ao iniciar scrcpy: {err.strip()}")
                self.connect_button.configure(state="normal")
                
        except Exception as e:
            self.update_status(f"Erro inesperado: {str(e)}")
            self.connect_button.configure(state="normal")
    
    def _monitor_session(self):
        """Monitora se a janela do scrcpy foi fechada pelo usuário"""
        while self.should_reconnect and self.is_connected:
            time.sleep(2)
            if self.scrcpy_process and self.scrcpy_process.poll() is not None:
                self.update_status("Janela de espelhamento fechada.")
                self.is_connected = False
                self.should_reconnect = False
                self.connect_button.configure(state="normal")
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
            self.connect_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.refresh_devices_async()
        except Exception as e:
            self.update_status(f"Erro ao encerrar: {str(e)}")
            
    def on_closing(self):
        """Salva configurações e limpa processos ao sair"""
        self.save_settings()
        if self.is_connected:
            self.stop_connection()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SM0App()
    app.run()
