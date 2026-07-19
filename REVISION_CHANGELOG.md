# Revision Changelog

## Frozen checkpoints

- `revision_work/freeze/pre-revision-freeze/`: checksum inventory of the submitted analysis state.
- `revision_work/freeze/reviewer-required-analyses-v1/`: frozen cohort, episode, subject, table, figure-source, and results-manifest outputs with SHA-256 checksums.
- The workspace has no usable Git history; versioned checksum snapshots replace commits.

## Reviewer 1

| Comment | Analysis/change | Manuscript/output | Response |
|---|---|---|---|
| Mathematical methods need expert-reviewable detail | Architecture, losses, split, training, QT covariance, hysteresis, matching, and hierarchy specified | Methods 2.2–2.5; Supplement S1–S3 | Reviewer 1.1 |
| Text difficult to understand | Full plain-language rewrite; three contrasts separated; rhetoric removed | Entire clean manuscript | Reviewer 1.2 |
| Ischemia interpretation and ECG strips | Narrow null framing; ischemic-vs-baseline shown; reproducible two-case ECG/trend figure | Results 3.3/3.5; Discussion; Figure 1 | Reviewer 1.3 |

## Reviewer 2

| Comment | Analysis/change | Manuscript/output | Response |
|---|---|---|---|
| Label purity/heart-rate explanation | Label-aware language; rate-dynamic, hysteresis, protocol, and concordance analyses | Methods 2.4; Results 3.4; Discussion | Reviewer 2.1 |
| Fraction from subjects with ischemic episodes | Raw and retained overlap at subject/record/lead/episode/duration/beat levels | Table 1; Results 3.2; `subject_episode_overlap.csv` | Reviewer 2.2 |
| Per-patient effects and substrate | Overlap interaction; within-subject analysis; exploratory clinical-header strata | Table 4; Results 3.3–3.4 | Reviewer 2.2–2.3 |
| Generalizability | LTST selected-cohort and EDB generic-ST limitations | Discussion and Limitations | Reviewer 2.3 |

## Additional integrity changes

- Replaced the independent-group Welch uncertainty for every equal-subject direct contrast with 20,000-draw unique-subject bootstrap inference that preserves both summaries for overlapping subjects. Under primary `.stb`, the estimate remains 4.87 ms but the 95% CI is −0.34 to 10.23 and p=0.065.
- Disclosed that the primary scientific comparison was prespecified but the equal-subject principal inferential analysis was introduced during revision; retained the submitted −1.78-ms uncertainty-weighted beat model as a sensitivity analysis.
- Split the cohort and rate/overlap tables, moved duration/beat counts to the Supplement, converted equations to native Word math, and placed manuscript tables in a landscape section at 8.5-point minimum type.
- Added the 16-subject heart-rate-related-only clinical-header cross-tabulation and narrowed substrate/overlap interpretations.
- Removed the author-identifying repository from blinded documents and created a separate blinded review archive.
- Replaced a truncated LTST signal only after verifying the official SHA-256; reprocessed 86/86 records.
- Mapped 86 LTST records to 80 unique subjects and repeated EDB records to documented subjects.
- Added subject-clustered beat models, episode models, equal-subject bootstrap/permutation estimates, and nine-subject paired sensitivity.
- Added direct-QT MAE, bias, RMSE, covariance, and independence/covariance-aware PICP.
- Added signed-direction analyses; absolute residual is never described as QT prolongation.
- Rebuilt Figures 1–3 and Figures S1–S4 from scripts; publication TIFF files use lossless LZW compression.
- Created `results_manifest.csv`, `cohort_flow.csv`, subject/episode results, editable table sources, figure sources, and environment files.
