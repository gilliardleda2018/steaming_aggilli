# Integração Aggilli Music com Nextcloud WebDAV

## Objetivo

Usar a pasta `musica` na Aggilli Nuvem como origem central de arquivos MP3, permitindo o envio remoto sem acesso SSH ao Debian.

## Endpoint

`https://nuvem.aggillintelligence.com.br/remote.php/dav/files/aggilli-admin/musica/`

O teste sem credenciais retornou HTTP 401 (autenticação necessária). **Acesso autenticado ainda não foi validado.**

## Estado desta branch

O script `list_music.py` faz uma consulta WebDAV `PROPFIND` com `Depth: 1`, lista apenas MP3 do nível atual e apresenta nome, tamanho e ETag. **Não grava, exclui, baixa ou importa músicas.** Subpastas ainda não são percorridas.

## Teste seguro no Debian

Crie uma senha de aplicativo no Nextcloud. Não compartilhe a senha no GitHub ou no chat.

```bash
cd /home/gilliard/projetos/steaming_aggilli
git fetch origin
git switch feat/nextcloud-webdav-sync
read -r -p 'Usuario Nextcloud: ' AGGILLI_WEBDAV_USER
read -r -s -p 'Senha de aplicativo: ' AGGILLI_WEBDAV_APP_PASSWORD
echo
export AGGILLI_WEBDAV_USER AGGILLI_WEBDAV_APP_PASSWORD
python3 integrations/nextcloud/list_music.py
unset AGGILLI_WEBDAV_APP_PASSWORD
```

O script usa apenas a biblioteca padrão do Python. O nome do usuário e a senha são lidos localmente e não são gravados em arquivos pelo script. Evite executar com `set -x` e não compartilhe a saída contendo nomes privados de músicas, caso necessário.

## Próximas etapas, somente após validação

1. Autenticar e validar leitura da pasta.
2. Adicionar paginação/recursão e validação de tamanho, formato e ETag.
3. Implementar sincronizador com estado persistente e idempotência, sem apagar arquivos.
4. Importar via API autenticada do AzuraCast e aguardar processamento.
5. Atualizar o catálogo do player após confirmação e executar testes de regressão.
6. Adicionar agendamento opcional por systemd timer.

**Não alterar mounts, volumes ou diretórios do AzuraCast em produção nesta fase.**
