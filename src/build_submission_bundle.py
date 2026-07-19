"""Assemble upload-ready files and a versioned reproducibility archive."""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission_revision_v1.0.0"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    deliverables = [
        *sorted((ROOT / "paper/docx_revision").glob("*.docx")),
        ROOT / "paper/manuscript_revised_numbered.pdf",
        *sorted((ROOT / "paper/figures_revision").glob("*.tiff")),
    ]
    for p in deliverables:
        shutil.copy2(p, OUT / p.name)

    archive_files = [
        *sorted((ROOT / "src").glob("*.py")),
        *sorted((ROOT / "tests").glob("*.py")),
        *sorted((ROOT / "paper").glob("*revised*.md")),
        ROOT / "paper/response_to_reviewers.md",
        *sorted((ROOT / "paper/tables_revision").glob("*.csv")),
        *sorted((ROOT / "revision_work/figure_source").glob("*.csv")),
        *sorted((ROOT / "revision_work/audit").glob("*.csv")),
        *sorted((ROOT / "revision_work/analysis").glob("*.csv")),
        ROOT / "results_manifest.csv", ROOT / "analysis_environment.yml",
        ROOT / "requirements.txt", ROOT / "REVISION_CHANGELOG.md",
        ROOT / "revision_work/literature_search.md",
        ROOT / "revision_work/submission_QA.md",
        ROOT / "revision_work/completion_audit.md",
        ROOT / "revision_work/data/ltstdb_verified/RECORDS",
        ROOT / "revision_work/data/ltstdb_verified/SHA256SUMS.txt",
    ]
    archive_files = sorted({p for p in archive_files if p.exists() and p.is_file()})
    archive = OUT / "reproducibility_archive_v1.0.0.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in archive_files:
            z.write(p, p.relative_to(ROOT))
        z.writestr("ARCHIVE_VERSION.txt", "qt-revision v1.0.0\ncreated 2026-07-19\n")

    all_outputs = sorted(p for p in OUT.iterdir()
                         if p.is_file() and p.name != "SHA256SUMS.csv")
    pd.DataFrame([{"file": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
                  for p in all_outputs]).to_csv(OUT / "SHA256SUMS.csv", index=False)
    (OUT / "README.md").write_text(
        "# Submission revision v1.0.0\n\n"
        "Upload-ready DOCX documents, numbered manuscript PDF, separate lossless TIFF figures, "
        "and a versioned reproducibility archive. Raw public ECG data and multi-gigabyte derived "
        "Parquet files are excluded; official data records/checksums and download/build scripts are included.\n",
        encoding="utf-8")
    print(f"deliverables={len(deliverables)} archive_files={len(archive_files)} archive={archive.stat().st_size} bytes")


if __name__ == "__main__":
    main()
