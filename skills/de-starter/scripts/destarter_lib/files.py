from hashlib import sha256
from pathlib import Path
from typing import Iterator, Optional

from .models import FileRecord

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".next", ".nuxt", ".cache", ".pytest_cache",
    ".tox", ".venv", "venv", "build", "dist", "coverage", "node_modules",
    "vendor", "__pycache__",
}
SAFE_ENV_EXAMPLES = {".env.example", ".env.sample", ".env.template"}
MAX_TEXT_BYTES = 2 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> Optional[str]:
    if is_secret_name(path.name) or path.stat().st_size > MAX_TEXT_BYTES:
        return None
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def is_secret_name(name: str) -> bool:
    return name == ".env" or (
        name.startswith(".env.") and name not in SAFE_ENV_EXAMPLES
    )


def iter_project_files(root: Path) -> Iterator[FileRecord]:
    records = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if is_secret_name(path.name):
            continue
        records.append(
            FileRecord(
                relpath=rel.as_posix(),
                size=path.stat().st_size,
                sha256=sha256_file(path),
                is_text=read_text(path) is not None,
            )
        )
    yield from sorted(records, key=lambda item: item.relpath)
