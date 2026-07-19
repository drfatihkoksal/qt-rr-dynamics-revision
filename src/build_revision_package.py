"""Build immutable, machine-readable tables and manifests for the revision.

This script only transforms pipeline outputs; it never recomputes or edits an
inferential result.  Run after all analysis scripts and before manuscript export.
"""
from __future__ import annotations

import hashlib
import platform
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ANA = ROOT / "revision_work/analysis"
AUD = ROOT / "revision_work/audit"
OUT = ROOT / "revision_work/freeze/reviewer-required-analyses-v1"
TABLES = ROOT / "paper/tables_revision"


def subject_results() -> pd.DataFrame:
    e = pd.read_csv(ANA / "episode_level_results.csv")
    event = e[e.episode_type.isin(["ischemic", "rate_related"])].copy()
    base = e[e.episode_type.eq("matched_baseline")].copy()
    cols = ["record", "subject_id", "lead", "episode_id"]
    measures = ["mean_abs_resid_ms", "median_abs_resid_ms",
                "mean_signed_resid_ms", "median_signed_resid_ms"]
    paired = event.merge(base[cols + measures], on=cols, suffixes=("_episode", "_baseline"))
    for m in measures:
        paired[f"delta_{m}"] = paired[f"{m}_episode"] - paired[f"{m}_baseline"]
    agg = {"episode_id": "size", "retained_beats": "sum"}
    agg.update({f"delta_{m}": "mean" for m in measures})
    out = (paired.groupby(["subject_id", "episode_type"], as_index=False)
           .agg(agg).rename(columns={"episode_id": "episodes",
                                    "retained_beats": "retained_episode_beats"}))
    return out


def results_manifest() -> pd.DataFrame:
    frames = []
    specs = [
        (ANA / "hierarchical_effects.csv", "revision_statistics.py", "LTST"),
        (ANA / "subgroup_effects.csv", "revision_subgroups.py", "LTST subgroup"),
        (ANA / "sensitivity_effects.csv", "revision_residual_reanalysis.py", "LTST sensitivity"),
        (ANA / "edb_hierarchical_effects.csv", "revision_edb_statistics.py", "EDB"),
    ]
    for path, script, family in specs:
        d = pd.read_csv(path)
        ren = {"analysis": "analysis_id", "specification": "analysis_id",
               "effect_ms": "effect_estimate", "ci_low_ms": "ci_lower",
               "ci_high_ms": "ci_upper", "subjects": "independent_subjects"}
        d = d.rename(columns=ren)
        if "analysis_id" not in d:
            d["analysis_id"] = [f"{family}_{i+1:03d}" for i in range(len(d))]
        d["analysis_family"] = family
        d["source_file"] = str(path.relative_to(ROOT))
        d["source_script"] = f"src/{script}"
        frames.append(d)

    # Accuracy/calibration outputs are long-form manifest rows so every
    # reported metric is machine-addressable alongside inferential effects.
    acc_path = ANA / "direct_qt_accuracy_covariance.csv"
    acc = pd.read_csv(acc_path)
    metrics = [c for c in acc.columns if c not in {"source", "n"}]
    a = acc.melt(id_vars=["source", "n"], value_vars=metrics,
                 var_name="outcome", value_name="effect_estimate")
    a["analysis_id"] = [f"QTACC_{i+1:03d}" for i in range(len(a))]
    a["analysis_family"] = "direct QT accuracy/covariance"
    a["analysis_level"] = "annotated_beat"
    a["observations"] = a["n"]
    a["model"] = a["source"]
    a["source_file"] = str(acc_path.relative_to(ROOT))
    a["source_script"] = "src/revision_qt_uncertainty.py"
    frames.append(a)

    picp_path = ANA / "direct_qt_picp.csv"
    picp = pd.read_csv(picp_path)
    pcols = [c for c in picp.columns if c.startswith("picp_")]
    p = picp.melt(id_vars=["source", "method", "n"], value_vars=pcols,
                  var_name="outcome", value_name="effect_estimate")
    p["analysis_id"] = [f"QTPICP_{i+1:03d}" for i in range(len(p))]
    p["analysis_family"] = "direct QT prediction interval coverage"
    p["analysis_level"] = "annotated_beat"
    p["observations"] = p["n"]
    p["model"] = p["source"] + "; " + p["method"]
    p["source_file"] = str(picp_path.relative_to(ROOT))
    p["source_script"] = "src/revision_qt_uncertainty.py"
    frames.append(p)

    lm_path = ROOT / "results/coverage_picp.csv"
    lm = pd.read_csv(lm_path)
    lm_metrics = ["mae_ms", "mean_sigma_ms", "rmse_ms"] + [c for c in lm.columns if c.startswith("PICP_")]
    l = lm.melt(id_vars=["source", "landmark", "n"], value_vars=lm_metrics,
                var_name="outcome", value_name="effect_estimate")
    l["analysis_id"] = [f"LMCAL_{i+1:03d}" for i in range(len(l))]
    l["analysis_family"] = "landmark accuracy/calibration"
    l["analysis_level"] = "annotated_beat"
    l["observations"] = l["n"]
    l["model"] = l["source"] + "; " + l["landmark"]
    l["source_file"] = str(lm_path.relative_to(ROOT))
    l["source_script"] = "src/coverage.py"
    frames.append(l)

    direction_path = ANA / "signed_residual_direction.csv"
    direction = pd.read_csv(direction_path)
    dir_metrics = [c for c in direction.columns if c not in {"episode_type", "direction"}]
    d = direction.melt(id_vars=["episode_type", "direction"], value_vars=dir_metrics,
                       var_name="outcome", value_name="effect_estimate")
    d["analysis_id"] = [f"SIGNDIR_{i+1:03d}" for i in range(len(d))]
    d["analysis_family"] = "episode signed direction"
    d["analysis_level"] = "episode"
    d["model"] = d["episode_type"]
    d["source_file"] = str(direction_path.relative_to(ROOT))
    d["source_script"] = "src/revision_statistics.py"
    frames.append(d)
    all_cols = sorted(set().union(*(x.columns for x in frames)))
    return pd.concat([x.reindex(columns=all_cols) for x in frames], ignore_index=True)


def copy_table(name: str, source: Path) -> None:
    shutil.copy2(source, TABLES / name)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    subjects = subject_results()
    subjects.to_csv(ANA / "subject_level_results.csv", index=False)
    manifest = results_manifest()
    manifest.to_csv(ROOT / "results_manifest.csv", index=False)

    figure_sources = ROOT / "revision_work/figure_source"
    figure_sources.mkdir(parents=True, exist_ok=True)
    source_map = {
        "figure2_episode_level_results.csv": ANA / "episode_level_results.csv",
        "figure2_episode_matched_effects.csv": ANA / "episode_matched_effects.csv",
        "figure2_hierarchical_effects.csv": ANA / "hierarchical_effects.csv",
        "figure2_subgroup_effects.csv": ANA / "subgroup_effects.csv",
        "figure3_landmark_coverage.csv": ROOT / "results/coverage_picp.csv",
        "figure3_direct_qt_coverage.csv": ANA / "direct_qt_picp.csv",
        "figureS1_sensitivity_effects.csv": ANA / "sensitivity_effects.csv",
        "figureS2_tau_selection.csv": ANA / "tau_selection_primary_all_record_leads.csv",
        "figureS3_episode_signed_residuals.csv": ANA / "episode_level_results.csv",
        "figureS4_cross_lead_concordance.csv": AUD / "cross_lead_concordance_stb.csv",
    }
    for name, source in source_map.items():
        shutil.copy2(source, figure_sources / name)

    copy_table("table1_subject_overlap.csv", AUD / "subject_overlap_summary.csv")
    copy_table("table2_landmark_calibration.csv", ROOT / "results/coverage_picp.csv")
    copy_table("table2_direct_qt_accuracy.csv", ANA / "direct_qt_accuracy_covariance.csv")
    copy_table("table2_direct_qt_coverage.csv", ANA / "direct_qt_picp.csv")
    copy_table("table3_primary_estimands.csv", ANA / "hierarchical_effects.csv")
    copy_table("table4_subgroups.csv", ANA / "subgroup_effects.csv")
    copy_table("tableS_hysteresis_protocol.csv", ANA / "sensitivity_effects.csv")
    copy_table("tableS_cross_lead.csv", AUD / "cross_lead_concordance_stb.csv")
    copy_table("tableS_edb.csv", ANA / "edb_hierarchical_effects.csv")

    required = [
        ROOT / "results_manifest.csv", AUD / "cohort_flow.csv",
        AUD / "subject_episode_overlap.csv", ANA / "episode_level_results.csv",
        AUD / "edb_qtdb_overlap_exclusions.csv",
        ANA / "subject_level_results.csv", *sorted(TABLES.glob("*.csv")),
        *sorted(figure_sources.glob("*.csv")),
    ]
    for p in required:
        target = OUT / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    rows = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
             "sha256": sha256(p)} for p in required]
    pd.DataFrame(rows).to_csv(OUT / "SHA256SUMS.csv", index=False)
    (OUT / "README.md").write_text(
        "# Reviewer-required analyses v1\n\nGenerated by `src/build_revision_package.py`. "
        "Files are copied from pipeline outputs and must not be edited manually.\n",
        encoding="utf-8")
    print(f"manifest rows: {len(manifest)}; subject rows: {len(subjects)}")
    print(f"frozen files: {len(required)}; Python {platform.python_version()}; pandas {pd.__version__}")


if __name__ == "__main__":
    main()
