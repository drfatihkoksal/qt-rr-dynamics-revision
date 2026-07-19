# QT–RR Dynamics Revision Reproducibility Repository

Versioned code, statistical outputs, source data, and manuscript-supporting material for:

> Köksal F. *Uncertainty-Aware Deep-Learning Delineation of QT–RR Dynamics During Ischemic and Heart-Rate–Related ST Episodes in Long-Term Ambulatory ECG.* Major revision for the Journal of Electrocardiology.

## Scientific scope

The primary endpoint compares the equal-subject mean absolute QT–RR residual between database-labeled ischemic and database-labeled heart-rate-related ST episodes. The revision preserves the null interpretation narrowly: no larger ischemic departure was demonstrated, and the result is neither an equivalence finding nor evidence that ischemia has no repolarization effect.

## Repository contents

- `src/`: model, preprocessing, cohort audit, reanalysis, statistics, figure, and packaging scripts.
- `tests/`: executable critical pipeline tests.
- `revision_work/analysis/`: machine-readable statistical outputs (CSV; large beat-level Parquet files excluded).
- `revision_work/audit/`: subject maps, cohort flow, overlap, exclusions, clinical-header summaries, and source-overlap mapping.
- `revision_work/figure_source/`: source data for every figure.
- `paper/tables_revision/`: editable table source data.
- `results_manifest.csv`: long-form index of inferential effects and calibration metrics.
- `analysis_environment.yml` and `requirements.txt`: exact analysis environment.
- `REVISION_CHANGELOG.md`: reviewer-comment-to-analysis/document mapping.

## Reproduction

Create the environment:

```bash
conda env create -f analysis_environment.yml
conda activate qt-revision-2026-07-19
```

Run the critical test and syntax checks:

```bash
pytest -q tests/test_revision_pipeline.py
python -m py_compile src/*.py
```

Regenerate tables, manifests, and figures after obtaining the public datasets:

```bash
PYTHONPATH=. python src/build_revision_package.py
PYTHONPATH=. python src/revision_figures.py
PYTHONPATH=. python src/revision_ecg_figure.py
PYTHONPATH=. python src/revision_workflow_figure.py
```

The multi-million-beat reanalysis outputs are intentionally not stored in Git. Scripts consume locally prepared WFDB data and regenerate those outputs. Statistical CSVs, figure sources, and frozen checksums are included so manuscript claims remain auditable without redistributing source signals.

## Data

All ECG datasets are public through PhysioNet: LUDB v1.0.1, QTDB v1.0.0, Long-Term ST Database v1.0.0, and European ST-T Database v1.0.0. Dataset files retain their original terms and are not redistributed here. `revision_work/data/ltstdb_verified/RECORDS` and `SHA256SUMS.txt` identify the exact LTST inputs.

## Versioning

The manuscript revision uses release `v1.0.0`. The release asset contains the exact reproducibility archive supplied with the revision. SHA-256 manifests provide integrity checks where Git history was unavailable during the original local audit.

## License

Analysis code is released under the MIT License. Manuscript text and third-party datasets are not relicensed by this repository.

## Contact

Fatih Köksal, MD — ORCID: 0000-0002-4197-4683
