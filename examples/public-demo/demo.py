#!/usr/bin/env python3
"""Create and inspect a sentinel-owned synthetic de-starter demo workspace."""

from pathlib import Path
from typing import Dict, Sequence
import argparse
import hashlib
import json
import os
import shutil
import sys


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[1]
SEED = DEMO_DIR / "seed"
SENTINEL = ".de-starter-public-demo.json"
BASELINE = "baseline-inventory.json"
_OWNED_TOP_LEVEL = {SENTINEL, BASELINE, "project", "run"}


def _sentinel_payload(workspace: Path) -> dict:
    return {
        "kind": "de-starter-public-demo",
        "version": 1,
        "workspace": str(workspace),
    }


def _safe_workspace_path(workspace: Path) -> Path:
    original = workspace.expanduser()
    if original.is_symlink():
        raise ValueError("refusing a symlink workspace")
    root = original.resolve()
    if root == Path(root.anchor):
        raise ValueError("refusing the filesystem root")
    if root == Path.home().resolve():
        raise ValueError("refusing the home directory")
    if root == REPO_ROOT or REPO_ROOT in root.parents:
        raise ValueError("refusing a workspace inside the repository")
    return root


def _atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise ValueError("temporary demo artifact already exists: " + str(temporary))
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def require_owned_workspace(workspace: Path) -> Dict[str, Path]:
    root = _safe_workspace_path(workspace)
    marker = root / SENTINEL
    if not marker.is_file() or marker.is_symlink():
        raise ValueError("public demo sentinel is missing")
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("public demo sentinel is invalid") from exc
    if payload != _sentinel_payload(root):
        raise ValueError("public demo sentinel workspace identity is invalid")
    project = root / "project"
    run_dir = root / "run"
    if project.parent != root or run_dir.parent != root:
        raise ValueError("public demo child boundary is invalid")
    if not project.is_dir() or project.is_symlink():
        raise ValueError("public demo project is missing or unsafe")
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise ValueError("public demo run directory is missing or unsafe")
    return {"workspace": root, "project": project, "run_dir": run_dir}


def inventory_project(workspace: Path) -> dict:
    owned = require_owned_workspace(workspace)
    project = owned["project"]
    files = {}
    directories = []
    for path in sorted(project.rglob("*")):
        if path.is_symlink():
            raise ValueError("public demo project contains a symlink")
        relative = path.relative_to(project).as_posix()
        if path.is_file():
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_dir():
            directories.append(relative)
        else:
            raise ValueError("public demo project contains an unsupported entry")
    return {"files": files, "directories": directories}


def prepare_workspace(workspace: Path) -> dict:
    root = _safe_workspace_path(workspace)
    if root.exists():
        if not root.is_dir() or root.is_symlink():
            raise ValueError("demo workspace must be an empty directory")
        if any(root.iterdir()):
            raise ValueError("demo workspace must be empty or already owned")
    else:
        root.mkdir(parents=True)

    project = root / "project"
    run_dir = root / "run"
    try:
        shutil.copytree(SEED, project, symlinks=False)
        run_dir.mkdir()
        (project / "public" / "starter").mkdir()
        (project / "public" / "uploads").mkdir()
        _atomic_json(root / SENTINEL, _sentinel_payload(root))
        baseline = inventory_project(root)
        _atomic_json(root / BASELINE, baseline)
    except BaseException:
        if root.exists() and not any(root.iterdir()):
            root.rmdir()
        raise
    return {
        "workspace": str(root),
        "project": str(project),
        "run_dir": str(run_dir),
        "baseline_inventory": str(root / BASELINE),
    }


def reset_workspace(workspace: Path) -> None:
    owned = require_owned_workspace(workspace)
    root = owned["workspace"]
    if owned["project"] != root / "project" or owned["run_dir"] != root / "run":
        raise ValueError("public demo child boundary is invalid")
    baseline = root / BASELINE
    if not baseline.is_file() or baseline.is_symlink():
        raise ValueError("public demo baseline inventory is missing or unsafe")
    unexpected = sorted(path.name for path in root.iterdir() if path.name not in _OWNED_TOP_LEVEL)
    if unexpected:
        raise ValueError("unexpected public demo top-level entries: " + ", ".join(unexpected))
    shutil.rmtree(root)


def check_applied(workspace: Path) -> dict:
    owned = require_owned_workspace(workspace)
    project = owned["project"]
    run_dir = owned["run_dir"]
    errors = []
    if (project / "LICENSE").read_bytes() != (SEED / "LICENSE").read_bytes():
        errors.append("LICENSE changed")
    try:
        messages = json.loads(
            (project / "messages" / "en.json").read_text(encoding="utf-8")
        )
        package = json.loads((project / "package.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("could not read applied demo files") from exc
    if messages.get("plan") != "starter_monthly":
        errors.append("retained P1 plan key changed")
    if messages.get("brand") != "Your Product":
        errors.append("neutral product placeholder is missing")
    if messages.get("support") != "support@example.com":
        errors.append("neutral support placeholder is missing")
    if package.get("name") != "your-product":
        errors.append("neutral package name is missing")
    if package.get("author") != "Your Company":
        errors.append("neutral owner placeholder is missing")
    if package.get("repository") != "https://github.com/your-org/your-product":
        errors.append("neutral repository placeholder is missing")
    if (project / "app" / "demo").exists():
        errors.append("approved P2 demo path remains")
    if (project / "public" / "starter").exists():
        errors.append("approved source-named empty directory remains")
    if not (project / "public" / "uploads").is_dir():
        errors.append("ordinary empty directory was removed")
    if (project / "public" / "starter-logo.svg").exists():
        errors.append("approved source-named asset path remains")
    if not (project / "public" / "product-logo.svg").is_file():
        errors.append("renamed product asset is missing")
    for artifact in ("backup", "restore.json", "reverse.diff", "apply-result.json"):
        if not (run_dir / artifact).exists():
            errors.append("missing external recovery artifact: " + artifact)
    if errors:
        raise ValueError("; ".join(errors))
    return {"status": "approved-scope-verified", "checks": 12}


def tamper_previewed_project(workspace: Path) -> Path:
    """Change one fixed synthetic file to demonstrate stale-preview refusal."""
    owned = require_owned_workspace(workspace)
    target = owned["project"] / "messages" / "en.json"
    if not target.is_file() or target.is_symlink():
        raise ValueError("expected synthetic demo message file is missing")
    with target.open("ab") as handle:
        handle.write(b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return target


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage a disposable, synthetic de-starter public demo workspace."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "inventory", "check", "reset"):
        child = subparsers.add_parser(command)
        child.add_argument("--workspace", type=Path, required=True)
    tamper = subparsers.add_parser(
        "tamper",
        help="intentionally stale one file inside a sentinel-owned disposable demo",
    )
    tamper.add_argument("--workspace", type=Path, required=True)
    return parser


def main(argv: Sequence[str] = ()) -> int:
    args = _parser().parse_args(list(argv) if argv else None)
    try:
        if args.command == "prepare":
            payload = prepare_workspace(args.workspace)
        elif args.command == "inventory":
            payload = inventory_project(args.workspace)
        elif args.command == "check":
            payload = check_applied(args.workspace)
        elif args.command == "tamper":
            target = tamper_previewed_project(args.workspace)
            payload = {
                "status": "intentionally-stale",
                "target": target.relative_to(
                    require_owned_workspace(args.workspace)["project"]
                ).as_posix(),
            }
        else:
            reset_workspace(args.workspace)
            payload = {"status": "reset", "workspace": str(args.workspace)}
    except (OSError, ValueError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
