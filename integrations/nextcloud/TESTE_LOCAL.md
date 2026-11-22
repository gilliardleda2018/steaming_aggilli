# Teste isolado do streaming WebDAV

A aplicação `backend/cloud_test_app.py` monta as rotas `/cloud/{filename}` em um servidor FastAPI separado, **somente em loopback** (`127.0.0.1:8450`). Ela usa a autenticação administrativa existente e as credenciais WebDAV fornecidas em variáveis de ambiente. Não altera o AzuraCast, o Apache ou o player em produção.

## Preparação

Executar no Debian com o ambiente virtual já instalado:

```bash
cd /home/gilliard/projetos/steaming_aggilli
git pull --ff-only origin feat/nextcloud-webdav-sync
/home/gilliard/projetos/aggilli-music-upload/.venv/bin/python -m compileall -q backend
/home/gilliard/projetos/aggilli-music-upload/.venv/bin/python -m unittest discover -s tests -v
```

## Iniciar teste (terminal A)

A senha de aplicativo é solicitada sem eco; não compartilhe.

```bash
cd /home/gilliard/projetos/steaming_aggilli
read -r -s -p 'Senha de aplicativo Nextcloud: ' AGGILLI_WEBDAV_APP_PASSWORD
echo
export AGGILLI_WEBDAV_USER=aggilli-admin AGGILLI_WEBDAV_APP_PASSWORD
cd backend
/home/gilliard/projetos/aggilli-music-upload/.venv/bin/python -m uvicorn cloud_test_app:app --host 127.0.0.1 --port 8450
```

O servidor fica ativo até Ctrl+C. Execute somente em máquina confiável; variáveis de ambiente de processo devem ser tratadas como segredos.

## Testar intervalo (terminal B)

```bash
curl -sS -i --max-time 10 http://127.0.0.1:8450/health
```

Para testar a rota protegida, use `curl --user admin` e um nome MP4 codificado como URL. Solicite apenas 1024 bytes com `--range 0-1023`, `--max-filesize 2048`, `--output /dev/null`, `--dump-header -`. O resultado esperado é HTTP 206, Content-Range e Content-Length: 1024.

Não adicionar esta porta ao Apache, Caddy ou Tailscale. Não abrir firewall. Não mesclar o PR antes de verificar os resultados.
