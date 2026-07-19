# Uncertainty-Aware Deep-Learning Delineation of QT–RR Dynamics During Ischemic and Heart-Rate–Related ST Episodes in Long-Term Ambulatory ECG

## Highlights

- A deep-learning ECG delineator provided beat-level landmarks and predictive uncertainty.
- Coverage was near nominal in same-protocol validation but lower in fully held-out records.
- Both database-labeled episode types had larger absolute QT–RR departures than baseline.
- The direct between-label comparison did not demonstrate a larger ischemic departure.
- Label uncertainty, subject overlap, cardiac substrate, and rate dynamics limit interpretation.

## Abstract

**Background:** We evaluated a deep-learning ECG delineator and used it to compare QT–RR dynamics during database-labeled ischemic and heart-rate-related ST episodes.

**Methods:** A one-dimensional U-Net-style model was pretrained on the Lobachevsky University Electrocardiography Database and fine-tuned on the QT Database (QTDB). Landmark and direct-QT errors and prediction-interval coverage were evaluated in same-protocol validation data and 11 fully held-out, dual-annotated QTDB records. The model was then applied to all 86 Long-Term ST Database (LTST DB) records (80 unique subjects). Absolute and signed deviations from an individualized, hysteresis-adjusted QT–RR relation were summarized by episode and subject. The primary contrast compared database-labeled ischemic with heart-rate-related episodes; secondary contrasts used episode-matched baseline. Subject overlap, rate dynamics, hysteresis, and annotation protocols were examined in sensitivity analyses.

**Results:** Under the primary `.stb` annotation protocol, the equal-subject difference in mean absolute residual was 4.87 ms (95% confidence interval [CI], −0.34 to 10.23; p=0.065) for ischemic versus heart-rate-related episodes; unique-subject bootstrap retained both summaries for nine overlapping subjects. A larger ischemic departure was not demonstrated under the primary protocol, although estimates were annotation-protocol sensitive. Relative to matched baseline, absolute residual increased by 7.67 ms (95% CI, 5.06 to 10.95) during 1,060 ischemic episodes from 60 subjects and by 4.57 ms (95% CI, 2.34 to 6.90) during 218 heart-rate-related episodes from 25 subjects. Nine of 25 subjects contributing retained heart-rate-related episodes also had an annotated ischemic episode; these subjects contributed 58/218 (26.6%) heart-rate-related episodes. The overlap interaction was imprecise (2.54 ms; 95% CI, −2.50 to 7.57; p=0.305). Rate-dynamic adjustment attenuated the heart-rate-related-versus-baseline estimate to 2.23 ms (95% CI, −0.50 to 4.97), and the adjusted direct estimate was 3.47 ms (95% CI, −1.51 to 7.69). Direct-QT 95% interval coverage under the independence approximation was 96.7% in same-protocol validation and 90.6% and 95.3% in the two held-out annotation sets; covariance-aware coverage was 90.5%, 85.2%, and 92.0%, respectively.

**Conclusions:** Both database-labeled episode types were associated with greater absolute QT–RR departure than matched baseline. Under the primary `.stb` protocol, the direct comparison did not demonstrate a larger departure during ischemic episodes, although estimates were annotation-protocol sensitive. This does not exclude an ischemic repolarization effect or establish physiological equivalence. ECG-based label uncertainty, subject-level overlap and substrate, and residual rate/hysteresis effects constrain mechanistic interpretation. Prediction-interval transportability was limited on fully held-out records.

**Keywords:** electrocardiography; QT interval; myocardial ischemia; deep learning; uncertainty; ambulatory monitoring

## 1. Introduction

Automated ECG delineation converts wave boundaries into intervals used for physiological and clinical inference [1–4]. Uncertainty-aware QT measurement can additionally quantify confidence in individual estimates [5]. Point accuracy alone does not show whether a model's uncertainty estimates have the advertised frequency interpretation, particularly after a change in dataset or annotator. Empirical prediction-interval coverage—the proportion of reference measurements contained within nominal intervals—provides a direct check of interval performance.

The LTST DB characterizes transient ST patterns using ECG morphology and heart-rate context [6–8]. These annotations support reproducible comparisons but are not independent episode-level proof that myocardial ischemia is present or absent. Likewise, a heart-rate-related ST label does not imply that every concurrent QT change must be fully explained by the immediately preceding RR interval. QT adaptation exhibits hysteresis, so a dynamic rather than instantaneous QT–RR reference is needed [9,10].

This study had two aims. First, we evaluated point-estimate accuracy and predictive-interval behavior of a deep-learning delineator, including direct QT uncertainty and comparison with dual-expert annotations. Second, we tested whether absolute and signed deviations from an individualized, hysteresis-adjusted QT–RR relation increased during database-labeled ischemic ST episodes and whether those deviations differed from database-labeled heart-rate-related ST episodes. The direct between-label comparison remained the primary endpoint. Subject overlap, rate dynamics, annotation protocol, and lead concordance were assessed to define the range of plausible interpretations.

## 2. Methods

### 2.1 Study design and datasets

LUDB was used for pretraining and QTDB for fine-tuning and uncertainty evaluation [1,2]. Eleven QTDB records with two annotation files were held out from model development. The remaining 93 fine-tuning records and their record-level validation split did not overlap the held-out set. One of 105 QTDB catalog records lacked a compatible delineation annotation and was not parsed. The primary application used LTST DB `.stb` annotations (100 µV minimum ST deviation and 30 s minimum duration) [7]. All 86 records were verified against official checksums and processed; their identifiers mapped to 80 unique subjects. EDB provided a generic ST-episode-versus-baseline analysis after exclusion of QTDB source overlaps [11]. Repeated EDB recordings were mapped to subjects using official documentation.

The inferential units were defined as follows: a subject was a unique person; a record was one ambulatory recording; a record-lead was one signal channel; an episode was one lead-specific annotated interval; and a beat was one eligible normal-beat measurement. Counts were generated from a machine-readable cohort-flow file. Public, de-identified data were analyzed; no new participants were enrolled.

### 2.2 Model and training

Each input was a 500-sample (2.0 s at 250 Hz), single-lead window spanning 200 samples before and 300 after an annotated R peak. Per-window z normalization was used. The 5,982,928-parameter network had four encoder stages (32, 64, 128, and 256 channels), a 512-channel bottleneck, and a symmetric decoder. Each stage used two kernel-7 convolutions, batch normalization, and rectified-linear activation; max pooling and stride-2 transposed convolution performed down- and up-sampling, with encoder–decoder skip connections. A four-class samplewise head predicted background, P, QRS, and T segments. A pooled bottleneck head predicted normalized location, log variance, and presence probability for P onset, QRS onset, QRS offset, and T offset.

The total loss was cross-entropy segmentation loss plus five times the presence-masked Gaussian landmark negative log likelihood plus binary cross-entropy presence loss. Log variance was clipped to [−14,6] and the gradient norm to 5. Adam used an initial learning rate of 0.001, batch size 256, ReduceLROnPlateau (factor 0.5; patience 4), and early stopping after 10 unimproved epochs, with a 40-epoch maximum and seed 0. The lowest validation-loss checkpoint was retained. LUDB pretraining preceded QTDB fine-tuning. Further implementation detail and the exact equations are in the Supplement.

### 2.3 Delineation and direct QT uncertainty

Normal-beat annotations anchored the windows. Predictions required presence probability >0.5 for both QRS onset and T offset. QT was their time difference. The submitted independence approximation was

$$
\sigma_{QT,ind}^2=\sigma_T^2+\sigma_Q^2.
$$

Because the two landmark errors arise from the same beat and model, validation data were also used to estimate their standardized error correlation, giving

$$
\sigma_{QT,cov}^2=\sigma_T^2+\sigma_Q^2-2\rho\sigma_T\sigma_Q.
$$

The correlation was estimated only in same-protocol validation data and applied unchanged to held-out data. We report direct-QT mean absolute error (MAE), median absolute error, bias, root mean squared error, and empirical prediction-interval coverage. These checks do not establish calibration in LTST DB or EDB, where beat-level expert QT ground truth was unavailable.

### 2.4 Episode labels, QT–RR reference, and matching

The primary `.stb` stream classifies lead-specific ST episodes as ischemic, heart-rate-related, or other according to database algorithms and expert review [6–8]. Mixed/other intervals were not assigned to either primary label. Simultaneous leads were audited for concordant and discordant labels.

For each record-lead, eligible non-episode beats fitted an individualized linear QT–RR relation after exponential RR smoothing. Candidate hysteresis constants were selected by cross-validation on eligible non-episode data, never on episode outcomes. The primary grid was 10–300 s; a 5–600 s grid and fixed 30, 60, 120, and 180 s constants were sensitivities. The signed residual was measured QT minus predicted individualized baseline QT; its absolute value measured departure magnitude, not QT prolongation. For each episode, the algorithm selected the nearest available non-episode window of the same duration; windows were not reused, and deterministic candidate ordering resolved ties. Primary matching did not impose time-of-day or rate-slope balance. Rate-dynamic sensitivities therefore adjusted for smoothed RR and RR/heart-rate slope.

### 2.5 Outcomes and statistics

The ischemic-versus-heart-rate-related contrast was the prespecified primary scientific comparison. In response to concerns regarding unequal beat contribution and patient-level confounding, the revision designated the equal-subject estimate as the principal inferential analysis. Each label-specific subject summary received equal weight within its label group. Because nine subjects contributed to both groups, 20,000 bootstrap samples were drawn from the 76 unique subjects; both label-specific summaries were retained whenever an overlapping subject was selected. Percentile confidence intervals and two-sided bootstrap tail probabilities were calculated from that distribution. The originally submitted uncertainty-weighted beat-level model was retained as a sensitivity analysis. Major secondary estimands compared each label with matched baseline. The analysis hierarchy additionally comprised one-summary-per-episode models clustered by subject and a paired sensitivity restricted to both-label subjects. Both unweighted and inverse-variance-weighted beat models were reported. Regression standard errors for episode- and beat-level models were clustered by subject to accommodate within-subject dependence [12]. The three equal-subject mean-absolute contrasts formed one Benjamini–Hochberg false-discovery-rate family; other analyses were labeled sensitivity or exploratory. Confidence intervals were emphasized, and non-significance was not interpreted as equivalence.

Reviewer-requested analyses stratified heart-rate-related episodes by any raw annotated ischemic episode and by any retained ischemic episode, tested an episode-state-by-overlap interaction, and explored historical header evidence of coronary disease (documented, no coronary disease documented in the available header, or unknown). Missing documentation was not treated as disease absence. Sensitivities included signed outcomes, alternative hysteresis constants, `.sta/.stb/.stc` protocols, rate-dynamic adjustment, cross-lead concordance, and EDB generic ST episodes. Direct contrasts across protocols, hysteresis specifications, and rate adjustment used unique-subject resampling that retained both labels for overlapping subjects. The ECG examples were selected reproducibly as episodes closest to the prespecified subgroup median, not as maximum effects.

## 3. Results

### 3.1 Cohort flow and uncertainty evaluation

All 86 LTST DB records (80 subjects; 190 record-leads) were processed. Eighty-one records from 76 subjects contained a retained primary-label episode. The final analysis included 1,060 ischemic and 218 heart-rate-related episodes, 1,020,184 and 278,995 episode beats, respectively, and 1,131,733 matched-baseline beats. Of 19,801,021 beat-lead annotations, 19,281,040 were normal; edge, signal-quality, delineation, and plausibility exclusions left 19,278,075 analysis-eligible measurements. Because annotations are lead-specific, these audit counts are beat-lead rather than unique temporal beats.

Direct-QT MAE was 23.89 ms in same-protocol validation and 29.52 and 24.78 ms against held-out annotators 1 and 2. Corresponding biases were −3.48, +3.28, and −7.31 ms. QRS-onset and T-offset error correlation was 0.381 in validation. At nominal 95%, independence-based QT coverage was 96.7%, 90.6%, and 95.3%; covariance-aware coverage was 90.5%, 85.2%, and 92.0%. T-offset landmark coverage was 90.3%, 76.2%, and 91.8%, showing annotator- and dataset-dependent undercoverage (Table 2; Fig. 3).

### 3.2 Subject overlap

Among 25 subjects contributing retained heart-rate-related episodes, 9 (36.0%) also had at least one database-annotated ischemic episode. They contributed 58/218 (26.6%) retained heart-rate-related episodes, 51,295/172,444 s (29.7%) of their retained duration, and 76,043/278,995 (27.3%) retained beats. Before quality and delineation exclusions, the corresponding proportions were 10/26 subjects (38.5%), 61/228 episodes (26.8%), 51,724/173,772 s (29.8%), and 76,754/280,930 annotated normal beats (27.3%). The mutually exclusive retained groups comprised 51 ischemic-only, 16 heart-rate-related-only, 9 both-label, and 4 no-retained-label subjects (Table 1).

### 3.3 Primary and baseline contrasts

Under the primary `.stb` protocol, the equal-subject difference in mean absolute QT–RR residual was 4.87 ms (95% CI, −0.34 to 10.23; p=0.065; adjusted p=0.065) for ischemic versus heart-rate-related episodes. The unique-subject bootstrap treated the 76 subjects as independent clusters and retained both label summaries for the nine overlapping subjects. The interval admitted effects in both directions and did not demonstrate a larger ischemic residual. The episode-level estimate was 5.63 ms (95% CI, −2.90 to 14.15; p=0.193). The paired analysis of nine both-label subjects was −1.36 ms (95% CI, −9.27 to 5.64; p=0.770), and was necessarily imprecise.

Relative to matched baseline, the equal-subject absolute residual increased during ischemic episodes by 7.67 ms (95% CI, 5.06 to 10.95; adjusted p<0.001) and during heart-rate-related episodes by 4.57 ms (95% CI, 2.34 to 6.90; adjusted p<0.001). Episode-level estimates were 6.96 ms (95% CI, 2.17 to 11.75) and 3.89 ms (95% CI, 1.39 to 6.40), respectively. Beat-level subject-clustered estimates were positive for both baseline contrasts under unweighted and uncertainty-weighted models, while the direct beat contrast was near zero. Thus the principal conclusion did not depend solely on beat count or weighting (Table 3; Fig. 2).

### 3.4 Subgroups, direction, and sensitivities

Heart-rate-related episodes versus baseline increased equal-subject mean absolute residual by 6.20 ms (95% CI, 3.00 to 9.68) among the nine subjects with any raw ischemic annotation and by 3.66 ms (95% CI, 0.78 to 6.67) among the 16 without one. The interaction was 2.54 ms (95% CI, −2.50 to 7.57; p=0.305), providing no precise evidence that overlap modified the association. Among those 16 subjects without an annotated ischemic episode, historical headers indicated documented coronary disease in one, no coronary disease documented in the available header in seven, and unknown/insufficient information in eight. Across all 25 heart-rate-related contributors, exploratory historical-header strata yielded 8.74 ms in eight subjects with documented coronary disease, 0.38 ms in eight with no coronary disease documented in the available header, and 4.61 ms in nine with insufficient/unknown information. These incomplete historical data cannot establish substrate or episode mechanism.

Signed-residual contrasts were not consistently directional. Median episode residual was negative in 545/1,060 (51.4%) ischemic episodes and 126/218 (57.8%) heart-rate-related episodes. Subject-level direct signed contrasts included zero. The absolute-residual findings therefore reflect a mixture of positive and negative departures rather than uniform QT prolongation.

Rate-dynamic adjustment preserved the ischemic-versus-baseline association (5.51 ms; 95% CI, 2.92 to 8.10) but attenuated the heart-rate-related-versus-baseline estimate (2.23 ms; 95% CI, −0.50 to 4.97). The equal-subject, rate-adjusted direct estimate was 3.47 ms (95% CI, −1.51 to 7.69; p=0.182) using the same unique-subject bootstrap structure. Direct estimates varied across reasonable hysteresis assumptions: 4.87 ms under individualized primary `.stb`, 4.36 ms with the expanded grid, and 1.64–4.66 ms across fixed 30–180 s constants; all corresponding intervals included zero. Alternative annotation streams produced direct estimates of 5.97 ms (95% CI, 1.86 to 10.34; `.sta`) and 6.36 ms (95% CI, 0.72 to 12.20; `.stc`), demonstrating protocol dependence rather than a uniformly stable specificity result. Primary tau selection accumulated at 10 s in 71/190 record-leads and at 300 s in 15/190, supporting the expanded-grid sensitivity. Cross-lead auditing identified 405 concordant multilead ischemic segments, 60 concordant heart-rate-related segments, and three discordant segments.

### 3.5 EDB and ECG examples

After source-overlap screening, 57 EDB records (48 event-contributing subjects) yielded 200 generic ST episodes. Their equal-subject absolute residual exceeded matched baseline by 9.07 ms (95% CI, 5.32 to 13.58). Because EDB does not supply the LTST ischemic-versus-heart-rate-related contrast used here, this supports a generic ST-episode association only, not ischemia specificity.

Figure 1 shows raw ECG morphology, model landmarks and uncertainty, QT–RR residuals, heart rate, and ST trends for a both-label subject and a subject without an annotated ischemic episode. These reproducibly selected cases permit signal-level inspection but do not establish the cohort effect.

## 4. Discussion

The study separates three findings. Database-labeled ischemic episodes showed larger absolute QT–RR departure than matched baseline. Heart-rate-related episodes also showed larger departure than baseline. Under the primary `.stb` annotation protocol, the direct equal-subject comparison did not demonstrate a larger departure in ischemic episodes; estimates were sensitive to the annotation protocol. This narrow primary-protocol result does not imply that ischemia has no ventricular-repolarization effect and does not establish that the episode types are physiologically equivalent; its CI included both a modest ischemic excess and a modest heart-rate-related excess.

Label meaning is central. LTST labels classify ST morphology in heart-rate context, but do not independently confirm or exclude myocardial ischemia at every episode. “Heart-rate-related” describes the ST/heart-rate pattern, not complete explanation of simultaneous QT behavior by RR. Label ambiguity, shared autonomic activation, incomplete QT adaptation modeling, cardiac substrate, and morphology-dependent delineation error therefore remain plausible, non-exclusive explanations.

Same-subject overlap was material: nine of 25 heart-rate-related contributors also had ischemic annotations, accounting for about 27% of retained heart-rate-related episodes and beats. Similar unadjusted associations in both overlap strata suggest that same-subject overlap may not be the sole explanation. However, the imprecise interaction and attenuation after rate-dynamic adjustment preclude a firm conclusion regarding the relative contributions of overlap, cardiac substrate, label uncertainty, and residual rate dynamics. Historical headers indicated heterogeneous coronary substrate among subjects contributing heart-rate-related episodes, but were incomplete and could not establish episode mechanism. “No annotated ischemic episode” is therefore not synonymous with “non-ischemic patient.”

Rate dynamics provided a second caution. Adjustment for dynamic rate attenuated the heart-rate-related baseline association until its CI included zero, whereas the ischemic baseline estimate remained positive. Direct effects changed with annotation protocol and hysteresis choices. These results make residual rate/hysteresis confounding plausible and oppose selecting one favorable specification. A more flexible dynamic QT–RR model and independently adjudicated episodes would be needed to distinguish rate adaptation from other processes.

Signed analyses showed both QT lengthening and shortening. The absolute outcome is distance from an individualized relation, not QT prolongation, and the observed association is best understood as increased mixed-direction departure. Direct-QT errors and held-out undercoverage further show that uncertainty estimates are not universally transportable. The numerical residual magnitude should not be compared directly with regulatory directional QTc treatment-effect thresholds.

LTST DB is a selected ambulatory ST-abnormality cohort, not an unselected Holter sample. Neither the overlap pattern nor the effect estimates should be assumed to reproduce where disease prevalence, medications, morphology, and episode ascertainment differ. The EDB result supports only a generic ST-episode association. Future work needs independent ischemia adjudication, richer clinical covariates, and more subjects exhibiting both labels.

Same-protocol direct-QT coverage was near nominal under the original independence approximation, but held-out coverage and landmark coverage deteriorated. Accounting for positive landmark-error covariance narrowed intervals and revealed undercoverage in all three sets. This is evidence for dataset- and annotator-dependent uncertainty, not universal calibration. Covariance itself also changed across annotation sets, so the validation estimate should not be presumed stable in ambulatory data.

### 4.1 Limitations

Episode labels were ECG-based and did not independently verify ischemia. Episode type was partly confounded by subject, and only nine subjects supported a paired direct contrast. Clinical headers were historical and incomplete. Beat-level observations were highly dependent, although episode- and equal-subject inference reduced reliance on beat count. The linear QT–RR and exponential hysteresis model may not fully capture rapid rate change, autonomic state, or nonlinear response. Baseline selection matched duration and temporal proximity but not time of day; incomplete balance was addressed only by covariate sensitivity analysis. Analysis was restricted to `N`-labeled beats, but adjacent ectopy and conduction abnormalities were not separately excluded. Absolute residual gives no direction. Delineation error may vary with ST–T morphology. Landmark covariance was estimated in a modest validation set and QT uncertainty was not validated against expert ambulatory labels. Held-out undercoverage limits transportability. One development seed/model was used. LTST DB is not representative of an unselected Holter population.

## 5. Conclusions

An uncertainty-aware deep-learning delineator enabled large-scale analysis of ambulatory QT–RR dynamics, although interval coverage deteriorated on fully held-out records. Both database-labeled ischemic and heart-rate-related ST episodes were associated with greater absolute departure than matched baseline. Under the primary `.stb` annotation protocol, the direct comparison did not demonstrate a larger departure during ischemic episodes; estimates were sensitive to the annotation protocol. Because labels were ECG-based and episode type was partly confounded by subject, substrate, and rate dynamics, these findings neither establish physiological equivalence nor exclude an ischemia-specific component. Replication with independent ischemia adjudication and stronger within-subject sampling is required.

## Data and code availability

All source datasets are publicly available through PhysioNet [13]. A blinded, versioned review archive containing the complete analysis code, tests, machine-readable result manifest, frozen checksums, and figure/table source data is supplied with the submission. The permanent public repository and release are identified on the separate title page.

## Declaration of generative AI and AI-assisted technologies

During preparation, the author used Claude (Anthropic) and Codex (OpenAI) to assist with analysis-software development, debugging, statistical-output assembly, and drafting/language editing. The author directed the work, verified the code, results, and text, and takes full responsibility for the manuscript.

## References

1. Kalyakulina AI, Yusipov II, Moskalenko VA, et al. LUDB: a new open-access validation tool for electrocardiogram delineation algorithms. IEEE Access. 2020;8:186181–186190. doi:10.1109/ACCESS.2020.3029211.
2. Laguna P, Mark RG, Goldberger AL, Moody GB. A database for evaluation of algorithms for measurement of QT and other waveform intervals in the ECG. Comput Cardiol. 1997:673–676. doi:10.1109/CIC.1997.648140.
3. Jiménez-Pérez G, Alcaine A, Camara O. U-Net architecture for the automatic detection and delineation of the electrocardiogram. Comput Cardiol. 2019. doi:10.23919/CinC49843.2019.9005824.
4. Peimankar A, Puthusserypady S. DENS-ECG: a deep learning approach for ECG signal delineation. Expert Syst Appl. 2021;165:113911. doi:10.1016/j.eswa.2020.113911.
5. Doggart P, Kennedy A, Bond R, Finlay D. Uncertainty calibrated deep regression for QT interval measurement in reduced lead set ECGs. Proc ISSC. 2024. doi:10.1109/ISSC61953.2024.10603025.
6. Jager F, Moody GB, Mark RG. Characterization of transient ischemic and non-ischemic ST segment changes. Comput Cardiol. 1995:721–724. doi:10.1109/CIC.1995.482766.
7. Jager F, Taddei A, Moody GB, et al. Long-term ST database: a reference for the development and evaluation of automated ischaemia detectors and for the study of the dynamics of myocardial ischaemia. Med Biol Eng Comput. 2003;41:172–182. doi:10.1007/BF02344885.
8. Faganeli J, Jager F. Automatic classification of transient ischaemic and transient non-ischaemic heart-rate related ST segment deviation episodes in ambulatory ECG records. Physiol Meas. 2010;31:323–337. doi:10.1088/0967-3334/31/3/004.
9. Malik M, Johannesen L, Hnatkova K, Stockbridge N. Universal correction for QT/RR hysteresis. Drug Saf. 2016;39:577–588. doi:10.1007/s40264-016-0406-0.
10. Gravel H, Jacquemet V, Dahdah N, Curnier D. Clinical applications of QT/RR hysteresis assessment: a systematic review. Ann Noninvasive Electrocardiol. 2018;23:e12514. doi:10.1111/anec.12514.
11. Taddei A, Distante G, Emdin M, et al. The European ST-T database: standard for evaluating systems for the analysis of ST-T changes in ambulatory electrocardiography. Eur Heart J. 1992;13:1164–1172. doi:10.1093/oxfordjournals.eurheartj.a060332.
12. Cameron AC, Miller DL. A practitioner's guide to cluster-robust inference. J Hum Resour. 2015;50:317–372. doi:10.3368/jhr.50.2.317.
13. Goldberger AL, Amaral LAN, Glass L, et al. PhysioBank, PhysioToolkit, and PhysioNet. Circulation. 2000;101:e215–e220. doi:10.1161/01.CIR.101.23.e215.

## Figure legends

**Figure 1.** Reproducibly selected ECG examples and time-aligned trends. Case A is a subject with both database labels; Case B has no annotated ischemic episode. Raw single-lead ECG is shown with QRS onset, T offset, prediction uncertainty, and analyzed quantities. Longer panels show heart rate, ST deviation, signed and absolute QT–RR residual, and QT uncertainty. Examples are illustrative, not proof of cohort effects.

![](figures_revision/figure1_ecg_examples.png)

**Figure 2.** Subject- and episode-level absolute QT–RR effects. Points show individual units; summaries show estimates and 95% confidence intervals. The symlog episode axis preserves extreme observations without allowing them to determine visual scale.

![](figures_revision/figure2_subject_episode_effects.png)

**Figure 3.** Landmark and direct-QT empirical prediction-interval coverage in same-protocol validation and fully held-out records against annotators 1 and 2. The diagonal denotes nominal coverage. Covariance-aware QT intervals use correlation estimated in same-protocol validation.

![](figures_revision/figure3_calibration.png)

```{=latex}
\clearpage
\begin{landscape}
\newgeometry{margin=0.65in}
\small
\setlength{\tabcolsep}{3pt}
```

## Tables

**Table 1. Retained cohort composition and subject-level overlap.**

| Subject group | Subjects | Records | Record-leads | Ischemic episodes | HR-related episodes |
|---|---:|---:|---:|---:|---:|
| Both labels | 9 | 9 | 20 | 62 | 58 |
| Ischemic only | 51 | 57 | 130 | 998 | 0 |
| HR-related only | 16 | 16 | 32 | 0 | 160 |
| Neither retained | 4 | 4 | 8 | 0 | 0 |

**Table 2. Direct-QT accuracy and 95% prediction-interval coverage.**

| Set | n | MAE (ms) | Median AE (ms) | Bias (ms) | RMSE (ms) | Coverage, independent | Coverage, covariance-aware |
|---|---:|---:|---:|---:|---:|---:|---:|
| Same-protocol validation | 391 | 23.89 | 18.01 | −3.48 | 30.96 | 0.967 | 0.905 |
| Fully held-out, annotator 1 | 487 | 29.52 | 21.70 | +3.28 | 39.17 | 0.906 | 0.852 |
| Fully held-out, annotator 2 | 402 | 24.78 | 20.96 | −7.31 | 36.25 | 0.953 | 0.920 |

**Table 3. Main hierarchical mean-absolute-residual estimands.**

| Contrast | Level/weighting | Effect (ms) | 95% CI (ms) | p | Adjusted p | Subjects | Episodes |
|---|---|---:|---:|---:|---:|---:|---:|
| Ischemic vs HR-related | Equal subject; partially paired bootstrap | 4.87 | −0.34 to 10.23 | 0.065 | 0.065 | 76 | 1,278 |
| Ischemic vs baseline | Equal subject | 7.67 | 5.06 to 10.95 | <0.001 | <0.001 | 60 | 1,060 |
| HR-related vs baseline | Equal subject | 4.57 | 2.34 to 6.90 | <0.001 | <0.001 | 25 | 218 |
| Ischemic vs HR-related | Paired equal subject | −1.36 | −9.27 to 5.64 | 0.770 | — | 9 | — |
| Ischemic vs HR-related | Episode, subject-clustered | 5.63 | −2.90 to 14.15 | 0.193 | — | 76 | 1,278 |

**Table 4A. Reviewer-requested overlap subgroup analyses.**

| Analysis | Group/contrast | Effect (ms) | 95% CI (ms) | p | Subjects | Episodes |
|---|---|---:|---:|---:|---:|---:|
| HR vs baseline | Any raw ischemic episode | 6.20 | 3.00 to 9.68 | — | 9 | 58 |
| HR vs baseline | No annotated ischemic episode | 3.66 | 0.78 to 6.67 | — | 16 | 160 |
| Interaction | Difference between overlap groups | 2.54 | −2.50 to 7.57 | 0.305 | 25 | 218 |

**Table 4B. Rate-dynamic analyses.**

| Analysis | Contrast | Effect (ms) | 95% CI (ms) | p | Subjects | Episodes |
|---|---|---:|---:|---:|---:|---:|
| Rate-dynamic adjusted | Ischemic vs baseline | 5.51 | 2.92 to 8.10 | <0.001 | 60 | 1,060 |
| Rate-dynamic adjusted | HR vs baseline | 2.23 | −0.50 to 4.97 | 0.110 | 25 | 218 |
| Rate-dynamic adjusted | Ischemic vs HR-related | 3.47 | −1.51 to 7.69 | 0.182 | 76 | 1,278 |

Positive values indicate a larger mean absolute residual in the first-named group.

```{=latex}
\restoregeometry
\end{landscape}
```
