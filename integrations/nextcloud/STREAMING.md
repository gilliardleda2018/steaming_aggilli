# Streaming direto da Aggilli Nuvem — protótipo

O módulo `backend/cloud_stream.py` adiciona um roteador FastAPI **ainda não ativado** para entregar MP3/MP4 diretamente do Nextcloud ao navegador por meio do backend Aggilli.

## Otimizações

- Suporte a `Range: bytes=...` para seek e reprodução progressiva (`206 Partial Content`).
- Transmissão em blocos de 128 KiB; o servidor não precisa armazenar um MP4 inteiro.
- `HEAD` para consultar metadados.
- URL WebDAV e credenciais permanecem no servidor; nunca no JavaScript do player.
- Sem cópia permanente de vídeos ou conversão durante a reprodução.
- Somente arquivos de um componente de caminho com extensão MP3/MP4.
- Acesso administrativo obrigatório, herdado de `require_upload_auth`.

## Limitações e verificações antes de ativar

1. O código **não foi testado** contra o Nextcloud real nem em navegador.
2. O roteador **não está montado** em `backend/main.py`; nenhuma rota nova foi exposta.
3. O acesso usa autenticação administrativa por arquivo. **Não usar esta rota para um player público** sem desenhar autorização de ouvintes (ex.: sessões/URLs assinadas e de curta duração).
4. O WebDAV precisa suportar byte ranges; testar `HEAD`, `206`, seek e consumo de banda.
5. O navegador só reproduz MP4 com codecs compatíveis; MP4 é contêiner, não garantia de codec suportado.
6. O AzuraCast não foi alterado; transmissão de rádio exigirá pipeline separado de extração de áudio, sem conversão on-the-fly para cada ouvinte.
7. Validar limites de conexões, timeouts, proxy buffering, logs e tamanho máximo de arquivos antes de disponibilizar externamente.
8. Configurar `AGGILLI_WEBDAV_USER` e `AGGILLI_WEBDAV_APP_PASSWORD` no ambiente privado do serviço; **não comitar valores**.

## Próxima fase

Testes automatizados com HTTPX mock, teste de streaming `Range` autenticado e desenho de acesso ao player. Manter `main` e produção inalteradas até validação.
