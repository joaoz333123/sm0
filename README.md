# 📱 SM0 - Utilitário de Espelhamento Android

Aplicação desktop moderna construída em Python (**CustomTkinter**) para espelhamento de tela e transmissão de áudio sem fio de smartphones Android (via Wi-Fi / ADB Wireless e cabo USB), utilizando o **scrcpy 3.x** e **ADB v37.0.1 (Google SDK Platform-Tools)**.

---

## ✨ Funcionalidades Principais

* 📷 **Conexão e Espelhamento Automático por QR Code (Android 11+):**
  * Ao abrir o aplicativo, um QR Code exclusivo com credenciais seguras é gerado imediatamente na tela.
  * Basta apontar a câmera do celular em *Depuração sem fio > Parear dispositivo com código QR* — o SM0 detecta o aparelho via mDNS (Zeroconf), realiza o pareamento e **inicia a janela de espelhamento automaticamente**, sem necessidade de clicar em botão algum!
* ⚡ **Descoberta de Rede mDNS / Zeroconf:** Localiza automaticamente a porta de pareamento e a porta de conexão de depuração do celular na rede local.
* 🛠️ **ADB Atualizado (v37.0.1):** Binários oficiais mais recentes do Android SDK Platform-Tools da Google embutidos para máxima estabilidade e compatibilidade.
* 🔄 **Detecção em Tempo Real:** Monitora e exibe no painel o status de dispositivos conectados ao ADB (USB ou Wi-Fi).
* 🧹 **Reset Rápido do ADB (`🧹 Resetar ADB`):** Desconecta sockets travados e reinicia o servidor ADB e o listener do QR Code com 1 clique.
* 🔊 **Áudio Nativo de Baixa Latência:** Streaming de áudio integrado diretamente pelo motor do `scrcpy 3.x`.
* 🎬 **Controle Avançado de Vídeo:**
  * Resoluções selecionáveis: `720p`, `1080p`, `1440p` ou `Original`.
  * Taxa de quadros: `30 FPS`, `60 FPS` ou `Max`.
  * Bitrate configurável (padrão: 12 Mbps).
* 🔋 **Modos de Economia e Produtividade:**
  * **Apagar tela do celular:** Desliga o display do celular durante o espelhamento para poupar bateria e evitar aquecimento (`--turn-screen-off`).
  * **Manter ativo:** Impede que o celular suspenda durante o uso (`--stay-awake`).
  * **Modo Desktop / DeX:** Ativa flags de redimensionamento e janelas livres no Android.
* 💾 **Salvamento Automático:** Lembra suas preferências, último IP e portas no arquivo `settings.json`.

---

## 📋 Pré-requisitos

1. **Python 3.10+** instalado no Windows (certifique-se de marcar *"Add Python to PATH"* durante a instalação).
2. Smartphone Android com **Depuração Sem Fio** (Android 11 ou superior) ou **Depuração USB** ativada nas *Opções do Desenvolvedor*.
3. PC e Celular conectados na **mesma rede Wi-Fi**.

---

## 🚀 Instalação e Execução

### Método Rápido (Recomendado)
Dê um duplo clique no arquivo:
```cmd
executar_sm0.bat
```
*(O script verifica e instala dependências automaticamente e inicia o SM0)*

### Método Manual via Terminal
1. Instale as dependências:
   ```powershell
   pip install -r requirements.txt
   ```
2. Inicie a aplicação:
   ```powershell
   python main.py
   ```

---

## 📱 Guia de Conexão Rápida via QR Code (Recomendado)

1. Abra o SM0 no computador (`executar_sm0.bat` ou `python main.py`).
2. No celular (conectado no mesmo Wi-Fi do computador):
   * Abra **Configurações** > **Opções do desenvolvedor**.
   * Ative a chave **Depuração sem fio**.
   * Toque na opção **"Parear dispositivo com código QR"**.
3. Aponte a câmera do celular para o QR Code exibido na tela do SM0.
4. **Pronto!** O celular será pareado e a tela abrirá automaticamente no seu PC.

---

## 🔧 Guia de Conexão Manual por IP (Opcional)

Se preferir conectar manualmente ou utilizar PIN de pareamento:
1. No celular, em **Depuração sem fio**, veja o **Endereço IP e porta principal** (ex: `192.168.3.83:38171`).
2. No SM0, digite o **IP** e a **Porta Conexão**.
3. Se for um novo pareamento sem QR Code, toque em *"Parear com código de pareamento"* no celular e digite a **Porta Parear** e o **PIN** no SM0.
4. Clique em **"▶ Conectar e Espelhar Manualmente"**.

---

## ⌨️ Atalhos Úteis do Scrcpy durante o Espelhamento

| Atalho | Ação |
| :--- | :--- |
| `Alt` + `F` | Alternar tela cheia (Fullscreen) |
| `Alt` + `O` | Ligar/desligar a tela do celular |
| `Alt` + `H` | Botão Home (Início) |
| `Alt` + `B` ou `Botão Direito do Mouse` | Botão Voltar (Back) |
| `Alt` + `S` | Alternar aplicativos recentes |
| `Alt` + `Up` / `Down` | Aumentar / Diminuir volume |
| `Ctrl` + `V` no PC | Cola a área de transferência do PC no Android |

---

## 📂 Estrutura de Arquivos

```
sm0/
├── main.py              # Interface gráfica CustomTkinter e controle principal
├── adb_qr_pair.py       # Motor de pareamento AOSP QR Code e listener mDNS Zeroconf
├── executar_sm0.bat     # Inicializador automático para Windows
├── requirements.txt     # Dependências (customtkinter, qrcode, zeroconf)
├── settings.json        # Configurações salvas do usuário
├── README.md            # Documentação da aplicação
└── scrcpy/             # Binários embutidos do scrcpy 3.x e ADB v37.0.1
    ├── scrcpy.exe
    ├── adb.exe
    ├── scrcpy-server
    └── ... (DLLs auxiliares)
```
