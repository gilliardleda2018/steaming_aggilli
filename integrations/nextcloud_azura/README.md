# Nextcloud -> AzuraCast (somente importação)

Sincroniza arquivos MP3 de uma pasta WebDAV e extrai áudio MP3 de MP4 antes de enviar para a biblioteca da estação 1 do AzuraCast. Não remove nem altera arquivos na nuvem. Não altera o player, playlists ou serviços.

## Pré-requisitos
- Debian com `python3-httpx`, `ffmpeg` e chave de API do AzuraCast já existente em `/etc/aggilli-music/azuracast-api-key`.
- Pasta Nextcloud WebDAV padrão: `musicas/` (plural). Opcionalmente configure `AGGILLI_WEBDAV_FOLDER=musicas` no arquivo `/etc/aggilli-music/nextcloud-sync.env`.
- Conta WebDAV com senha de aplicativo; não colocar senha no Git.

## Instalação (root, depois de revisar o código)
```bash
apt-get install -y python3-httpx ffmpeg
install -m 600 /dev/null /etc/aggilli-music/nextcloud-sync.env
# Edite o arquivo com duas linhas:
# AGGILLI_WEBDAV_USER=...
# AGGILLI_WEBDAV_APP_PASSWORD=...
install -m 644 integrations/nextcloud_azura/aggilli-nextcloud-sync.service /etc/systemd/system/
install -m 644 integrations/nextcloud_azura/aggilli-nextcloud-sync.timer /etc/systemd/system/
systemctl daemon-reload
systemctl start aggilli-nextcloud-sync.service
journalctl -u aggilli-nextcloud-sync.service -n 50 --no-pager
# Só depois de validar:
systemctl enable --now aggilli-nextcloud-sync.timer
```

A execução manual via Windows BAT requer nome DNS/SSH correto e permissão para iniciar o serviço. O BAT é opcional: o timer no Debian automatiza a cada 15 minutos. Evite dar sudo irrestrito ao usuário; autorize somente o comando necessário.

## Limites e segurança
- Somente arquivos diretamente na pasta `musica/` (não recursivo).
- Upload máximo 100 MB após conversão, conforme o backend existente.
- Arquivos já presentes com o mesmo nome são ignorados, não substituídos.
- MP4 sem trilha de áudio falha sem modificar o original.
- O estado fica em `/var/lib/aggilli-music/nextcloud-azura-state.json`.
- Antes de ativar o timer, valide uma importação pequena e confira se a estação indexou a faixa.

## Diagnóstico do erro HTTP 403

O caminho antigo era `musica/` (singular). O novo padrão é `musicas/`.
O erro 403 também pode significar que a conta WebDAV não tem acesso à pasta
ou que a senha de aplicativo foi revogada. Não trocar credenciais nem afrouxar
permissões automaticamente.

Após atualizar o código no Debian, confirme que o serviço lê
`/etc/aggilli-music/nextcloud-sync.env` e inclua:

```ini
AGGILLI_WEBDAV_FOLDER=musicas
```

Para verificar sem mostrar senhas, execute como administrador:

```sh
systemctl cat aggilli-nextcloud-sync.service
systemctl start aggilli-nextcloud-sync.service
journalctl -u aggilli-nextcloud-sync.service -n 40 --no-pager
```

O sincronizador não faz exclusões remotas nem tenta a pasta antiga após um
403. **Commit no GitHub não atualiza automaticamente o script em execução
no Debian**; confirme a atualização local antes de reiniciar o serviço.
