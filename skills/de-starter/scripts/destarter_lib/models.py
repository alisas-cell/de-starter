from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RiskLevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


@dataclass(frozen=True)
class FileRecord:
    relpath: str
    size: int
    sha256: str
    is_text: bool


@dataclass(frozen=True)
class Candidate:
    kind: str
    value: str
    score: int
    sources: List[str]


@dataclass(frozen=True)
class ProjectFacts:
    kind: str
    package_manager: Optional[str]
    validation_commands: List[str]
    git_present: bool
    git_dirty: Optional[bool] = None


@dataclass(frozen=True)
class Finding:
    finding_id: str
    relpath: str
    line: int
    column: int
    matched: str
    category: str
    risk: RiskLevel
    evidence: str
    sha256: str


@dataclass
class DiscoveryResult:
    project: ProjectFacts
    candidates: List[Candidate]
    files: List[FileRecord]


@dataclass
class AuditResult:
    project: ProjectFacts
    source_terms: List[str]
    findings: List[Finding]
    files: List[FileRecord]


@dataclass(frozen=True)
class DecisionAction:
    finding_id: str
    action: str
    replacement: Optional[str] = None
    migration_plan: Optional[str] = None
    rollback_plan: Optional[str] = None


@dataclass
class DecisionSet:
    brand_mode: str
    brand_profile: Dict[str, str]
    actions: List[DecisionAction]
    delete_paths: List[str] = field(default_factory=list)
    rename_paths: Dict[str, str] = field(default_factory=dict)


@dataclass
class PreviewManifest:
    run_id: str
    project_root: str
    preview_root: str
    source_hashes: Dict[str, str]
    preview_hashes: Dict[str, str]
    delete_tree_hashes: Dict[str, str]
    rename_tree_hashes: Dict[str, Dict[str, str]]
    changed_paths: List[str]
    deleted_paths: List[str]
    renamed_paths: Dict[str, str]
    approval_token: str


@dataclass
class ApplyResult:
    run_id: str
    changed_paths: List[str]
    deleted_paths: List[str]
    renamed_paths: Dict[str, str]
    backup_root: str
    restore_manifest: str


def to_dict(value: object) -> Dict[str, object]:
    return asdict(value)
