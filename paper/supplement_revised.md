# Supplementary Material

## Uncertainty-Aware Deep-Learning Delineation of QT–RR Dynamics During Ischemic and Heart-Rate–Related ST Episodes in Long-Term Ambulatory ECG

## S1. Model specification

The delineator accepts a 1×500 beat-centered vector sampled at 250 Hz. Four encoder blocks contain two 1D convolutions (kernel 7, stride 1, same padding), batch normalization, and ReLU, followed by max pooling; channel counts are 32, 64, 128, and 256. The bottleneck has 512 channels. Four decoder stages use kernel-2, stride-2 transposed convolution, concatenated encoder skip connections, and the same double-convolution block in reverse channel order. A kernel-1 head produces four samplewise logits. Adaptive average pooling of the bottleneck, a 512-to-256 ReLU layer, and a 256-to-12 linear layer yield location, log variance, and presence logit for four landmarks. The model has 5,982,928 trainable parameters; no dropout or dilation is used.

For landmark \(j\), presence \(m_j\), target \(y_j\), mean \(\mu_j\), and predicted log variance \(s_j\), the presence-masked Gaussian loss is

\[
L_{lm}=\frac{\sum_j m_j\{s_j/2+(y_j-\mu_j)^2/[2\exp(s_j)]\}}{\sum_jm_j},
\]

where \(s_j\) is clipped to [−14,6]. Total loss is \(L=L_{seg}+5L_{lm}+L_{presence}\). Segmentation uses unweighted four-class cross entropy and presence uses binary cross entropy. Landmark coordinates are normalized to the 500-sample window. A landmark is analyzed only if sigmoid presence exceeds 0.5.

Adam used learning rate 0.001, batch size 256, maximum 40 epochs, seed 0, and gradient-norm clipping at 5. ReduceLROnPlateau used factor 0.5 and patience 4; early stopping used patience 10 and retained minimum validation loss. LUDB pretraining and QTDB fine-tuning used the same procedure. Record-level random splitting used a 15% validation fraction; the 11 dual-annotated QTDB records were excluded before fine-tuning. No augmentation, architecture search, or multi-seed model-development analysis was performed.

## S2. Signal processing and episode analysis

WFDB normal-beat annotations anchored 2-s windows. Each was z-normalized independently. Windows crossing a record edge, nearly constant windows, absent QRS/T predictions, nonfinite measurements, and implausible QT values were excluded with explicit reason codes. The audit counts refer to beat-lead observations because each lead has its own episode stream.

For record-lead \(r\), non-episode beats fitted \(QT=a_r+b_rRR_\tau\), where exponentially smoothed RR followed the observed interbeat time increments: \(RR_{\tau,t}=\alpha_t RR_t+(1-\alpha_t)RR_{\tau,t-1}\), with \(\alpha_t=1-\exp(-\Delta t/\tau)\). Candidate \(\tau\) was chosen by cross-validation on non-episode data. Residuals were back-transformed to milliseconds before analysis. For each episode, candidates began at free, non-episode normal beats and were searched outward from episode onset. The first available window spanning the episode duration was retained. A selected window could not overlap an annotated episode or a previously selected baseline window; pre- and post-episode candidates used the same rule, with deterministic candidate ordering. Primary selection did not explicitly match time of day, smoothed RR, or rate slope. The reviewer sensitivity adjusted the resulting episode–baseline deltas for smoothed RR and RR/heart-rate slope. Episode summaries included mean/median absolute and signed residual, duration, mean/median RR and smoothed RR, RR and heart-rate slopes, model QT uncertainty, and matched-baseline counterparts.

Only beats labeled `N` in the WFDB beat stream were retained. Record-edge windows, nearly constant signals, database-marked quality intervals, absent QRS-onset/T-offset predictions, and implausible measured or predicted QT were excluded. The pipeline did not add an adjacency exclusion around ectopic beats or a separate conduction-abnormality classifier; this is a stated limitation because an `N` beat can retain rate-history effects from a neighboring ectopic beat.

## S3. Statistical specification

Beat-level sufficient-statistic regression used subject-clustered CR1 covariance and a t reference with subjects minus one degree of freedom. Models were both unweighted and inverse-variance weighted. Episode models used one matched delta per episode and subject-clustered covariance. For each label, the principal equal-subject estimate averaged episodes within subject and then gave equal weight to label-specific subject summaries. Nine of 76 unique subjects contributed both label summaries. Therefore, direct between-label confidence intervals and p values used 20,000 unique-subject bootstrap draws; selecting an overlapping subject retained both summaries. The point estimate was the mean ischemic-subject summary minus the mean heart-rate-related-subject summary, the interval was the 2.5th–97.5th percentiles, and the two-sided p value was twice the smaller bootstrap tail probability around zero. The same partially paired resampling structure was used for direct contrasts under alternative annotation protocols, hysteresis specifications, and rate-dynamic adjustment. Within-label episode-versus-baseline equal-subject results used 10,000 deterministic subject bootstrap/permutation draws. Benjamini–Hochberg adjustment was applied only to the three principal equal-subject mean-absolute contrasts. All other p values are sensitivity/exploratory and unadjusted.

## S4. Cohort and overlap details

LTST DB contained 86 verified records, 80 unique subjects, and 190 record-leads. Eighty-one records/76 subjects contributed 1,278 retained episodes. Primary retained groups were: ischemic only, 51 subjects/57 records/130 record-leads/998 ischemic episodes; heart-rate-related only, 16/16/32/160 heart-rate-related episodes; both, 9/9/20/62 ischemic plus 58 heart-rate-related episodes; neither retained label, 4/4/8.

Pre-exclusion raw `.stb` labels comprised 1,118 ischemic and 228 heart-rate-related episodes. Ten of 26 raw heart-rate-related contributors also had ischemic annotations. Post-exclusion, the corresponding values were 9/25 subjects and 58/218 episodes. These definitions distinguish label overlap from clinical coronary substrate.

**Table S1. Retained duration and beat counts by subject-overlap group.**

| Subject group | Ischemic duration (s) | HR-related duration (s) | Retained ischemic beats | Retained HR-related beats |
|---|---:|---:|---:|---:|
| Both labels | 59,982 | 51,295 | 92,807 | 76,043 |
| Ischemic only | 612,115 | 0 | 927,377 | 0 |
| HR-related only | 0 | 121,149 | 0 | 202,952 |
| Neither retained | 0 | 0 | 0 | 0 |

**Table S2. Historical-header coronary-disease categories among heart-rate-related contributors.**

| Any raw annotated ischemic episode | Documented coronary disease | No coronary disease documented in available header | Unknown/insufficient | Total |
|---|---:|---:|---:|---:|
| No | 1 | 7 | 8 | 16 |
| Yes | 7 | 1 | 1 | 9 |
| Total | 8 | 8 | 9 | 25 |

## S5. Sensitivity results

Across individualized and fixed hysteresis constants, the direct ischemic-minus-heart-rate-related mean-absolute estimate ranged from 1.64 to 4.87 ms, and each 95% CI included zero. The expanded 5–600-s grid estimate was 4.36 ms (95% CI, −0.70 to 9.42). Primary-grid tau selected the 10-s lower boundary in 71/190 leads and 300-s upper boundary in 15/190 leads; the expanded-grid analysis therefore assesses boundary restriction without optimizing on episode outcomes.

Alternative LTST protocols were not fully invariant. Direct estimates were 5.97 ms (95% CI, 1.86 to 10.34) under `.sta`, 4.87 ms (95% CI, −0.34 to 10.23) under primary `.stb`, and 6.36 ms (95% CI, 0.72 to 12.20) under `.stc`. The baseline contrasts remained positive. These analyses show threshold sensitivity and are not used to replace the primary `.stb` result.

Rate-dynamic adjustment yielded 5.51 ms (95% CI, 2.92 to 8.10) for ischemic versus baseline, 2.23 ms (95% CI, −0.50 to 4.97) for heart-rate-related versus baseline, and 3.47 ms (95% CI, −1.51 to 7.69) for the equal-subject direct contrast. The attenuation of the heart-rate-related association is consistent with residual dynamic-rate confounding.

Under `.stb`, cross-lead consolidation found 405 concordant multilead ischemic segments (39 subjects), 60 concordant multilead heart-rate-related segments (12 subjects), and three discordant segments (two subjects). Single-lead classifications remained more common. Source tables also report `.sta` and `.stc`.

## S6. Direct-QT uncertainty

In same-protocol validation (n=391), direct-QT MAE/median absolute error/bias/RMSE were 23.89/18.01/−3.48/30.96 ms. In fully held-out annotator 1 (n=487), they were 29.52/21.70/+3.28/39.17 ms; for annotator 2 (n=402), 24.78/20.96/−7.31/36.25 ms. Same-protocol QRS-onset/T-offset error covariance was 158.99 ms² (correlation 0.381; standardized correlation 0.354). Positive covariance reduced mean derived QT sigma from 33.31 to 28.05 ms. The validation standardized correlation was carried unchanged into held-out coverage calculations to prevent use of held-out truth for recalibration.

## S7. EDB mapping

EDB has 90 records from 79 subjects. Repeated-subject groups were mapped according to database documentation (e0118–e0122, e0123–e0126, e0129/e0133, e0136/e0139, e0147/e0148, e0154/e0155, and e0162/e0163). Thirty-three source-overlap records were excluded before analysis, leaving 57 records: e0104, e0106, e0107, e0110, e0111, e0112, e0114, e0116, e0121, e0122, e0124, e0126, e0129, e0133, e0136, e0166, e0170, e0203, e0210, e0211, e0303, e0405, e0406, e0409, e0411, e0509, e0603, e0604, e0606, e0607, e0609, e0612, and e0704. The reproducible one-to-one `e0xxx`/`sele0xxx` mapping is supplied in the review archive. Forty-eight unique subjects contributed 200 retained generic ST episodes. This analysis cannot distinguish ischemic from heart-rate-related labels. LTST record s20021 and EDB record e0113 are documented as the same source subject; the database-specific analyses were not combined as independent replications at subject level.

## Supplementary figures

**Figure S1.** Specification curve across annotation protocol, individualized/expanded-grid hysteresis, fixed constants, and rate-dynamic adjustment.

**Figure S2.** Primary and expanded-grid hysteresis constant distributions, including boundary selections.

**Figure S3.** Episode-level signed QT–RR effects, showing mixed positive and negative directions.

**Figure S4.** Cross-lead label concordance under the primary `.stb` protocol.

**Figure S5.** Model architecture, dataset roles and analysis workflow, and primary LTST DB cohort flow.

![](figures_revision/figureS5_architecture_workflow.png)

## Supplementary editable tables

Editable source tables, the machine-readable results manifest, and source data and generation scripts for every figure are included in the blinded review archive.
