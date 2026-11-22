# Painel de administração comercial (protótipo isolado)

O arquivo `index.html` é uma interface estática para a API em
`commercial/admin_api.py`. Não faz parte do Winamp e não foi publicado
em produção.

## Implantação futura
- Servir o painel e a API **na mesma origem HTTPS**, sob acesso administrativo
  restrito, com proxy que encaminhe `/admin/rights` e `/health` para a API.
  O painel aceita a URL base da origem. Não habilitar CORS irrestrito.
- Configurar `AGGILLI_COMMERCIAL_ADMIN_TOKEN` com segredo aleatório de 32+
  caracteres e `AGGILLI_COMMERCIAL_DATA_DIR` fora da raiz web.
- Executar a API como usuário não privilegiado com permissões exclusivas
  de escrita no diretório de dados; proteger arquivos de auditoria e backups.
- Configurar HTTPS, controle de acesso administrativo, rate limiting,
  backups e monitoramento antes de uso real.
- Tokens ficam somente na memória da página; nunca no HTML, URL, cookies,
  localStorage ou repositório. Fechar a página encerra a sessão.
- Para lançamento comercial, migrar do token compartilhado para identidade
  individual, MFA e auditoria por administrador.

**Atenção:** cadastrar uma licença nesta interface não desbloqueia áudio
no player público. A API de reprodução com autorização server-side ainda
não foi implementada. Não publicar o acervo atual como catálogo comercial.
