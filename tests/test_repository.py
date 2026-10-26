"""Keep onboarding links and the dependency-free scaffold usable."""

from pathlib import Path
import re
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_onboarding_local_links_exist(self):
        for relative in ["README.md", "CONTRIBUTING.md", "docs/ARCHITECTURE.md",
                         "docs/NCM_INTEGRATION.md", "docs/ROADMAP.md"]:
            doc = ROOT / relative
            for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                path = target.split("#", 1)[0]
                with self.subTest(document=relative, target=target):
                    self.assertTrue((doc.parent / path).exists())

    def test_package_has_no_model_dependencies(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual(config["project"]["dependencies"], [])

    def test_example_config_parses_as_toml(self):
        config = tomllib.loads((ROOT / "configs/worker.example.toml").read_text())
        self.assertEqual(config["backend"]["backend"], "ncm")


if __name__ == "__main__":
    unittest.main()
