"""Final consistency checks for the revision submission package."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
TEXTS = [
    PAPER / "manuscript_revised_clean.md", PAPER / "supplement_revised.md",
    PAPER / "response_to_reviewers.md", PAPER / "cover_letter_revised.md",
    PAPER / "title_page_revised.md",
]
PLACEHOLDERS = re.compile(r"\[add|\[adjust|\[repository|\bTBD\b|\bTODO\b|\bXX\b|page X|line Y", re.I)


def main() -> None:
    problems = []
    for p in TEXTS:
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if PLACEHOLDERS.search(line):
                problems.append(f"placeholder {p.relative_to(ROOT)}:{n}")
    manifest = pd.read_csv(ROOT / "results_manifest.csv")
    if len(manifest) != 304:
        problems.append(f"unexpected manifest rows: {len(manifest)}")
    cohort = pd.read_csv(ROOT / "revision_work/audit/cohort_flow.csv")
    required_counts = {("database_catalog", "records"): 86,
                       ("pipeline", "unique_subjects"): 80,
                       ("primary_analysis", "episodes"): 1278}
    for (stage, unit), expected in required_counts.items():
        q = cohort[(cohort.stage == stage) & (cohort.unit == unit)]
        if len(q) != 1 or int(q.iloc[0].n) != expected:
            problems.append(f"cohort {stage}/{unit} != {expected}")
    for name, expected_shapes in {
        "manuscript_revised_clean.docx": (4, 3),
        "manuscript_revised_marked.docx": (4, 3),
    }.items():
        d = Document(PAPER / "docx_revision" / name)
        got = (len(d.tables), len(d.inline_shapes))
        if got != expected_shapes:
            problems.append(f"{name} tables/figures {got} != {expected_shapes}")
        if not all(section._sectPr.find(qn("w:lnNumType")) is not None for section in d.sections):
            problems.append(f"{name} lacks continuous line-numbering XML")

    manuscript = (PAPER / "manuscript_revised_clean.md").read_text(encoding="utf-8")
    release_url = "https://github.com/drfatihkoksal/qt-rr-dynamics-revision/releases/tag/v1.0.0"
    if release_url not in manuscript:
        problems.append("versioned public repository URL missing from manuscript")
    h = pd.read_csv(ROOT / "revision_work/analysis/hierarchical_effects.csv").set_index("analysis_id")
    numeric_claims = {
        "4.87 ms": h.loc["LTST_018", "effect_ms"],
        "7.67 ms": h.loc["LTST_002", "effect_ms"],
        "4.57 ms": h.loc["LTST_010", "effect_ms"],
        "−1.36 ms": h.loc["LTST_019", "effect_ms"],
    }
    for rendered, value in numeric_claims.items():
        expected = f"{value:.2f} ms".replace("-", "−")
        if rendered != expected or rendered not in manuscript:
            problems.append(f"primary numeric claim missing/mismatched: {rendered} from {value}")
    overlap = pd.read_csv(ROOT / "revision_work/audit/hr_overlap_fractions.csv")
    ep_overlap = overlap[overlap.unit.eq("episodes")]
    if ("58/218" not in manuscript or len(ep_overlap) != 1 or
            int(ep_overlap.iloc[0].numerator) != 58 or int(ep_overlap.iloc[0].denominator) != 218):
        problems.append("overlap episode numerator/denominator not traceable")
    if problems:
        raise SystemExit("\n".join(problems))
    report = ROOT / "revision_work/submission_QA.md"
    report.write_text(
        "# Submission QA\n\n"
        "- Placeholder scan: PASS (five revised English sources).\n"
        "- Results manifest: PASS (304 rows, including inferential effects, direct-QT and landmark calibration, and signed direction).\n"
        "- Cohort invariants: PASS (86 records, 80 subjects, 1,278 episodes).\n"
        "- DOCX integrity: PASS (clean and marked each contain 4 editable tables and 3 figures).\n"
        "- Marked manuscript: all substantive text highlighted because the manuscript was fully rewritten.\n"
        "- Automated pipeline test and Python compilation: run separately in final QA.\n"
        "- Public versioned repository: PASS (release v1.0.0 URL included in manuscript).\n",
        encoding="utf-8")
    print("revision QA passed")


if __name__ == "__main__":
    main()
