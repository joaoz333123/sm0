"""
Módulo de Pareamento ADB via QR Code e mDNS (Zeroconf) para SM0.
Compatível com Android 11+ (Wireless Debugging / Depuração sem fio).
"""

import os
import random
import re
import socket
import string
import subprocess
import threading
import time
from typing import Callable, Optional
from PIL import Image
import qrcode
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo


class ADBQRPairListener(ServiceListener):
    def __init__(self, target_service_name: str, on_found_callback: Callable[[str, int], None]):
        self.target_service_name = target_service_name
        self.on_found_callback = on_found_callback
        self.handled = False

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if self.handled:
            return
        
        try:
            info = zc.get_service_info(type_, name)
            if info:
                addresses = info.parsed_scoped_addresses()
                ip = None
                for addr in addresses:
                    if ":" not in addr:  # Preferir IPv4
                        ip = addr
                        break
                if not ip and addresses:
                    ip = addresses[0]

                if ip and info.port:
                    self.handled = True
                    self.on_found_callback(ip, info.port)
        except Exception:
            pass


class ADBQRConnectListener(ServiceListener):
    def __init__(self, target_ip: str, on_connect_found_callback: Callable[[str, int], None]):
        self.target_ip = target_ip
        self.on_connect_found_callback = on_connect_found_callback
        self.handled = False

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if self.handled:
            return
        
        try:
            info = zc.get_service_info(type_, name)
            if info:
                addresses = info.parsed_scoped_addresses()
                for addr in addresses:
                    if addr == self.target_ip:
                        self.handled = True
                        self.on_connect_found_callback(self.target_ip, info.port)
                        break
        except Exception:
            pass


class ADBQRPairer:
    def __init__(
        self,
        adb_path: str = "scrcpy/adb.exe",
        on_status: Optional[Callable[[str], None]] = None,
        on_success: Optional[Callable[[str, int, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        self.adb_path = adb_path
        self.on_status = on_status or (lambda msg: None)
        self.on_success = on_success or (lambda ip, port, serial: None)
        self.on_error = on_error or (lambda err: None)

        self.service_name = ""
        self.password = ""
        self.payload = ""
        self.zc: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        self.connect_browser: Optional[ServiceBrowser] = None
        self.is_running = False
        self.lock = threading.Lock()

    def generate_session(self) -> str:
        """Gera credenciais seguras e payload no formato oficial AOSP."""
        rand_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.service_name = f"SM0-{rand_suffix}"
        # Senha numérica de 6 dígitos para compatibilidade total
        self.password = "".join(random.choices(string.digits, k=6))
        self.payload = f"WIFI:T:ADB;S:{self.service_name};P:{self.password};;"
        return self.payload

    def get_qr_image(self, size: int = 240) -> Image.Image:
        """Gera a imagem do QR Code para exibição na GUI."""
        if not self.payload:
            self.generate_session()

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(self.payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        return img.resize((size, size), Image.Resampling.LANCZOS)

    def start_listening(self):
        """Inicia a escuta por mDNS em segundo plano."""
        with self.lock:
            if self.is_running:
                self.stop()

            self.is_running = True
            if not self.payload:
                self.generate_session()

        def _listen_worker():
            try:
                self.on_status("Aguardando leitura do QR Code no celular...")
                self.zc = Zeroconf()
                listener = ADBQRPairListener(self.service_name, self._on_pairing_device_found)
                self.browser = ServiceBrowser(self.zc, "_adb-tls-pairing._tcp.local.", listener)

                # Monitorar até 180 segundos
                start_time = time.time()
                while self.is_running and (time.time() - start_time < 180):
                    time.sleep(1)
                    if not self.is_running:
                        break
            except Exception as e:
                if self.is_running:
                    self.on_error(f"Erro no serviço de descoberta mDNS: {e}")

        threading.Thread(target=_listen_worker, daemon=True).start()

    def _on_pairing_device_found(self, ip: str, pair_port: int):
        """Disparado quando o celular anuncia o serviço de pareamento na rede local."""
        if not self.is_running:
            return

        self.on_status(f"Celular detectado ({ip}:{pair_port})! Pareando...")

        def _pair_worker():
            try:
                pair_target = f"{ip}:{pair_port}"
                # Passa a senha como argumento direto do comando adb pair (evita bugs de stdin)
                cmd = [self.adb_path, "pair", pair_target, self.password]
                
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                output = (res.stdout + " " + res.stderr).strip()

                if res.returncode != 0 and "successfully paired" not in output.lower():
                    # Se falhar passando argumento direto, tentar com input interativo como fallback
                    res2 = subprocess.run(
                        [self.adb_path, "pair", pair_target],
                        input=f"{self.password}\n",
                        text=True,
                        capture_output=True,
                        timeout=15
                    )
                    output2 = (res2.stdout + " " + res2.stderr).strip()
                    if res2.returncode != 0 and "successfully paired" not in output2.lower():
                        self.on_error(f"Falha no pareamento: {output2 or output}")
                        return

                self.on_status("✅ Pareamento concluído! Conectando depuração...")

                # Conectar à porta de depuração do celular
                self._resolve_and_connect(ip)

            except Exception as e:
                self.on_error(f"Erro durante o pareamento: {str(e)}")

        threading.Thread(target=_pair_worker, daemon=True).start()

    def _resolve_and_connect(self, ip: str):
        """Descobre a porta de conexão do celular e conecta o ADB."""
        connect_port = None

        # 1. Tentar localizar a porta de conexão via listener mDNS _adb-tls-connect._tcp.local.
        connected_event = threading.Event()
        found_port = []

        def _on_connect_service(discovered_ip: str, port: int):
            found_port.append(port)
            connected_event.set()

        try:
            if self.zc:
                conn_listener = ADBQRConnectListener(ip, _on_connect_service)
                self.connect_browser = ServiceBrowser(self.zc, "_adb-tls-connect._tcp.local.", conn_listener)
                connected_event.wait(timeout=3.0)
        except Exception:
            pass

        if found_port:
            connect_port = found_port[0]

        # 2. Se não detectou a porta específica por mDNS listener, consultar 'adb mdns services'
        if not connect_port:
            connect_port = self._get_connect_port_from_adb_mdns(ip)

        # 3. Verificar se já existe conexão ativa no 'adb devices'
        active_serial = self._get_connected_device_serial(ip)
        if active_serial:
            self.on_status(f"🎉 Conexão ADB ativa encontrada: {active_serial}!")
            self.on_success(ip, connect_port or 5555, active_serial)
            self.stop()
            return

        # 4. Tentar comando connect
        target_to_connect = f"{ip}:{connect_port}" if connect_port else ip

        self.on_status(f"Conectando ADB em {target_to_connect}...")
        try:
            conn_res = subprocess.run(
                [self.adb_path, "connect", target_to_connect],
                capture_output=True,
                text=True,
                timeout=10
            )
            out = (conn_res.stdout + conn_res.stderr).strip()
            
            time.sleep(1.0)
            active_serial = self._get_connected_device_serial(ip)
            
            if active_serial:
                self.on_status(f"🎉 Conectado com sucesso em {active_serial}!")
                self.on_success(ip, connect_port or 5555, active_serial)
            elif "connected" in out.lower() or "already" in out.lower():
                self.on_status(f"🎉 Conectado com sucesso em {target_to_connect}!")
                self.on_success(ip, connect_port or 5555, target_to_connect)
            else:
                self.on_error(f"Erro ao conectar via ADB: {out}")
        except Exception as e:
            self.on_error(f"Erro na conexão ADB: {str(e)}")
        finally:
            self.stop()

    def _get_connected_device_serial(self, ip: str) -> Optional[str]:
        """Verifica se há um serial correspondente conectado em adb devices."""
        try:
            res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, timeout=4)
            for line in res.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    serial = parts[0]
                    if ip in serial or ":" in serial:
                        return serial
                    return serial
        except Exception:
            pass
        return None

    def _get_connect_port_from_adb_mdns(self, ip: str) -> Optional[int]:
        """Tenta obter a porta de conexão a partir da saída de 'adb mdns services'."""
        try:
            res = subprocess.run([self.adb_path, "mdns", "services"], capture_output=True, text=True, timeout=3)
            for line in res.stdout.splitlines():
                if "_adb-tls-connect" in line and ip in line:
                    parts = line.split()
                    for p in parts:
                        if ":" in p:
                            host_port = p.split(":")
                            if len(host_port) == 2 and host_port[1].isdigit():
                                return int(host_port[1])
        except Exception:
            pass
        return None

    def stop(self):
        """Para listeners mDNS e libera recursos de rede."""
        with self.lock:
            self.is_running = False
            try:
                if self.browser:
                    self.browser.cancel()
                    self.browser = None
                if self.connect_browser:
                    self.connect_browser.cancel()
                    self.connect_browser = None
                if self.zc:
                    self.zc.close()
                    self.zc = None
            except Exception:
                pass
