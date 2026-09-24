import os
import sys
import subprocess
import time
from datetime import datetime

# Caminhos e configurações
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ADB_PATH = os.path.join(PROJECT_DIR, "scrcpy", "adb.exe")
DEVICE_TARGET = "192.168.3.5:45537"

# Pasta de destino dentro do inventário
DEST_BASE = os.path.join(PROJECT_DIR, "inventario_backup", "arquivos_copiados")
os.makedirs(DEST_BASE, exist_ok=True)

# Pastas autorizadas para cópia (TOTALMENTE EXCLUÍDO O WHATSAPP)
TARGET_FOLDERS = [
    "/sdcard/DCIM",
    "/sdcard/Pictures",
    "/sdcard/Movies",
    "/sdcard/Download",
    "/sdcard/Documents",
    "/sdcard/Voo",
    "/sdcard/Recordings",
    "/sdcard/Music",
    "/sdcard/X Video Player"
]

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}" if unit != 'B' else f"{bytes_size} B"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_connected_device():
    res = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True, errors="ignore")
    lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            if parts[0] == DEVICE_TARGET:
                return parts[0]
            # Se mudou de porta mas é o mesmo IP
            if parts[0].startswith("192.168.3.5"):
                return parts[0]
    return DEVICE_TARGET

def collect_file_list(device):
    print("=" * 70)
    print(" 🔍 MAPEANDO ARQUIVOS NO CELULAR (EXCETO WHATSAPP)...")
    print("=" * 70)
    
    file_list = []
    
    for folder in TARGET_FOLDERS:
        print(f" -> Lendo diretório: {folder}")
        cmd = [ADB_PATH, "-s", device, "shell", f"ls -laR '{folder}' 2>/dev/null"]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        
        current_dir = folder
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.endswith(":") and ("/" in line):
                current_dir = line[:-1]
                continue
            
            parts = line.split(maxsplit=7)
            if len(parts) >= 8 and parts[0].startswith("-"):
                try:
                    size = int(parts[4])
                    fname = parts[7]
                    if fname in [".", "..", ".nomedia"]:
                        continue
                    if ".thumbnails" in current_dir:
                        continue
                    
                    full_remote_path = f"{current_dir}/{fname}"
                    # Calcular caminho relativo local
                    rel_path = full_remote_path.replace("/sdcard/", "").replace("/", os.sep)
                    local_dest_path = os.path.join(DEST_BASE, rel_path)
                    
                    file_list.append({
                        "remote": full_remote_path,
                        "local": local_dest_path,
                        "name": fname,
                        "size": size,
                        "size_fmt": format_size(size)
                    })
                except (ValueError, IndexError):
                    continue
                    
    return file_list

def run_backup():
    device = get_connected_device()
    print(f"\nDispositivo alvo: {device}")
    print(f"Pasta de destino local: {DEST_BASE}\n")
    print("⚠️  AVISO DE SEGURANÇA: MODO ESTREITAMENTE LEITURA (PULL).")
    print("   Nenhum arquivo será excluído, movido ou alterado no seu celular.\n")
    
    files = collect_file_list(device)
    total_files = len(files)
    total_bytes = sum(f["size"] for f in files)
    
    if total_files == 0:
        print("❌ Nenhum arquivo encontrado ou aparelho desconectado.")
        return
        
    print("\n" + "=" * 70)
    print(f" 📦 INÍCIO DO BACKUP: {total_files} arquivos | {format_size(total_bytes)}")
    print("=" * 70 + "\n")
    
    bytes_transferred = 0
    start_time = time.time()
    
    for idx, item in enumerate(files, 1):
        remote_file = item["remote"]
        local_file = item["local"]
        file_size = item["size"]
        size_fmt = item["size_fmt"]
        
        # Cria as subpastas locais se não existirem
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        
        # Verificar se o arquivo já foi copiado anteriormente com tamanho correto
        if os.path.exists(local_file) and os.path.getsize(local_file) == file_size:
            bytes_transferred += file_size
            pct = (idx / total_files) * 100
            print(f"[{idx:4d}/{total_files}] ({pct:5.1f}%) ⏩ [JÁ EXISTE] {item['name']} ({size_fmt})")
            continue
            
        pct = (idx / total_files) * 100
        print(f"[{idx:4d}/{total_files}] ({pct:5.1f}%) ⏳ Copiando: {item['name']} ({size_fmt})...", end="\r")
        
        cmd = [ADB_PATH, "-s", device, "pull", remote_file, local_file]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        
        if res.returncode == 0 and os.path.exists(local_file):
            bytes_transferred += file_size
            print(f"[{idx:4d}/{total_files}] ({pct:5.1f}%) ✅ [COPIADO] {item['name']} ({size_fmt}) -> {os.path.dirname(local_file)}")
        else:
            print(f"[{idx:4d}/{total_files}] ({pct:5.1f}%) ⚠️ [ERRO/PULADO] {item['name']} - {res.stderr.strip() or 'Falha'}")
            
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f" 🎉 BACKUP CONCLUÍDO COM SUCESSO!")
    print(f" - Total processado: {total_files} arquivos ({format_size(bytes_transferred)})")
    print(f" - Tempo decorrido: {elapsed/60:.1f} minutos")
    print(f" - Local salvo: {DEST_BASE}")
    print("=" * 70)

if __name__ == "__main__":
    run_backup()
