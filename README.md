# Aggilli Streaming

Projeto Aggilli Music e Aggilli Radio.

## Componentes
- `player/`: interface web do Aggilli Music
- `backend/`: API FastAPI para upload autenticado de MP3
- `infra/apache/`: exemplos de configuração Apache
- `infra/systemd/`: unidades do serviço de upload

## Tecnologias
Debian, Apache, FastAPI, Uvicorn, AzuraCast e Tailscale.

## Segurança
Credenciais, certificados, dados de produção e músicas não
fazem parte deste repositório.

## Estado atual
Upload autenticado de MP3 testado com sucesso.
Atualização automática do catálogo ainda pendente.

As configurações de infraestrutura são referências do ambiente
existente e devem ser revisadas antes de reutilização.
