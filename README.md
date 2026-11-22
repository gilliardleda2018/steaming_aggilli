# Aggilli Streaming

Projeto que reúne o **Aggilli Music** (player web) e a infraestrutura de **Aggilli Radio**.

## Componentes previstos

- `player/`: interface web, reprodução, equalizador e catálogo
- `backend/`: API FastAPI para upload autenticado de MP3
- `infra/apache/`: configurações de proxy
- `infra/systemd/`: unidades do serviço de upload

## Situação do repositório

A estrutura inicial e as regras de exclusão foram criadas. **O código em produção ainda precisa ser importado do servidor Debian**, após revisão de segredos e dados sensíveis.

## Segurança

Não publicar músicas, credenciais do AzuraCast, hashes de senhas, tokens, certificados, chaves privadas ou arquivos de ambiente.

## Implantação

O player e a API estão atualmente hospedados fora deste repositório. Não utilizar este repositório como fonte de deploy até a importação e validação dos arquivos reais.
