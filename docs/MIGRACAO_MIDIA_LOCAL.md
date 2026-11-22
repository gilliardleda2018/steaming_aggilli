# Retorno ao armazenamento local — Aggilli Music

Decisão: a biblioteca principal será uma pasta de mídia no próprio Debian, não o Nextcloud WebDAV. **Não implantar a branch de WebDAV em produção.**

## Caminhos propostos

- Origem no host: `/srv/aggilli-music/media/musicas` e `/srv/aggilli-music/media/videos`.
- URL pública planejada: `/music/media/musicas/` e `/music/media/videos/` (depende de configuração Apache a validar).
- Catálogo: gerado no servidor por varredura de MP3/MP4, com IDs estáveis e metadados seguros.
- Reprodução: arquivos estáticos com HTTP Range; vídeo embutido no Winamp, EQ e Spectrum Analyzer mantidos.
- Rádio AzuraCast e catálogo existente: independentes e preservados.
- Nextcloud: somente origem opcional de cópia/importação, nunca dependência da reprodução.

## Plano seguro de migração

1. Criar diretórios locais sem mover ou excluir arquivos existentes.
2. Copiar um MP3 e um MP4 como amostras, sem expor a biblioteca inteira.
3. Verificar espaço livre, permissões, acesso Apache e suporte a Range.
4. Implementar gerador de catálogo e testar na prévia.
5. Integrar à interface existente e validar EQ/Spectrum, navegação, seek e rádio.
6. Promover à produção apenas após revisão e testes; não apagar dados da nuvem.

## Segurança

Não disponibilizar automaticamente o conteúdo de uma pasta privada inteira na internet. Usar pasta de publicação dedicada, seleção explícita de mídia e regras de acesso adequadas. Evitar symlinks que permitam servir arquivos fora da pasta autorizada.
