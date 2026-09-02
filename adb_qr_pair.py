"""
Módulo de Pareamento e Reconexão Automática ADB via QR Code e mDNS (Zeroconf) para SM0.
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
from typing import Callable, Optional, List, Dict
from PIL import Image
import qrcode
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo


def get_active_adb_devices(adb_path: str = "scrcpy/adb.exe") -> List[Dict[str, str]]:
    """Retorna a lista de dispositivos atualmente autorizados e conectados no ADB."""
    devices = []
    try:
        res = subprocess.run([adb_path, "devices", "-l"], capture_output=True, text=True, timeout=4)
        for line in res.stdout.strip().splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                model_match = re.search(r"model:(\S+)", line)
                model = model_match.group(1) if model_match else "Android"
                devices.append({"serial": serial, "model": model, "raw": line})
    except Exception:
        pass
    return devices


def get_mdns_connect_services(adb_path: str = "scrcpy/adb.exe") -> List[Dict[str, str]]:
    """Consulta 'adb mdns services' para encontrar celulares com depuração ativa na rede."""
    services = []
    try:
        res = subprocess.run([adb_path, "mdns", "services"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            if "_adb-tls-connect" in line:
                parts = line.split()
                # Exemplo: adb-RQCTB01SRXM-LUFN1L  _adb-tls-connect._tcp  192.168.3.5:41603
                for p in parts:
                    if ":" in p and "." in p:
                        host_port = p.split(":")
                        if len(host_port) == 2 and host_port[1].isdigit():
                            services.append({
                                "service": parts[0],
                                "ip": host_port[0],
                                "port": int(host_port[1]),
                                "endpoint": p
                            })
    except Exception:
        pass
    return services


def quick_connect_adb(adb_path: str, endpoint: str, timeout: int = 5) -> bool:
    """Tenta conexão rápida ao IP:porta via adb connect."""
    try:
        res = subprocess.run([adb_path, "connect", endpoint], capture_output=True, text=True, timeout=timeout)
        out = (res.stdout + res.stderr).lower()
        if "connected to" in out or "already connected" in out:
            return True
    except Exception:
        pass
    return False


class ADBQRPairListener(ServiceListener):
    """Escuta anúncios de novos pareamentos por QR Code (_adb-tls-pairing)."""
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


class ADBAutoConnectListener(ServiceListener):
    """Escuta anúncios de celulares já pareados na rede (_adb-tls-connect)."""
    def __init__(self, on_connect_found_callback: Callable[[str, int, str], None]):
        self.on_connect_found_callback = on_connect_found_callback
        self.seen_endpoints = set()

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        try:
            info = zc.get_service_info(type_, name)
            if info:
                addresses = info.parsed_scoped_addresses()
                ip = None
                for addr in addresses:
                    if ":" not in addr:
                        ip = addr
                        break
                if not ip and addresses:
                    ip = addresses[0]

                if ip and info.port:
                    endpoint = f"{ip}:{info.port}"
                    if endpoint not in self.seen_endpoints:
                        self.seen_endpoints.add(endpoint)
                        self.on_connect_found_callback(ip, info.port, name)
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
        self.pair_browser: Optional[ServiceBrowser] = None
        self.connect_browser: Optional[ServiceBrowser] = None
        self.is_running = False
        self.connected_or_paired = False
        self.lock = threading.Lock()

    def generate_session(self) -> str:
        """Gera credenciais seguras e payload no formato oficial AOSP para o QR Code."""
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

    def start_listening(self, listen_for_autoconnect: bool = True):
        """Inicia a escuta por mDNS tanto para pareamento (QR) quanto para celulares já pareados."""
        with self.lock:
            if self.is_running:
                self.stop()

            self.is_running = True
            self.connected_or_paired = False
            if not self.payload:
                self.generate_session()

        def _listen_worker():
            try:
                self.on_status("🔍 Procurando celular pareado na rede ou aguardando leitura do QR Code...")
                self.zc = Zeroconf()

                # 1. Escutar pareamento com QR Code
                pair_listener = ADBQRPairListener(self.service_name, self._on_pairing_device_found)
                self.pair_browser = ServiceBrowser(self.zc, "_adb-tls-pairing._tcp.local.", pair_listener)

                # 2. Escutar dispositivos já pareados na rede local
                if listen_for_autoconnect:
                    auto_connect_listener = ADBAutoConnectListener(self._on_auto_connect_device_found)
                    self.connect_browser = ServiceBrowser(self.zc, "_adb-tls-connect._tcp.local.", auto_connect_listener)

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

    def _on_auto_connect_device_found(self, ip: str, port: int, service_name: str):
        """Disparado quando um celular já pareado anuncia serviço de depuração na rede local."""
        if not self.is_running or self.connected_or_paired:
            return

        def _auto_connect_worker():
            with self.lock:
                if self.connected_or_paired:
                    return

            self.on_status(f"⚡ Celular pareado detectado em {ip}:{port}! Conectando...")
            endpoint = f"{ip}:{port}"
            success = quick_connect_adb(self.adb_path, endpoint, timeout=6)
            
            # Checar se já temos device conectado
            active_devices = get_active_adb_devices(self.adb_path)
            matching = [d for d in active_devices if ip in d["serial"] or endpoint in d["serial"] or service_name.split(".")[0] in d["serial"]]
            
            if matching:
                target_serial = matching[0]["serial"]
                with self.lock:
                    self.connected_or_paired = True
                self.on_status(f"🎉 Celular pareado reconectado com sucesso ({matching[0]['model']})!")
                self.on_success(ip, port, target_serial)
                self.stop()
            elif success:
                with self.lock:
                    self.connected_or_paired = True
                self.on_status(f"🎉 Conectado em {endpoint}!")
                self.on_success(ip, port, endpoint)
                self.stop()

        threading.Thread(target=_auto_connect_worker, daemon=True).start()

    def _on_pairing_device_found(self, ip: str, pair_port: int):
        """Disparado quando o celular lê o QR Code e anuncia o serviço de pareamento na rede."""
        if not self.is_running or self.connected_or_paired:
            return

        self.on_status(f"📷 QR Code lido pelo celular ({ip}:{pair_port})! Pareando...")

        def _pair_worker():
            try:
                pair_target = f"{ip}:{pair_port}"
                cmd = [self.adb_path, "pair", pair_target, self.password]
                
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                output = (res.stdout + " " + res.stderr).strip()

                if res.returncode != 0 and "successfully paired" not in output.lower():
                    # Fallback com stdin interativo
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
                self._resolve_and_connect(ip)

            except Exception as e:
                self.on_error(f"Erro durante o pareamento: {str(e)}")

        threading.Thread(target=_pair_worker, daemon=True).start()

    def _resolve_and_connect(self, ip: str):
        """Descobre a porta de conexão do celular recém-pareado e conecta o ADB."""
        connect_port = None

        # 1. Consultar 'adb mdns services'
        services = get_mdns_connect_services(self.adb_path)
        for s in services:
            if s["ip"] == ip:
                connect_port = s["port"]
                break

        # 2. Verificar se já existe conexão ativa no 'adb devices'
        active_devices = get_active_adb_devices(self.adb_path)
        for d in active_devices:
            if ip in d["serial"]:
                with self.lock:
                    self.connected_or_paired = True
                self.on_status(f"🎉 Conexão ADB ativa encontrada: {d['serial']}!")
                self.on_success(ip, connect_port or 5555, d["serial"])
                self.stop()
                return

        # 3. Tentar conectar
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
            active_devices = get_active_adb_devices(self.adb_path)
            matching = [d for d in active_devices if ip in d["serial"] or target_to_connect in d["serial"]]
            
            with self.lock:
                self.connected_or_paired = True

            if matching:
                self.on_status(f"🎉 Conectado com sucesso em {matching[0]['serial']}!")
                self.on_success(ip, connect_port or 5555, matching[0]["serial"])
            elif "connected" in out.lower() or "already" in out.lower():
                self.on_status(f"🎉 Conectado com sucesso em {target_to_connect}!")
                self.on_success(ip, connect_port or 5555, target_to_connect)
            else:
                self.on_error(f"Erro ao conectar via ADB: {out}")
        except Exception as e:
            self.on_error(f"Erro na conexão ADB: {str(e)}")
        finally:
            self.stop()

    def stop(self):
        """Para listeners mDNS e libera recursos de rede."""
        with self.lock:
            self.is_running = False
            try:
                if self.pair_browser:
                    self.pair_browser.cancel()
                    self.pair_browser = None
                if self.connect_browser:
                    self.connect_browser.cancel()
                    self.connect_browser = None
                if self.zc:
                    self.zc.close()
                    self.zc = None
            except Exception:
                pass
