# Integração nativa no player Winamp existente

## Decisão de produto

Não criar segundo player, nova página ou mudança no layout aprovado. Integrar faixas AzuraCast e arquivos Nextcloud MP3/MP4 na **mesma lista**, com os mesmos controles de navegação, busca, shuffle, gêneros e estado de reprodução.

## Biblioteca padrão

A **Aggilli Nuvem (Nextcloud WebDAV)** é a origem padrão da biblioteca exibida no player. Pasta configurada no servidor: `https://nuvem.aggillintelligence.com.br/remote.php/dav/files/aggilli-admin/musica/`.

- Ao abrir, carregar primeiro o catálogo da nuvem; mesclar em seguida as faixas existentes do AzuraCast na mesma lista, sem removê-las.
- A navegação, busca, reprodução e shuffle funcionam sobre a biblioteca unificada; a nuvem é a origem preferencial quando houver itens equivalentes, mas não excluir duplicatas automaticamente.
- Se o Nextcloud estiver indisponível, continuar mostrando o catálogo AzuraCast existente e informar discretamente a indisponibilidade da nuvem.
- O botão de upload e as credenciais administrativas permanecem separados da reprodução pública.
- Não montar WebDAV diretamente como volume de mídia do AzuraCast, nem migrar arquivos em produção sem testes.

## Modelo de faixa

Cada item recebe ID estável e fonte explícita:

- `source: "azuracast"`, `format: "mp3"`, `download_url` existente.
- `source: "nextcloud"`, `format: "mp3" | "mp4"`, `filename` e `etag` (somente no backend quando apropriado).

IDs da nuvem devem usar namespace `cloud:` para evitar colisão com IDs do AzuraCast. Exibir origem e indicador de vídeo discretamente na linha existente, sem mudar as colunas.

## Reprodução

- MP3 e rádio continuam usando o elemento `audio#audio` e seu Web Audio EQ/Spectrum existentes.
- MP4 com vídeo utiliza elemento `video` oculto por padrão, exibido **dentro do bloco `section.player`**, sem abrir modal ou nova página.
- Ao trocar de fonte, pausar o elemento anterior, remover a origem anterior e preservar o estado da fila.
- Controles play/pause, seek, anterior/próxima, stop e shuffle devem agir sobre o elemento ativo.
- Volume e mute devem acompanhar o elemento ativo; Web Audio EQ e Spectrum precisam de conexão ao áudio do vídeo ou fallback documentado, sem duplicar saídas sonoras.
- `preload="metadata"` e `playsinline` para vídeo. Não baixar MP4 inteiro antes de iniciar.
- `canPlayType` e erros de decodificação devem resultar em mensagem amigável, sem travar a fila.
- Não permitir reprodução simultânea do vídeo, do áudio e da rádio.

## Catálogo e segurança

- Endpoint de catálogo deve ser servido pelo backend e fazer PROPFIND autenticado no Nextcloud; nunca enviar senha ou token ao navegador.
- Player público exige política de autorização própria para catálogo e streaming; **não reutilizar a senha administrativa Basic como credencial de todos os ouvintes**.
- Validar permissões por faixa e uso autorizado do acervo antes de expor a biblioteca.
- Suportar Range 206 e conexões persistentes; limitar concorrência e timeouts.
- ETag para atualização incremental do catálogo. Não excluir ou mover arquivos originais.
- Evitar dados sensíveis no HTML ou no JSON público.

## Entrega incremental

1. Criar testes para unificação de IDs e controle de mídia ativa.
2. Implementar catálogo agregado no backend com acesso autenticado de teste.
3. Integrar vídeo embutido na UI da branch de desenvolvimento, preservando o HTML/CSS aprovado.
4. Testar reprodução, seek, troca entre MP3/MP4/rádio, shuffle, EQ, Spectrum e dispositivos móveis.
5. Resolver autorização de ouvintes e publicar somente após validação.

A branch atual não altera produção.
