import json
from pathlib import Path


def test_root_package_exposes_dev_production_and_check_scripts() -> None:
    package_json = Path(__file__).resolve().parents[3] / "package.json"
    scripts = json.loads(package_json.read_text(encoding="utf-8"))["scripts"]

    assert scripts["dev"]
    assert scripts["dev:backend"]
    assert scripts["dev:frontend"]
    assert scripts["build"]
    assert scripts["start"]
    assert scripts["check:backend"]
    assert scripts["check:frontend"]
    assert scripts["check"]
