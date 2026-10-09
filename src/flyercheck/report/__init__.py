"""findings.json + self-contained report.html. Owned by track T5."""
from flyercheck.domain.models import RunResult


def write_report(run: RunResult, out_dir: str) -> str:
    """Write findings.json and report.html into out_dir; return the html path."""
    raise NotImplementedError
