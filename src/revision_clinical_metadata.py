"""Extract auditable LTST DB subject-level cardiac-substrate metadata."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def explicit_status(text: str, positive: list[str], negative: list[str]) -> str:
    low = text.lower()
    if any(re.search(pattern, low) for pattern in positive):
        return "documented_present"
    if any(re.search(pattern, low) for pattern in negative):
        return "explicitly_documented_absent"
    return "unknown_or_insufficient"


def coronary_status(text: str) -> str:
    lines = [re.sub(r"^#\s*", "", x).strip().lower() for x in text.splitlines()]
    negative_terms = ("no coronary artery disease", "no history of coronary artery disease",
                      "no evidence of coronary artery disease",
                      "no definite diagnosis of coronary artery disease",
                      "coronary arteriography: no significant disease")
    positive = False; negative = False
    for line in lines:
        if any(term in line for term in negative_terms):
            negative = True; continue
        if "family history" in line:
            continue
        if "coronary artery disease" in line or "known cad" in line or re.search(r"patient with cad\b", line):
            positive = True
    return ("documented_present" if positive else
            "explicitly_documented_absent" if negative else
            "unknown_or_insufficient")


def prior_mi_status(text: str) -> str:
    lines = [re.sub(r"^#\s*", "", x).strip().lower() for x in text.splitlines()]
    negative = False
    for line in lines:
        if line.startswith("previous myocardial infarction:"):
            value = line.split(":", 1)[1].strip()
            if value.startswith("yes") or (value and not value.startswith("no")):
                return "documented_present"
            if value == "no":
                negative = True
        elif ("old myocardial infarction" in line or
              re.search(r"myocardial infarction in \d{4}", line) or
              re.search(r"previous myocardial infarction(?!:)", line)):
            return "documented_present"
    return ("explicitly_documented_absent" if negative else
            "unknown_or_insufficient")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path,
                    default=Path("revision_work/data/ltstdb_verified"))
    ap.add_argument("--out", type=Path,
                    default=Path("revision_work/audit/subject_clinical_metadata.csv"))
    args = ap.parse_args()
    records = [x.strip() for x in (args.data_dir / "RECORDS").read_text().splitlines()
               if x.strip()]
    rows = []
    for record in records:
        text = (args.data_dir / f"{record}.hea").read_text(errors="replace")
        age = re.search(r"#Age:\s*(.*?)(?=\s+Sex:|[\n\r]|$)", text, re.I)
        sex = re.search(r"Sex:\s*([^\n\r]+)", text, re.I)
        coronary = coronary_status(text)
        prior_mi = prior_mi_status(text)
        revascularization = explicit_status(
            text, [r"balloon angioplasty:\s*(?:yes|\d{4})", r"coronary artery bypass grafting:\s*yes",
                   r"\bpci\b", r"\bcabg\b"],
            [r"balloon angioplasty:\s*no[\s\S]*coronary artery bypass grafting:\s*no"])
        angina = explicit_status(
            text, [r"(?<!no )\b(?:prinzmetal'?s |resting |effort |unstable |mixed )?angina\b"],
            [r"angina:\s*no", r"no (?:history of )?angina"])
        rows.append({"record": record, "subject_id": record[:-1],
                     "age_text": age.group(1).strip() if age else "",
                     "sex_text": sex.group(1).strip() if sex else "",
                     "coronary_disease_status": coronary,
                     "prior_mi_status": prior_mi,
                     "revascularization_status": revascularization,
                     "angina_status": angina,
                     "header_text": text.replace("\r", "")})
    rec = pd.DataFrame(rows)
    # Conservative subject aggregation: any documented present wins; absence
    # requires every informative record to say absent; otherwise unknown.
    def combine(series: pd.Series) -> str:
        vals = set(series)
        if "documented_present" in vals:
            return "documented_present"
        if vals == {"explicitly_documented_absent"}:
            return "explicitly_documented_absent"
        return "unknown_or_insufficient"
    status_cols = [x for x in rec.columns if x.endswith("_status")]
    subject = rec.groupby("subject_id", as_index=False).agg(
        records=("record", lambda x: ";".join(x)),
        age_text=("age_text", lambda x: ";".join(sorted(set(v for v in x if v)))),
        sex_text=("sex_text", lambda x: ";".join(sorted(set(v for v in x if v)))),
        **{col: (col, combine) for col in status_cols},
        source_headers=("record", lambda x: ";".join(f"{v}.hea" for v in x)))
    subject.to_csv(args.out, index=False)
    rec.drop(columns="header_text").to_csv(
        args.out.with_name("record_clinical_metadata.csv"), index=False)
    print(subject[status_cols].apply(pd.Series.value_counts).fillna(0).astype(int))


if __name__ == "__main__":
    main()
