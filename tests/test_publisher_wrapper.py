import os
import subprocess
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
WRAPPER = SCRIPTS / "aggilli-publish-player"
INSTALLER = SCRIPTS / "install-publisher.sh"


def run(*args):
    return subprocess.run(["bash", str(WRAPPER), *args], capture_output=True, text=True)


class PublisherWrapperTests(unittest.TestCase):
    def test_rejects_missing_or_malformed_revision(self):
        for args in ((), ("main",), ("HEAD~1",), ("abc",), ("3da6199; id",)):
            with self.subTest(args=args):
                self.assertEqual(run(*args).returncode, 2)

    @unittest.skipIf(os.geteuid() == 0, "requires an unprivileged user")
    def test_requires_root_for_valid_revision(self):
        self.assertEqual(run("3da6199").returncode, 1)

    def test_runs_pinned_publisher_only_for_branch_commits(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("readonly publisher=/usr/local/lib/aggilli/publish-player.sh", source)
        self.assertIn('git merge-base --is-ancestor "$commit" "origin/$branch"', source)
        self.assertIn('exec "$publisher" "$commit"', source)

    def test_sudoers_rule_allows_only_the_wrapper(self):
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('rule="$user ALL=(root) NOPASSWD: /usr/local/sbin/aggilli-publish-player"', source)
        self.assertIn('visudo -cf "$tmp"', source)


if __name__ == "__main__":
    unittest.main()
