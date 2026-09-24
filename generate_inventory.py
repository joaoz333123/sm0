import os
import subprocess
import sys
from datetime import datetime

SUBPROCESS_FLAGS = {}
if sys.platform == "win32":
    SUBPROCESS_FLAGS["creationflags"] = subprocess.CREATE_NO_WINDOW
    _si = subprocess.STARTUPINFO()
    _si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _si.wShowWindow = subprocess.SW_HIDE
    SUBPROCESS_FLAGS["startupinfo"] = _si

ADB_PATH = os.path.abspath(r"scrcpy\adb.exe")
DEVICE = "192.168.3.5:45537"
OUTPUT_DIR = os.path.abspath(r"inventario_backup")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "inventario_arquivos.md")

os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_DIRS = [
    "/sdcard/DCIM",
    "/sdcard/Pictures",
    "/sdcard/Movies",
    "/sdcard/Download",
    "/sdcard/Documents",
    "/sdcard/Voo",
    "/sdcard/Recordings",
    "/sdcard/Music",
    "/sdcard/X Video Player",
    "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images",
    "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video",
    "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Documents",
    "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Animated Gifs"
]

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}" if unit != 'B' else f"{bytes_size} B"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def run_adb_shell(cmd):
    full_cmd = [ADB_PATH, "-s", DEVICE, "shell", cmd]
    result = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", **SUBPROCESS_FLAGS)
    return result.stdout

print("Iniciando coleta detalhada de inventário...")

report_data = {}
total_files = 0
total_bytes = 0

for target in TARGET_DIRS:
    print(f"Lendo: {target}")
    out = run_adb_shell(f"ls -laR '{target}' 2>/dev/null")
    current_dir = target
    report_data[target] = []
    
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith(":") and ("/" in line):
            current_dir = line[:-1]
            continue
        # -rw-rw---- 1 u0_a262 media_rw 8085086 2025-07-13 12:51 20250713_125114.jpg
        parts = line.split(maxsplit=7)
        if len(parts) >= 8 and parts[0].startswith("-"):
            try:
                size = int(parts[4])
                fname = parts[7]
                if fname in ['.', '..', '.nomedia']:
                    continue
                # Ignorar miniaturas temporárias de cache .thumbnails para não poluir
                if ".thumbnails" in current_dir:
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if not ext:
                    ext = "(sem extensão)"
                full_path = f"{current_dir}/{fname}"
                report_data[target].append({
                    "name": fname,
                    "path": full_path,
                    "folder": current_dir,
                    "size": size,
                    "size_fmt": format_size(size),
                    "ext": ext
                })
                total_files += 1
                total_bytes += size
            except (ValueError, IndexError):
                continue

print(f"Total coletado: {total_files} arquivos, {format_size(total_bytes)}")

# Gerando o arquivo Markdown
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("# Inventário Completo de Mídias e Arquivos - Samsung Galaxy S22\n\n")
    f.write(f"- **Data da Extração:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    f.write(f"- **Dispositivo:** Samsung S22 (ADB Wi-Fi: `{DEVICE}`)\n")
    f.write(f"- **Total de Arquivos Listados:** {total_files}\n")
    f.write(f"- **Volume Total:** {format_size(total_bytes)}\n\n")
    f.write("---\n\n")
    
    # Resumo por pasta raiz
    f.write("## 1. Resumo Consolidado por Pasta\n\n")
    f.write("| Diretório Base | Quantidade de Arquivos | Espaço Total |\n")
    f.write("| :--- | :--- | :--- |\n")
    
    for target in TARGET_DIRS:
        items = report_data.get(target, [])
        dir_bytes = sum(item["size"] for item in items)
        f.write(f"| `{target}` | {len(items)} arquivos | {format_size(dir_bytes)} |\n")
    
    f.write("\n---\n\n")
    
    # Detalhamento por pasta
    f.write("## 2. Detalhamento de Arquivos por Pasta\n\n")
    
    for target in TARGET_DIRS:
        items = report_data.get(target, [])
        if not items:
            continue
        
        dir_bytes = sum(item["size"] for item in items)
        f.write(f"### 📁 `{target}`\n\n")
        f.write(f"- **Subtotal:** {len(items)} arquivos ({format_size(dir_bytes)})\n\n")
        f.write("| Nome do Arquivo | Subpasta Relativa | Extensão | Tamanho Formatado | Tamanho (Bytes) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        
        for item in items:
            rel_folder = item["folder"].replace(target, "")
            if not rel_folder:
                rel_folder = "/"
            f.write(f"| {item['name']} | `{rel_folder}` | `{item['ext']}` | {item['size_fmt']} | {item['size']} |\n")
        
        f.write("\n---\n\n")

print(f"Inventário salvo com sucesso em: {OUTPUT_FILE}")
