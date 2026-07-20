import json
from pathlib import Path
import subprocess
from typing import List, Optional

from .models import ProjectFacts


def _node_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _git_dirty(root: Path) -> Optional[bool]:
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def detect_project(root: Path) -> ProjectFacts:
    git_present = (root / ".git").exists()
    package_path = root / "package.json"
    if package_path.exists():
        package = json.loads(package_path.read_text(encoding="utf-8"))
        dependencies = {
            **package.get("dependencies", {}),
            **package.get("devDependencies", {}),
        }
        kind = "node-next" if "next" in dependencies else "node"
        manager = _node_manager(root)
        scripts = package.get("scripts", {})
        commands = [
            f"{manager} {name}" if manager != "npm" else f"npm run {name}"
            for name in ("lint", "test", "build")
            if name in scripts
        ]
        return ProjectFacts(kind, manager, commands, git_present, _git_dirty(root))
    if (root / "pyproject.toml").exists():
        return ProjectFacts(
            "python", None, ["python3 -m unittest discover -v"],
            git_present, _git_dirty(root),
        )
    if (root / "index.html").exists():
        return ProjectFacts("static", None, [], git_present, _git_dirty(root))
    return ProjectFacts("generic", None, [], git_present, _git_dirty(root))
