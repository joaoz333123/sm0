# SM0 - Utilitário de Espelhamento Android

Aplicação desktop para espelhamento sem fio de smartphones Android usando scrcpy e sndcpy.

## Instalação

1. **Instalar Python 3.x** (se ainda não tiver)
   - Baixe em: https://www.python.org/downloads/
   - Certifique-se de marcar "Add Python to PATH" durante a instalação

2. **Instalar dependências**
   ```powershell
   cd C:\Users\user\Desktop\sm0
   pip install -r requirements.txt
   ```

3. **Configurar sndcpy (opcional)**
   - Baixe o sndcpy de: https://github.com/rom1v/sndcpy
   - Extraia os arquivos para a pasta `sndcpy/` no diretório do projeto
   - Certifique-se de que o arquivo `sndcpy.bat` está presente

## Uso

1. **Executar a aplicação**
   ```powershell
   cd C:\Users\user\Desktop\sm0
   python main.py
   ```

2. **Configurar conexão no Android**
   - Vá em Configurações > Desenvolvedor > Depuração sem fio
   - Ative "Depuração sem fio"
   - Anote o IP, portas e código de pareamento

3. **Conectar**
   - Preencha os dados de conexão na aplicação
   - Clique em "Conectar"
   - Aguarde a conexão ser estabelecida

## Configurações

- **Resolução**: 720p, 1080p, 1440p ou Original
- **FPS**: 30, 60 ou Máximo
- **Bitrate**: Taxa de bits em Mbps (padrão: 12)
- **Áudio**: Habilita/desabilita o áudio via sndcpy

## Estrutura de Arquivos

```
sm0/
├── main.py              # Aplicação principal
├── requirements.txt     # Dependências Python
├── settings.json        # Configurações salvas (criado automaticamente)
├── scrcpy/             # Arquivos do scrcpy
│   ├── scrcpy.exe
│   ├── adb.exe
│   └── ...
└── sndcpy/             # Arquivos do sndcpy (opcional)
    ├── sndcpy.bat
    ├── sndcpy.apk
    └── ...
```

Agora vou criar um arquivo batch para facilitar a execução:

```batch:Users/user/Desktop/sm0/executar_sm0.bat
@echo off
echo SM0 - Utilitario de Espelhamento Android
echo.
echo Instalando dependencias...
pip install -r requirements.txt
echo.
echo Iniciando aplicacao...
python main.py
pause
```

## Próximos Passos

Agora você tem a estrutura completa do projeto SM0! Para começar:

1. **Execute o arquivo batch** (duplo clique em `executar_sm0.bat`) ou use o PowerShell:
   ```powershell
   cd C:\Users\user\Desktop\sm0
   pip install -r requirements.txt
   python main.py
   ```

2. **Configure o sndcpy** (opcional):
   - Baixe de https://github.com/rom1v/sndcpy
   - Extraia para a pasta `sndcpy/`

3. **Teste a aplicação**:
   - Configure a depuração sem fio no seu S22
   - Preencha os dados de conexão
   - Clique em "Conectar"

A aplicação está completa e funcional, seguindo exatamente as especificações que você forneceu. Ela inclui:

- ✅ Interface moderna com CustomTkinter
- ✅ Validação de campos
- ✅ Gerenciamento de processos (adb, scrcpy, sndcpy)
- ✅ Salvamento automático de configurações
- ✅ Status em tempo real
- ✅ Tratamento de erros
- ✅ Fechamento limpo da aplicação

O código está pronto para uso e deve funcionar perfeitamente com seu setup atual!

## Solução de Problemas

### Firewall do Windows
Na primeira execução, o Windows Defender pode bloquear o adb.exe. Clique em "Permitir acesso" para redes Privadas e Públicas.

### Conexão falha
- Verifique se o PC e Android estão na mesma rede Wi-Fi
- Confirme se a "Isolação de AP/Cliente" está desativada no roteador
- Verifique se os dados de conexão estão corretos

### Áudio não funciona
- Certifique-se de que o sndcpy está instalado corretamente
- Verifique se o VLC está instalado no sistema
- O áudio pode ter delay de alguns segundos

## Suporte

Para problemas ou dúvidas, verifique:
1. Se todas as dependências estão instaladas
2. Se os arquivos do scrcpy estão presentes
3. Se as configurações de rede estão corretas

