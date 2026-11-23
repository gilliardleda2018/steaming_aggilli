#!/usr/bin/env bash
# Hospeda uma rádio externa no Icecast próprio do servidor (porta 8000), fazendo o
# papel de provedor de streaming: o Oddcast/ZaraRadio da rádio envia o áudio para
# cá e os ouvintes ouvem por https://radio.aggillintelligence.com.br/<ponto>.
#
#   su - -c 'bash /caminho/scripts/host-icecast-station.sh novaesperanca "Rádio Nova Esperança FM 106,3"'
#   ... --rotate   gera uma senha nova de transmissão para o ponto
#
# - Faz cópia do icecast.xml e do Caddyfile antes de mudar e volta atrás se algo falhar.
# - Troca as senhas padrão do Icecast ("hackme"), se ainda existirem.
# - A senha de transmissão aparece só neste terminal e fica em
#   /etc/aggilli-music/hosted-stations/<ponto>.env (root, 0600). Nunca a copie para o Git ou para conversas.
# - Não mexe no AzuraCast, na Aggilli Radio, no player nem no catálogo.
set -Eeuo pipefail
umask 077

readonly icecast_conf=/etc/icecast2/icecast.xml
readonly caddyfile=/etc/caddy/Caddyfile
readonly public_host=radio.aggillintelligence.com.br
readonly lan_ip=172.16.100.13
readonly state_dir=/etc/aggilli-music/hosted-stations
readonly admin_env=/etc/aggilli-music/icecast-admin.env
readonly backups=/var/backups/aggilli-music

[[ $EUID -eq 0 ]] || { echo "Rode como root (su - -c '...')." >&2; exit 1; }
mount=${1:-}; name=${2:-}; rotate=${3:-}
[[ $mount =~ ^[a-z0-9][a-z0-9-]{1,30}$ ]] || { echo "Ponto inválido: use letras minúsculas, números e hífen (ex.: novaesperanca)." >&2; exit 1; }
[[ -n $name && ${#name} -le 80 ]] || { echo "Informe o nome da rádio (até 80 caracteres)." >&2; exit 1; }
[[ -z $rotate || $rotate == --rotate ]] || { echo "Terceiro argumento aceito: --rotate" >&2; exit 1; }
for file in "$icecast_conf" "$caddyfile"; do [[ -f $file && ! -L $file ]] || { echo "Arquivo ausente: $file" >&2; exit 1; }; done

install -d -m 0700 "$backups" "$state_dir"
stamp=$(date +%Y%m%d-%H%M%S)
cp -p "$icecast_conf" "$backups/icecast.xml-$stamp"
cp -p "$caddyfile" "$backups/Caddyfile-$stamp"
restore() {
  echo "Falhou; restaurando as cópias de $stamp." >&2
  cp -p "$backups/icecast.xml-$stamp" "$icecast_conf"
  cp -p "$backups/Caddyfile-$stamp" "$caddyfile"
  systemctl restart icecast2 || true
  systemctl reload caddy || true
}
trap restore ERR

station_env="$state_dir/$mount.env"
new_config=$(mktemp)
# Python lê/escreve o XML preservando comentários; senhas só vão para arquivos 0600 e para stdout no fim.
python3 -I - "$icecast_conf" "$new_config" "$mount" "$name" "$public_host" "$station_env" "$admin_env" "${rotate:-}" <<'PY'
import os, secrets, string, sys
import xml.etree.ElementTree as ET

src, dst, mount, name, host, station_env, admin_env = sys.argv[1:8]
rotate = sys.argv[8] if len(sys.argv) > 8 else ""
alphabet = string.ascii_letters + string.digits   # sem símbolos: o Oddcast aceita sem escapes
new_secret = lambda: "".join(secrets.choice(alphabet) for _ in range(24))

def read_env(path):
    try:
        with open(path, encoding="utf-8") as f:
            return dict(l.rstrip("\n").split("=", 1) for l in f if "=" in l and not l.startswith("#"))
    except FileNotFoundError:
        return {}

def write_env(path, values, header):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(header + "\n" + "".join(f"{k}={v}\n" for k, v in values.items()))

tree = ET.parse(src, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
root = tree.getroot()
def child(parent, tag):
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    return node

# Senhas padrão do pacote Debian ("hackme") deixam qualquer um transmitir ou administrar.
auth = child(root, "authentication")
admin = read_env(admin_env)
changed_admin = False
for tag in ("source-password", "relay-password", "admin-password"):
    node = child(auth, tag)
    if not node.text or node.text.strip() in ("hackme", ""):
        node.text = new_secret()
        admin[tag.upper().replace("-", "_")] = node.text
        changed_admin = True
if changed_admin:
    write_env(admin_env, admin, "# Icecast próprio (porta 8000) - senhas de administração. Não compartilhe.")

child(root, "hostname").text = host
limits = child(root, "limits")
child(limits, "clients").text = "300"
child(limits, "sources").text = "6"

# Ponto exclusivo da rádio hospedada, com senha própria (usuário "source", como no Oddcast).
path = "/" + mount
station = read_env(station_env)
password = station.get("PASSWORD") if rotate != "--rotate" else None
password = password or new_secret()
node = next((m for m in root.findall("mount") if (m.findtext("mount-name") or "") == path), None)
if node is None:
    node = ET.SubElement(root, "mount", {"type": "normal"})
for tag, value in (("mount-name", path), ("username", "source"), ("password", password),
                   ("max-listeners", "250"), ("stream-name", name), ("public", "0")):
    child(node, tag).text = value
write_env(station_env, {"MOUNT": path, "NAME": name, "PASSWORD": password},
          "# Rádio hospedada no Icecast próprio. Não compartilhe a senha fora do Oddcast da rádio.")
tree.write(dst, encoding="utf-8", xml_declaration=True)
PY
install -o root -g icecast -m 0640 "$new_config" "$icecast_conf"
rm -f "$new_config"

# Ouvintes em HTTPS pelo domínio público; o Caddy também passa a escutar no IP da rede local,
# para o encaminhamento IPv4 do roteador.
python3 -I - "$caddyfile" "$mount" "$public_host" "$lan_ip" <<'PY'
import re, sys
path, mount, host, lan = sys.argv[1:5]
text = open(path, encoding="utf-8").read()
start = text.index(f"https://{host} {{")
end = text.index("\n}", start)
block = text[start:end]
bind = re.search(r"^\tbind ([^\n]+)$", block, re.M)
if bind and lan not in bind.group(1).split():
    block = block.replace(bind.group(0), bind.group(0) + " " + lan, 1)
route = f"\treverse_proxy /{mount} 127.0.0.1:8000 {{\n\t\tflush_interval -1\n\t}}\n"
if f"reverse_proxy /{mount} " not in block:
    block = block.replace("\treverse_proxy 127.0.0.1:8080", route + "\treverse_proxy 127.0.0.1:8080", 1)
open(path, "w", encoding="utf-8").write(text[:start] + block + text[end:])
PY
caddy validate --config "$caddyfile" --adapter caddyfile >/dev/null

systemctl restart icecast2
systemctl reload caddy
sleep 2
curl -fsS -m 5 http://127.0.0.1:8000/status-json.xsl >/dev/null
curl -fsS -m 5 -o /dev/null https://$public_host/ 2>/dev/null || curl -fsS -m 5 -o /dev/null --resolve "$public_host:443:$lan_ip" "https://$public_host/"
trap - ERR

MOUNT=$(sed -n 's/^MOUNT=//p' "$station_env")
PASSWORD=$(sed -n 's/^PASSWORD=//p' "$station_env")
cat <<EOF

Rádio hospedada pronta: $name
Cópias de segurança: $backups/*-$stamp

Dados para o Oddcast da rádio (só no computador deles):
  Server Type : Icecast
  Server IP   : $public_host
  Server Port : 8000
  Mount point : $MOUNT
  Password    : $PASSWORD
  Encoder     : MP3, 96 kbps, 44100 Hz, estéreo (como já usam)

Endereço para os ouvintes: https://$public_host$MOUNT
Não cole a senha em conversas; para trocar: rode de novo com --rotate.
EOF
if [[ -f $admin_env ]]; then echo "Senhas de administração do Icecast: $admin_env (root, 0600)."; fi
if command -v nft >/dev/null && ! nft list ruleset 2>/dev/null | grep -q "dport 8000"; then
  echo "Aviso: confira se o firewall libera a porta 8000/TCP (não encontrei regra explícita no nftables)."
fi
