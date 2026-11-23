import os
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / "scripts" / "host-icecast-station.sh").read_text(encoding="utf-8")
ICECAST_PY, CADDY_PY = re.findall(r"<<'PY'\n(.*?)\nPY\n", SCRIPT, re.S)

DEBIAN_ICECAST = """<icecast>
    <location>Earth</location>
    <admin>icemaster@localhost</admin>
    <limits><clients>100</clients><sources>2</sources></limits>
    <authentication>
        <!-- Sources log in with username 'source' -->
        <source-password>hackme</source-password>
        <relay-password>hackme</relay-password>
        <admin-user>admin</admin-user>
        <admin-password>hackme</admin-password>
    </authentication>
    <hostname>localhost</hostname>
    <listen-socket><port>8000</port></listen-socket>
</icecast>
"""
CADDY = """{
\tauto_https disable_redirects
}

https://radio.aggillintelligence.com.br {
\tbind 2804:13b0:25:6581:2e0:4cff:fe02:8101
\ttls /etc/caddy/certs/radio-fullchain.pem /etc/caddy/certs/radio-privkey.pem
\treverse_proxy 127.0.0.1:8080
}
"""


class HostIcecastStationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name)
        (self.path / "icecast.xml").write_text(DEBIAN_ICECAST, encoding="utf-8")
        (self.path / "Caddyfile").write_text(CADDY, encoding="utf-8")

    def tearDown(self):
        self.dir.cleanup()

    def icecast(self, *extra):
        p = self.path
        subprocess.run([sys.executable, "-I", "-", str(p / "icecast.xml"), str(p / "out.xml"), "novaesperanca",
                        "Rádio Nova Esperança FM 106,3", "radio.aggillintelligence.com.br",
                        str(p / "station.env"), str(p / "admin.env"), *extra],
                       input=ICECAST_PY, text=True, check=True)
        (p / "out.xml").replace(p / "icecast.xml")
        return ET.parse(p / "icecast.xml").getroot()

    def env(self, name):
        return dict(l.split("=", 1) for l in (self.path / name).read_text(encoding="utf-8").splitlines()
                    if "=" in l and not l.startswith("#"))

    def test_default_passwords_are_replaced_and_kept_private(self):
        root = self.icecast()
        for tag in ("source-password", "relay-password", "admin-password"):
            value = root.findtext("authentication/" + tag)
            self.assertNotEqual(value, "hackme")
            self.assertEqual(len(value), 24)
        self.assertEqual(oct((self.path / "admin.env").stat().st_mode & 0o777), "0o600")
        self.assertIn("Sources log in", (self.path / "icecast.xml").read_text(encoding="utf-8"))

    def test_station_mount_has_its_own_password(self):
        root = self.icecast()
        mount = next(m for m in root.findall("mount") if m.findtext("mount-name") == "/novaesperanca")
        station = self.env("station.env")
        self.assertEqual(mount.findtext("username"), "source")
        self.assertEqual(mount.findtext("password"), station["PASSWORD"])
        self.assertNotEqual(station["PASSWORD"], root.findtext("authentication/source-password"))
        self.assertEqual(mount.findtext("stream-name"), "Rádio Nova Esperança FM 106,3")
        self.assertEqual(root.findtext("hostname"), "radio.aggillintelligence.com.br")
        self.assertEqual(oct((self.path / "station.env").stat().st_mode & 0o777), "0o600")

    def test_rerun_keeps_password_and_rotate_changes_it(self):
        self.icecast()
        first = self.env("station.env")["PASSWORD"]
        root = self.icecast()
        self.assertEqual(self.env("station.env")["PASSWORD"], first)
        self.assertEqual(len([m for m in root.findall("mount") if m.findtext("mount-name") == "/novaesperanca"]), 1)
        self.icecast("--rotate")
        self.assertNotEqual(self.env("station.env")["PASSWORD"], first)

    def test_caddy_routes_listeners_and_listens_on_the_lan_ip(self):
        for _ in range(2):  # idempotente
            subprocess.run([sys.executable, "-I", "-", str(self.path / "Caddyfile"), "novaesperanca",
                            "radio.aggillintelligence.com.br", "172.16.100.13"],
                           input=CADDY_PY, text=True, check=True)
        text = (self.path / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn("\tbind 2804:13b0:25:6581:2e0:4cff:fe02:8101 172.16.100.13\n", text)
        self.assertEqual(text.count("reverse_proxy /novaesperanca 127.0.0.1:8000 {"), 1)
        self.assertLess(text.index("reverse_proxy /novaesperanca"), text.index("reverse_proxy 127.0.0.1:8080"))
        self.assertIn("flush_interval -1", text)

    def test_script_backs_up_and_restores(self):
        self.assertIn('cp -p "$icecast_conf" "$backups/icecast.xml-$stamp"', SCRIPT)
        self.assertIn("trap restore ERR", SCRIPT)
        self.assertIn('caddy validate --config "$caddyfile"', SCRIPT)


if __name__ == "__main__":
    unittest.main()
