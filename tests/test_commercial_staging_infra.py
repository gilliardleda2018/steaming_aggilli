import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra" / "commercial"
SERVICE = (INFRA / "aggilli-commercial-staging.service").read_text(encoding="utf-8")
SOCKET = (INFRA / "aggilli-commercial-staging.socket").read_text(encoding="utf-8")
ENV = (INFRA / "commercial-staging.env.example").read_text(encoding="utf-8")
APACHE = (ROOT / "infra" / "apache" / "aggilli-music-commercial-staging.conf").read_text(encoding="utf-8")
INSTALLER = (ROOT / "scripts" / "install-commercial-staging.sh").read_text(encoding="utf-8")
TOKEN = (ROOT / "scripts" / "commercial-staging-login.sh").read_text(encoding="utf-8")


class CommercialStagingInfraTests(unittest.TestCase):
    def test_service_runs_unprivileged_and_hardened(self):
        for line in ("User=aggilli-commercial", "NoNewPrivileges=true", "ProtectSystem=strict",
                     "ProtectHome=true", "EnvironmentFile=/etc/aggilli-music/commercial-staging.env",
                     "ExecStart=/opt/aggilli-commercial/venv/bin/python -m uvicorn commercial.listener_api:app --fd 3"):
            with self.subTest(line=line):
                self.assertIn(line, SERVICE)

    def test_socket_is_reachable_only_by_apache_group(self):
        self.assertIn("ListenStream=/run/aggilli-commercial/api.sock", SOCKET)
        self.assertIn("SocketGroup=www-data", SOCKET)
        self.assertIn("SocketMode=0660", SOCKET)

    def test_ani_starts_disabled_and_template_has_no_secrets(self):
        self.assertIn("AGGILLI_ANI_ENABLED=false", ENV)
        self.assertIn("AGGILLI_ANI_PROVIDER=anthropic", ENV)
        self.assertIn("AGGILLI_ANI_MODEL=claude-opus-5-5", ENV)
        for key in ("ANTHROPIC_API_KEY=", "AGGILLI_ANI_CHAT_URL=", "AGGILLI_ANI_API_KEY="):
            line = next(l for l in ENV.splitlines() if l.startswith(key))
            self.assertEqual(line, key)

    def test_staging_venv_pins_the_anthropic_sdk(self):
        requirements = (INFRA / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("anthropic==2.12.0", requirements)

    def test_route_is_same_origin_as_player(self):
        self.assertIn('<Location "/music/commercial-api/">', APACHE)
        self.assertIn('ProxyPass "unix:/run/aggilli-commercial/api.sock|http://localhost/"', APACHE)

    def test_installer_never_overwrites_credentials_and_rolls_back(self):
        self.assertIn('if [[ ! -e $env_file ]]; then', INSTALLER)
        self.assertIn('chmod 0600 "$env_file"', INSTALLER)
        self.assertIn("if ! apache2ctl -t; then rollback_apache; exit 1; fi", INSTALLER)
        self.assertIn('git -C "$repo" merge-base --is-ancestor "$commit" "origin/$branch"', INSTALLER)

    def test_token_helper_reads_password_without_echo_or_argv(self):
        self.assertIn("read -r -s -p", TOKEN)
        self.assertIn('3<<<"$email"$\'\\n\'"$password"', TOKEN)


class AniSetupAssistantTests(unittest.TestCase):
    SCRIPT = (ROOT / "scripts" / "configure-ani-staging.sh").read_text(encoding="utf-8")

    def test_key_is_read_without_echo_and_file_stays_root_only(self):
        self.assertIn('read -r -s -p "Chave da API da Anthropic', self.SCRIPT)
        self.assertIn('chown root:root "$tmp"; chmod 0600 "$tmp"', self.SCRIPT)
        self.assertIn('cp -p -- "$env_file" "$backup"', self.SCRIPT)

    def test_only_anthropic_keys_and_clean_model_names_are_accepted(self):
        self.assertIn("[[ $key == sk-ant-* && $key != *[[:space:]]* ]]", self.SCRIPT)
        self.assertIn("readonly default_model=claude-opus-5-5", self.SCRIPT)

    def test_validation_reports_engine_without_printing_the_key(self):
        self.assertIn('print("ANI VALIDADA: engine=ani"', self.SCRIPT)
        self.assertIn("except anthropic.AuthenticationError:", self.SCRIPT)
        self.assertNotIn("print(os.environ", self.SCRIPT)


if __name__ == "__main__":
    unittest.main()
