import os
import sys
import subprocess
import time

# Força exibição imediata de cada linha no terminal sem esperar buffer
sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ADB_PATH = os.path.join(PROJECT_DIR, "scrcpy", "adb.exe")
INV_PATH = os.path.join(PROJECT_DIR, "inventario_backup", "inventario_arquivos.md")
DEST_BASE = os.path.join(PROJECT_DIR, "inventario_backup", "arquivos_copiados")
DEVICE_DEFAULT = "192.168.3.5:45537"

SUBPROCESS_FLAGS = {}
if sys.platform == "win32":
    SUBPROCESS_FLAGS["creationflags"] = subprocess.CREATE_NO_WINDOW
    _si = subprocess.STARTUPINFO()
    _si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _si.wShowWindow = subprocess.SW_HIDE
    SUBPROCESS_FLAGS["startupinfo"] = _si

os.makedirs(DEST_BASE, exist_ok=True)

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}" if unit != 'B' else f"{bytes_size} B"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_connected_device():
    res = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True, errors="ignore", **SUBPROCESS_FLAGS)
    lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return DEVICE_DEFAULT

def load_files_from_inventory():
    files = []
    current_folder = None
    
    if not os.path.exists(INV_PATH):
        return []
        
    with open(INV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("### 📁"):
                parts = line.split("`")
                if len(parts) >= 2:
                    current_folder = parts[1]
            elif line.startswith("|") and current_folder and "WhatsApp" not in current_folder:
                cols = [c.strip() for c in line.split("|")]
                if len(cols) >= 6 and cols[1] not in ["Nome do Arquivo", ""] and not cols[1].startswith(":"):
                    fname = cols[1]
                    sub = cols[2].replace("`", "").strip()
                    fmt = cols[4]
                    size = int(cols[5]) if cols[5].isdigit() else 0
                    
                    # Ignorar arquivos temporários zerados do cache de câmera
                    if fname.startswith(".temp-") and size == 0:
                        continue
                        
                    sub_clean = sub.strip("/\\")
                    if sub_clean:
                        remote_path = f"{current_folder}/{sub_clean}/{fname}"
                        rel_dir = os.path.join(current_folder.replace("/sdcard/", ""), sub_clean)
                    else:
                        remote_path = f"{current_folder}/{fname}"
                        rel_dir = current_folder.replace("/sdcard/", "")
                        
                    local_dest = os.path.join(DEST_BASE, rel_dir, fname)
                    
                    files.append({
                        "remote": remote_path,
                        "local": local_dest,
                        "rel_dir": rel_dir,
                        "name": fname,
                        "size": size,
                        "size_fmt": fmt
                    })
    return files

def main():
    print("=" * 75, flush=True)
    print(" 🚀 INICIANDO BACKUP SEGURO SAMSUNG S22 (SEM WHATSAPP)", flush=True)
    print("=" * 75, flush=True)
    
    device = get_connected_device()
    print(f"📱 Dispositivo conectado via Wi-Fi: {device}", flush=True)
    print(f"📁 Pasta de destino no seu PC: {DEST_BASE}", flush=True)
    print("🔒 MODO ESTREITAMENTE LEITURA: Nenhum arquivo será apagado do celular.", flush=True)
    print("-" * 75, flush=True)
    print("📋 Carregando lista de arquivos do inventário...", flush=True)
    
    files = load_files_from_inventory()
    total_files = len(files)
    total_bytes = sum(f["size"] for f in files)
    
    if total_files == 0:
        print("❌ Nenhum arquivo encontrado no inventário.", flush=True)
        return
        
    print(f"✅ Total a processar: {total_files} arquivos | {format_size(total_bytes)}", flush=True)
    print("=" * 75, flush=True)
    print("LISTA DE ARQUIVOS SENDO COPIADOS EM TEMPO REAL:\n", flush=True)
    
    bytes_transferred = 0
    start_time = time.time()
    
    for idx, item in enumerate(files, 1):
        remote_file = item["remote"]
        local_file = item["local"]
        file_size = item["size"]
        size_fmt = item["size_fmt"]
        rel_dir = item["rel_dir"]
        
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        pct = (idx / total_files) * 100
        
        # Se já existe com mesmo tamanho, pula
        if os.path.exists(local_file) and os.path.getsize(local_file) == file_size:
            bytes_transferred += file_size
            print(f"[{idx:4d}/{total_files}] ({pct:5.1f}%) ⏩ [JÁ EXISTE] {item['name']} ({size_fmt})", flush=True)
            continue
            
        # Executa o pull sem fio
        cmd = [ADB_PATH, "-s", device, "pull", remote_file, local_file]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore", **SUBPROCESS_FLAGS)
        
        if res.returncode == 0 and os.path.exists(local_file):
            bytes_transferred += file_size
            print(f"[{idx:4d}/{total_files}] ({pct:5.1f}%) ✅ [COPIADO] {item['name']} ({size_fmt}) -> {rel_dir}", flush=True)
        else:
            print(f"[{idx:4d}/{total_files}] ({pct:5.1f}%) ⚠️ [PULADO/ERRO] {item['name']} - {res.stderr.strip() or 'Erro de leitura'}", flush=True)
            
    elapsed = time.time() - start_time
    print("\n" + "=" * 75, flush=True)
    print(f"🎉 BACKUP CONCLUÍDO COM SUCESSO!", flush=True)
    print(f"📊 Total processado: {total_files} arquivos ({format_size(bytes_transferred)})", flush=True)
    print(f"⏱️ Tempo total: {elapsed/60:.1f} minutos", flush=True)
    print(f"📂 Local dos arquivos: {DEST_BASE}", flush=True)
    print("=" * 75, flush=True)

if __name__ == "__main__":
    main()
