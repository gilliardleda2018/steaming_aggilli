# Prévia do Aggilli Music unificado (Debian)

A APK Android carrega `https://server.taila400aa.ts.net/music/`. Portanto,
um build novo da APK não atualiza automaticamente a interface do servidor.

Para inspecionar a interface nova **sem sobrescrever produção**:

1. Atualize o clone do repositório no Debian para a branch
   `feat/nextcloud-webdav-sync` após confirmar que não há alterações locais
   que possam ser perdidas. Evite `git reset --hard`.
2. Execute como root:
   `bash /home/gilliard/projetos/steaming_aggilli/scripts/preview-unified-player.sh`
3. Inicie o servidor temporário local:
   `cd /var/www/aggilli-music-preview && python3 -m http.server 8765 --bind 127.0.0.1`
4. Abra `http://127.0.0.1:8765/` no navegador do próprio Debian, ou utilize
   túnel SSH se estiver em outro computador.

Esta prévia mostra layout, fila e DJ local, com cópia do índice do catálogo
público. **Não replica os endpoints de reprodução/upload**, portanto pode não
tocar áudio. Não é uma implantação nem substitui o player em produção.

Antes de publicar em `/music/`, testar reprodução, rádio, catálogo, volume,
busca, equalizador, Media Session, Android e sincronização. A implantação deve
criar backup do `index.html` atual e ter rollback pronto.
