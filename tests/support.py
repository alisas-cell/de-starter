from pathlib import Path
import shutil

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
SKILL_SCRIPTS = REPO_ROOT / "skills" / "de-starter" / "scripts"


def copy_fixture(name: str, destination: Path) -> Path:
    target = destination / name
    shutil.copytree(FIXTURES / name, target)
    return target
