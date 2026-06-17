"""Release config parsing and branch naming logic."""

UPSTREAM_REPOS = [
    ("openvinotoolkit", "model_server"),
    ("openvinotoolkit", "openvino"),
    ("openvinotoolkit", "openvino.genai"),
    ("openvinotoolkit", "openvino_tokenizers"),
]

MIDSTREAM_REPOS = [
    ("opendatahub-io", "openvino_model_server"),
    ("opendatahub-io", "openvino"),
    ("opendatahub-io", "openvino.genai"),
    ("opendatahub-io", "openvino_tokenizers"),
]


def parse_version(version: str) -> tuple[str, str]:
    """Parse '2026.2' into (year, minor)."""
    parts = version.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid version: {version} (expected YEAR.MINOR, e.g. 2026.2)")
    return parts[0], parts[1]


def get_branch_name(repo_name: str, year: str, minor: str, org: str = "midstream") -> str:
    """Get the correct branch name for a repo.

    openvino_model_server uses YEAR.MINOR-release (e.g., 2026.2-release)
    All other repos use releases/YEAR/MINOR (e.g., releases/2026/2)
    """
    if repo_name == "openvino_model_server" and org == "midstream":
        return f"{year}.{minor}-release"
    return f"releases/{year}/{minor}"


def get_upstream_branch(year: str, minor: str) -> str:
    """All upstream repos use releases/YEAR/MINOR."""
    return f"releases/{year}/{minor}"


def get_stable_branch() -> str:
    return "stable"


def get_rhoai_branch(rhoai_version: str) -> str:
    return f"rhoai-{rhoai_version}"


def get_downstream_branch(rhoai_version: str) -> str:
    return f"rhoai-{rhoai_version}"
