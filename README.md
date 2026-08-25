# 📱 SM0 - Utilitário de Espelhamento Android

Aplicação desktop moderna construída em Python (**CustomTkinter**) para espelhamento de tela e transmissão de áudio sem fio de smartphones Android (via Wi-Fi / ADB Wireless e cabo USB), utilizando o **scrcpy 3.x**.

---

## ✨ Funcionalidades Principais

* **Conexão Direta e Pareamento Sem Fio:** Pareie facilmente via Depuração Sem Fio (Android 11+) usando PIN e conecte via IP e Porta em segundos.
* **Detecção Automática do ADB:** Monitora e exibe em tempo real os aparelhos Android conectados (USB ou Wi-Fi).
* **Reset Rápido do ADB (`🧹 Resetar ADB`):** Desconecta sockets travados e reinicia o servidor ADB com 1 clique.
* **Áudio Nativo de Baixa Latência:** Streaming de áudio nativo integrado diretamente pelo motor do `scrcpy 3.x`.
* **Controle Avançado de Vídeo:**
  * Resoluções selecionáveis: `720p`, `1080p`, `1440p` ou `Original`.
  * Taxa de quadros: `30 FPS`, `60 FPS` ou `Max`.
  * Bitrate configurável (padrão: 12 Mbps).
* **Modos de Economia e Produtividade:**
  * **Apagar tela do celular:** Desliga o display do celular durante o espelhamento para poupar bateria e evitar aquecimento (`--turn-screen-off`).
  * **Manter ativo:** Impede que o celular suspenda durante o uso (`--stay-awake`).
  * **Modo Desktop / DeX:** Ativa flags de redimensionamento e janelas livres no Android.
* **Salvamento Automático:** Lembra suas preferências, último IP e portas no arquivo `settings.json`.

---

## 📋 Pré-requisitos

1. **Python 3.10+** instalado no Windows (certifique-se de marcar *"Add Python to PATH"* durante a instalação).
2. Smartphone Android com **Depuração Sem Fio** (Android 11 ou superior) ou **Depuração USB** ativada nas *Opções do Desenvolvedor*.

---

## 🚀 Instalação e Execução

### Método Rápido (Recomendado)
Dê um duplo clique no arquivo:
```cmd
executar_sm0.bat
```
*(O script verifica as dependências e inicia o SM0 automaticamente)*

### Método Manual via Terminal
1. Instale a dependência:
   ```powershell
   pip install -r requirements.txt
   ```
2. Inicie a aplicação:
   ```powershell
   python main.py
   ```

---

## 📱 Guia de Conexão Sem Fio (Passo a Passo)

### 1. No Celular (Conectado na mesma rede Wi-Fi que o PC)
1. Acesse: **Configurações** > **Opções do desenvolvedor** > **Depuração sem fio**.
2. Ative a chave **Depuração sem fio**.
3. Observe o **Endereço IP e porta principal** (ex: `192.168.3.83:38171`).

### 2. Primeiro Pareamento (Se for o primeiro acesso no computador)
1. No celular, toque em **"Parear dispositivo com código de pareamento"**.
2. Uma janela popup exibirá:
   * **Porta de pareamento** (ex: `33179`).
   * **Código de pareamento Wi-Fi de 6 dígitos** (ex: `759166`).
3. No **SM0**, preencha o **IP**, a **Porta Conexão**, a **Porta Parear** e o **PIN**.
4. Clique em **"▶ Conectar e Espelhar"**.

### 3. Conexões Futuras
* O pareamento fica salvo no celular! Nas próximas vezes, basta conferir o **IP** e a **Porta Conexão (Principal)** na tela de Depuração sem fio do celular e clicar em **"▶ Conectar e Espelhar"** (os campos de PIN podem ficar em branco).

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
├── main.py              # Interface gráfica CustomTkinter e lógica de controle
├── executar_sm0.bat     # Inicializador automático para Windows
├── requirements.txt     # Dependências Python (customtkinter)
├── settings.json        # Configurações salvas (gerado automaticamente)
├── README.md            # Documentação da aplicação
└── scrcpy/             # Binários embutidos do scrcpy 3.x e ADB
    ├── scrcpy.exe
    ├── adb.exe
    ├── scrcpy-server
    └── ... (DLLs auxiliares)
```
