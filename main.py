import customtkinter as ctk
import json
import subprocess
import threading
import time
import os
from pathlib import Path

# Configuração do tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SM0App:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("SM0 - Utilitário de Espelhamento Android")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        self.root.minsize(500, 600)
        
        # Variáveis de controle
        self.connection_process = None
        self.scrcpy_process = None
        self.sndcpy_process = None
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
        
    def load_settings(self):
        """Carrega as configurações salvas ou usa padrões"""
        default_settings = {
            "resolution": "720p",
            "fps": "30",
            "bitrate": "12",
            "enable_audio": True,
            "force_desktop": False,
            "last_ip": "192.168.0.3",
            "last_pair_port": "",
            "last_pair_code": "",
            "last_connect_port": ""
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                # Garantir que todas as chaves existam
                for key, value in default_settings.items():
                    if key not in self.settings:
                        self.settings[key] = value
            except:
                self.settings = default_settings
        else:
            self.settings = default_settings
    
    def save_settings(self):
        """Salva as configurações atuais"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")
    
    def create_widgets(self):
        """Cria todos os widgets da interface"""
        # Título principal
        title_label = ctk.CTkLabel(
            self.root, 
            text="SM0 - Utilitário de Espelhamento Android",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Scrollable frame principal
        scrollable_frame = ctk.CTkScrollableFrame(self.root)
        scrollable_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        # Frame principal
        main_frame = ctk.CTkFrame(scrollable_frame)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # === SEÇÃO A: CONEXÃO ===
        connection_frame = ctk.CTkFrame(main_frame)
        connection_frame.pack(padx=10, pady=10, fill="x")
        
        connection_title = ctk.CTkLabel(
            connection_frame, 
            text="Configurações de Conexão",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        connection_title.pack(pady=10)
        
        # IP do Celular
        ip_frame = ctk.CTkFrame(connection_frame)
        ip_frame.pack(padx=10, pady=5, fill="x")
        
        ip_label = ctk.CTkLabel(ip_frame, text="IP do Celular:")
        ip_label.pack(side="left", padx=10, pady=5)
        
        self.ip_entry = ctk.CTkEntry(ip_frame, placeholder_text="192.168.0.3")
        self.ip_entry.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        self.ip_entry.insert(0, self.settings["last_ip"])
        
        # Porta de Pareamento
        pair_port_frame = ctk.CTkFrame(connection_frame)
        pair_port_frame.pack(padx=10, pady=5, fill="x")
        
        pair_port_label = ctk.CTkLabel(pair_port_frame, text="Porta de Pareamento:")
        pair_port_label.pack(side="left", padx=10, pady=5)
        
        self.pair_port_entry = ctk.CTkEntry(pair_port_frame, placeholder_text="Ex: 12345")
        self.pair_port_entry.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        if self.settings["last_pair_port"]:
            self.pair_port_entry.insert(0, self.settings["last_pair_port"])
        
        # Código de Pareamento
        pair_code_frame = ctk.CTkFrame(connection_frame)
        pair_code_frame.pack(padx=10, pady=5, fill="x")
        
        pair_code_label = ctk.CTkLabel(pair_code_frame, text="Código de Pareamento:")
        pair_code_label.pack(side="left", padx=10, pady=5)
        
        self.pair_code_entry = ctk.CTkEntry(pair_code_frame, placeholder_text="Ex: 123456")
        self.pair_code_entry.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        if self.settings["last_pair_code"]:
            self.pair_code_entry.insert(0, self.settings["last_pair_code"])
        
        # Porta de Conexão
        connect_port_frame = ctk.CTkFrame(connection_frame)
        connect_port_frame.pack(padx=10, pady=5, fill="x")
        
        connect_port_label = ctk.CTkLabel(connect_port_frame, text="Porta de Conexão:")
        connect_port_label.pack(side="left", padx=10, pady=5)
        
        self.connect_port_entry = ctk.CTkEntry(connect_port_frame, placeholder_text="Ex: 12345")
        self.connect_port_entry.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        if self.settings["last_connect_port"]:
            self.connect_port_entry.insert(0, self.settings["last_connect_port"])
        
        # === SEÇÃO B: CONFIGURAÇÕES ===
        config_frame = ctk.CTkFrame(main_frame)
        config_frame.pack(padx=10, pady=10, fill="x")
        
        config_title = ctk.CTkLabel(
            config_frame, 
            text="Configurações de Vídeo",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        config_title.pack(pady=10)
        
        # Resolução
        resolution_frame = ctk.CTkFrame(config_frame)
        resolution_frame.pack(padx=10, pady=5, fill="x")
        
        resolution_label = ctk.CTkLabel(resolution_frame, text="Resolução:")
        resolution_label.pack(side="left", padx=10, pady=5)
        
        self.resolution_var = ctk.StringVar(value=self.settings["resolution"])
        self.resolution_menu = ctk.CTkOptionMenu(
            resolution_frame,
            values=["720p", "1080p", "1440p", "Original"],
            variable=self.resolution_var
        )
        self.resolution_menu.pack(side="right", padx=10, pady=5)
        
        # FPS
        fps_frame = ctk.CTkFrame(config_frame)
        fps_frame.pack(padx=10, pady=5, fill="x")
        
        fps_label = ctk.CTkLabel(fps_frame, text="FPS:")
        fps_label.pack(side="left", padx=10, pady=5)
        
        self.fps_var = ctk.StringVar(value=self.settings["fps"])
        self.fps_menu = ctk.CTkOptionMenu(
            fps_frame,
            values=["30", "60", "Max"],
            variable=self.fps_var
        )
        self.fps_menu.pack(side="right", padx=10, pady=5)
        
        # Bitrate
        bitrate_frame = ctk.CTkFrame(config_frame)
        bitrate_frame.pack(padx=10, pady=5, fill="x")
        
        bitrate_label = ctk.CTkLabel(bitrate_frame, text="Bitrate (Mbps):")
        bitrate_label.pack(side="left", padx=10, pady=5)
        
        self.bitrate_entry = ctk.CTkEntry(bitrate_frame, placeholder_text="12")
        self.bitrate_entry.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        self.bitrate_entry.insert(0, self.settings["bitrate"])
        
        # Habilitar áudio
        audio_frame = ctk.CTkFrame(config_frame)
        audio_frame.pack(padx=10, pady=5, fill="x")
        
        self.audio_var = ctk.BooleanVar(value=self.settings["enable_audio"])
        self.audio_checkbox = ctk.CTkCheckBox(
            audio_frame, 
            text="Habilitar áudio (via sndcpy)",
            variable=self.audio_var
        )
        self.audio_checkbox.pack(padx=10, pady=5)
        
        # Forçar modo desktop (experimental)
        self.desktop_var = ctk.BooleanVar(value=self.settings.get("force_desktop", False))
        self.desktop_checkbox = ctk.CTkCheckBox(
            audio_frame, 
            text="Forçar modo desktop (experimental)",
            variable=self.desktop_var
        )
        self.desktop_checkbox.pack(padx=10, pady=5)
        
        # === SEÇÃO C: CONTROLE E STATUS ===
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.pack(padx=10, pady=10, fill="x")
        
        control_title = ctk.CTkLabel(
            control_frame, 
            text="Controle e Status",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        control_title.pack(pady=10)
        
        # Botões
        button_frame = ctk.CTkFrame(control_frame)
        button_frame.pack(padx=10, pady=10, fill="x")
        
        self.connect_button = ctk.CTkButton(
            button_frame,
            text="Conectar",
            command=self.connect_device,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.connect_button.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="Parar",
            command=self.stop_connection,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_button.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        
        # Status
        status_frame = ctk.CTkFrame(control_frame)
        status_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        status_label = ctk.CTkLabel(status_frame, text="Status:")
        status_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.status_text = ctk.CTkTextbox(status_frame, height=100)
        self.status_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        self.status_text.insert("1.0", "Aguardando informações...")
        self.status_text.configure(state="disabled")
    
    def update_status(self, message):
        """Atualiza a mensagem de status"""
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", message)
        self.status_text.configure(state="disabled")
        self.root.update()
    
    def validate_connection_fields(self):
        """Valida se todos os campos de conexão foram preenchidos"""
        ip = self.ip_entry.get().strip()
        pair_port = self.pair_port_entry.get().strip()
        pair_code = self.pair_code_entry.get().strip()
        connect_port = self.connect_port_entry.get().strip()
        
        if not all([ip, pair_port, pair_code, connect_port]):
            self.update_status("Erro: Todos os campos de conexão devem ser preenchidos!")
            return False
        
        return True
    
    def get_scrcpy_command(self):
        """Constrói o comando scrcpy baseado nas configurações"""
        base_cmd = ["scrcpy/scrcpy.exe"]
        
        # Especificar dispositivo TCP/IP para evitar conflito com USB
        ip = self.ip_entry.get().strip()
        connect_port = self.connect_port_entry.get().strip()
        if ip and connect_port:
            base_cmd.extend(["-s", f"{ip}:{connect_port}"])
        
        # Resolução
        resolution = self.resolution_var.get()
        if resolution == "720p":
            base_cmd.extend(["--max-size", "720"])
        elif resolution == "1080p":
            base_cmd.extend(["--max-size", "1080"])
        elif resolution == "1440p":
            base_cmd.extend(["--max-size", "1440"])
        # "Original" não adiciona parâmetro de tamanho
        
        # FPS
        fps = self.fps_var.get()
        if fps != "Max":
            base_cmd.extend(["--max-fps", fps])
        
        # Bitrate
        bitrate = self.bitrate_entry.get().strip()
        if bitrate:
            base_cmd.extend(["--video-bit-rate", f"{bitrate}M"])
        
        return base_cmd
    
    def connect_device(self):
        """Inicia o processo de conexão"""
        if not self.validate_connection_fields():
            return
        
        # Desabilitar botão de conectar
        self.connect_button.configure(state="disabled")
        
        # Executar conexão em thread separada
        threading.Thread(target=self._connect_thread, daemon=True).start()
    
    def _connect_thread(self):
        """Thread para executar a conexão"""
        try:
            ip = self.ip_entry.get().strip()
            pair_port = self.pair_port_entry.get().strip()
            pair_code = self.pair_code_entry.get().strip()
            connect_port = self.connect_port_entry.get().strip()
            
            # Iniciar pareamento
            self.update_status("Pareando com o dispositivo...")
            pair_cmd = ["scrcpy/adb.exe", "pair", f"{ip}:{pair_port}"]
            
            try:
                result = subprocess.run(
                    pair_cmd,
                    input=f"{pair_code}\n",
                    text=True,
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    self.update_status(f"Erro no pareamento: {result.stderr}")
                    self.connect_button.configure(state="normal")
                    return
                
                self.update_status("Pareamento realizado com sucesso! Conectando...")
                
            except subprocess.TimeoutExpired:
                self.update_status("Erro: Timeout no pareamento")
                self.connect_button.configure(state="normal")
                return
            
            # Conectar ao dispositivo
            connect_cmd = ["scrcpy/adb.exe", "connect", f"{ip}:{connect_port}"]
            
            try:
                result = subprocess.run(
                    connect_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    self.update_status(f"Erro na conexão: {result.stderr}")
                    self.connect_button.configure(state="normal")
                    return
                
                self.update_status("Conexão estabelecida! Iniciando espelhamento...")
                
            except subprocess.TimeoutExpired:
                self.update_status("Erro: Timeout na conexão")
                self.connect_button.configure(state="normal")
                return
            
            # Tentar forçar modo desktop se habilitado
            if self.desktop_var.get():
                self.update_status("Conexão estabelecida! Tentando forçar modo desktop...")
                try:
                    # Comandos para tentar forçar modo desktop
                    desktop_commands = [
                        ["scrcpy/adb.exe", "shell", "settings", "put", "global", "force_desktop_mode_on_external_displays", "1"],
                        ["scrcpy/adb.exe", "shell", "settings", "put", "global", "force_resizable_activities", "1"],
                        ["scrcpy/adb.exe", "shell", "settings", "put", "global", "enable_freeform_support", "1"]
                    ]
                    
                    for cmd in desktop_commands:
                        try:
                            subprocess.run(cmd, capture_output=True, timeout=10)
                        except:
                            pass
                    
                    self.update_status("Conexão estabelecida! Modo desktop configurado. Iniciando espelhamento...")
                except Exception as e:
                    self.update_status(f"Conexão estabelecida! (Erro no modo desktop: {str(e)}). Iniciando espelhamento...")
            
            # Iniciar scrcpy
            scrcpy_cmd = self.get_scrcpy_command()
            
            try:
                self.scrcpy_process = subprocess.Popen(
                    scrcpy_cmd,
                    cwd=os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Aguardar um pouco para ver se o processo inicia corretamente
                time.sleep(2)
                
                # Verificar se o processo ainda está rodando
                if self.scrcpy_process.poll() is None:
                    # Salvar dados da conexão bem-sucedida
                    self.settings["last_ip"] = ip
                    self.settings["last_pair_port"] = pair_port
                    self.settings["last_pair_code"] = pair_code
                    self.settings["last_connect_port"] = connect_port
                    self.save_settings()
                    
                    self.update_status("Espelhamento ativo!")
                    self.is_connected = True
                    self.should_reconnect = True
                    
                    # Habilitar botão de parar
                    self.stop_button.configure(state="normal")
                    
                    # Iniciar monitoramento de reconexão
                    self.reconnect_thread = threading.Thread(target=self._monitor_connection, daemon=True)
                    self.reconnect_thread.start()
                    
                    # Iniciar sndcpy se habilitado
                    if self.audio_var.get():
                        self.update_status("Espelhamento ativo! Iniciando áudio...")
                        threading.Thread(target=self._start_sndcpy, daemon=True).start()
                else:
                    # Processo parou imediatamente
                    stdout, stderr = self.scrcpy_process.communicate()
                    error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Processo encerrado sem erro"
                    self.update_status(f"Erro: scrcpy parou imediatamente. {error_msg}")
                    self.connect_button.configure(state="normal")
                
            except Exception as e:
                self.update_status(f"Erro ao iniciar scrcpy: {str(e)}")
                self.connect_button.configure(state="normal")
                
        except Exception as e:
            self.update_status(f"Erro inesperado: {str(e)}")
            self.connect_button.configure(state="normal")
    
    def _start_sndcpy(self):
        """Inicia o sndcpy em thread separada"""
        try:
            if os.path.exists("sndcpy/sndcpy.bat"):
                self.sndcpy_process = subprocess.Popen(
                    ["sndcpy/sndcpy.bat"],
                    cwd=os.getcwd()
                )
                self.update_status("Espelhamento ativo! Áudio habilitado.")
            else:
                self.update_status("Espelhamento ativo! (sndcpy não encontrado)")
        except Exception as e:
            self.update_status(f"Espelhamento ativo! (Erro no áudio: {str(e)})")
    
    def _monitor_connection(self):
        """Monitora a conexão e reconecta automaticamente se necessário"""
        while self.should_reconnect and self.is_connected:
            time.sleep(5)  # Verificar a cada 5 segundos
            
            # Verificar se scrcpy ainda está rodando
            if self.scrcpy_process and self.scrcpy_process.poll() is not None:
                self.update_status("Conexão perdida! Tentando reconectar...")
                
                try:
                    # Tentar reconectar apenas via ADB (sem pareamento)
                    ip = self.ip_entry.get().strip()
                    connect_port = self.connect_port_entry.get().strip()
                    
                    if ip and connect_port:
                        # Verificar se o dispositivo ainda está conectado
                        result = subprocess.run(
                            ["scrcpy/adb.exe", "devices"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if f"{ip}:{connect_port}" in result.stdout:
                            # Dispositivo ainda conectado, reiniciar scrcpy
                            self.scrcpy_process.terminate()
                            time.sleep(1)
                            
                            scrcpy_cmd = self.get_scrcpy_command()
                            self.scrcpy_process = subprocess.Popen(
                                scrcpy_cmd,
                                cwd=os.getcwd(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                            
                            time.sleep(2)
                            if self.scrcpy_process.poll() is None:
                                self.update_status("Reconexão bem-sucedida! Espelhamento ativo.")
                            else:
                                self.update_status("Falha na reconexão. Clique em 'Conectar' novamente.")
                                self.should_reconnect = False
                                self.is_connected = False
                                self.connect_button.configure(state="normal")
                                self.stop_button.configure(state="disabled")
                        else:
                            self.update_status("Dispositivo desconectado. Clique em 'Conectar' novamente.")
                            self.should_reconnect = False
                            self.is_connected = False
                            self.connect_button.configure(state="normal")
                            self.stop_button.configure(state="disabled")
                            
                except Exception as e:
                    self.update_status(f"Erro na reconexão: {str(e)}")
                    self.should_reconnect = False
                    self.is_connected = False
                    self.connect_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
    
    def stop_connection(self):
        """Para a conexão e encerra os processos"""
        try:
            # Parar monitoramento de reconexão
            self.should_reconnect = False
            
            # Encerrar scrcpy
            if self.scrcpy_process:
                self.scrcpy_process.terminate()
                self.scrcpy_process = None
            
            # Encerrar sndcpy
            if self.sndcpy_process:
                self.sndcpy_process.terminate()
                self.sndcpy_process = None
            
            # Encerrar VLC (usado pelo sndcpy)
            try:
                subprocess.run(["taskkill", "/f", "/im", "vlc.exe"], 
                             capture_output=True, timeout=5)
            except:
                pass
            
            # Desconectar ADB
            try:
                ip = self.ip_entry.get().strip()
                connect_port = self.connect_port_entry.get().strip()
                if ip and connect_port:
                    subprocess.run(
                        ["scrcpy/adb.exe", "disconnect", f"{ip}:{connect_port}"],
                        capture_output=True,
                        timeout=10
                    )
            except:
                pass
            
            self.is_connected = False
            self.update_status("Conexão encerrada. Aguardando informações...")
            
            # Reativar botão de conectar
            self.connect_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            
        except Exception as e:
            self.update_status(f"Erro ao encerrar conexão: {str(e)}")
    
    def on_closing(self):
        """Chamado quando a janela é fechada"""
        # Salvar configurações
        self.settings["resolution"] = self.resolution_var.get()
        self.settings["fps"] = self.fps_var.get()
        self.settings["bitrate"] = self.bitrate_entry.get().strip()
        self.settings["enable_audio"] = self.audio_var.get()
        self.settings["force_desktop"] = self.desktop_var.get()
        self.save_settings()
        
        # Encerrar conexão se ativa
        if self.is_connected:
            self.stop_connection()
        
        self.root.destroy()
    
    def run(self):
        """Inicia a aplicação"""
        self.root.mainloop()

if __name__ == "__main__":
    app = SM0App()
    app.run()
