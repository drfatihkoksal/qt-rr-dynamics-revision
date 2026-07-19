# Requirement-by-requirement completion audit

Audited against `revision.md` on 2026-07-19. “Complete” means direct current-state evidence exists; “external pending” is not counted as complete.

| Requirement | Status | Authoritative evidence |
|---|---|---|
| Pre-revision freeze | Complete | `revision_work/freeze/pre-revision-freeze/` checksums and inventory |
| LTST subject/record/lead mapping | Complete | `revision_work/audit/ltstdb_subject_map.csv`, `record_lead_audit.csv`; 86 records/80 subjects/190 leads |
| Cohort flow and exclusions | Complete | `cohort_flow.csv`, `exclusion_audit.csv`, Figure S5C; manuscript Methods/Results |
| QTDB 105/93/11/1 reconciliation | Complete | manuscript Section 2.1 and cohort audit |
| EDB 90/57 and repeated subjects | Complete | Supplement S7, `edb_qtdb_overlap_exclusions.csv`, EDB scripts/results |
| Raw and retained subject overlap | Complete | `subject_episode_overlap.csv`, `subject_overlap_summary.csv`, `hr_overlap_fractions.csv`, Table 1 |
| Per-subject subgroups and interaction | Complete | `subgroup_effects.csv`, Figure 2C, Table 4A |
| Exploratory clinical substrate | Complete with stated metadata limitation | `subject_clinical_metadata.csv`, `clinical_overlap_crosstab.csv`, `subgroup_effects.csv`, Results 3.4 |
| Beat/episode/equal-subject/within-subject hierarchy | Complete | `hierarchical_effects.csv`, `subject_level_results.csv`, Table 3; partially paired direct contrasts resample 76 unique subjects |
| Unweighted and uncertainty-weighted results | Complete | hierarchical rows LTST_029–LTST_040 |
| Signed direction/dispersion | Complete | `signed_residual_direction.csv`, Figure S3, Results 3.4 |
| Dynamic-rate adjustment | Complete | `subgroup_effects.csv`, Table 4B; partially paired direct CI; attenuation reported in Abstract/Results/Discussion |
| Fixed and expanded hysteresis grid | Complete | `sensitivity_effects.csv`, tau source data, Figures S1–S2 |
| `.sta/.stb/.stc` sensitivity | Complete | `sensitivity_effects.csv`; protocol dependence reported without selection |
| Label purity and cross-lead concordance | Complete | `cross_lead_concordance_*.csv`, Figure S4, Methods/Discussion |
| ECG strips and aligned trends | Complete | Figure 1 TIFF; selection script/IDs; four Figure 1 source tables |
| Direct QT accuracy/covariance/PICP | Complete | `direct_qt_accuracy_covariance.csv`, `direct_qt_picp.csv`, Figure 3, Table 2 |
| Exact architecture/training/loss details | Complete | Methods 2.2; Supplement S1; Figure S5A; source model/train scripts |
| Matching algorithm disclosure | Complete | Methods 2.4 and Supplement S2 now match `assign_matched_baseline`; nonmatching of time-of-day and adjacent ectopy disclosed |
| Workflow/cohort diagram | Complete | Figure S5 and source data/script |
| Machine-readable manifest | Complete | `results_manifest.csv`, 304 long-form rows including effects and calibration metrics |
| Figure/table source data | Complete | `revision_work/figure_source/`, `paper/tables_revision/` |
| Environment and tests | Complete | `analysis_environment.yml`, `requirements.txt`, passing `tests/test_revision_pipeline.py`, Python compile |
| Clean/marked manuscript and other DOCX files | Complete | `paper/docx_revision/`; native Word equations; portrait narrative and landscape 8.5-point editable tables; marked text highlighted |
| Continuous line numbering | Complete | line-numbering XML in clean/marked DOCX; `manuscript_revised_numbered.pdf` |
| Exact response page/line references | Complete | `response_to_reviewers.md`; references correspond to 14-page numbered PDF |
| Placeholder/prohibited-claim QA | Complete | `revision_work/submission_QA.md`; quoted reviewer language excepted |
| Blinded peer-review archive | Complete | `submission_revision_v1.1.0/blinded_review_archive_v1.1.0.zip`; identity scan in QA |
| Versioned upload bundle/archive | Complete | `submission_revision_v1.1.0/`, `SHA256SUMS.csv`, validated ZIP |
| Persistent public repository URL/version | Complete | Public repository and release v1.1.0: https://github.com/drfatihkoksal/qt-rr-dynamics-revision/releases/tag/v1.1.0 |

## Completion conclusion

All analyses, documents, figures, tables, source data, line references, blinded archive, versioned public repository, local archive, and QA gates are complete. The author-identified persistent release is confined to the title page and cover letter; blinded materials contain the versioned review archive without identity-bearing repository metadata. Regenerated artifacts and checksums are tied to v1.1.0.
