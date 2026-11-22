@echo off
setlocal
REM Executar no Windows com OpenSSH instalado e acesso SSH ao Debian.
REM Solicita a senha SSH quando necessario. Nao armazena credenciais.
ssh gilliard@server "sudo /usr/local/bin/aggilli-nextcloud-sync"
if errorlevel 1 (
  echo Falha na sincronizacao. Verifique acesso SSH e permissao sudo.
  exit /b 1
)
echo Sincronizacao concluida.
