# Response to Reviewers

**Manuscript:** JECG-S-26-00605  
**Revised title:** *Uncertainty-Aware Deep-Learning Delineation of QT–RR Dynamics During Ischemic and Heart-Rate–Related ST Episodes in Long-Term Ambulatory ECG*

Dear Editor and Reviewers,

Thank you for the detailed and constructive review. We reprocessed the full LTST DB, audited subject identifiers and cohort flow, replaced record/beat-centered inference with a hierarchy including episode and equal-subject analyses, quantified label overlap and substrate, evaluated signed residuals, rate dynamics, hysteresis and label concordance, added direct-QT covariance/coverage validation, and replaced the lead figure with raw ECG examples and time-aligned trends. We also rewrote the manuscript in plain language and narrowed all interpretations of the primary result. The primary scientific comparison was unchanged; in response to concerns about unequal beat contribution and patient-level effects, the revision designated equal-subject analysis as the principal inferential approach. Every reported number is traceable through the machine-readable results manifest and frozen output checksums.

## Reviewer 1

> If this reviewer's understanding is correct, the authors aimed to 1) evaluate "calibrated-uncertainty ECG delineator and 2) compare QT dynamics during and outside ischemic events. This reviewer could not provide a proper evaluation of the manuscript.
>
> General comments
>
> 1. This reviewer is not expert in mathematical methods used in the study. The method section warrants specific expert reviewing.

**Response:** We agree that the submitted Methods were not sufficiently reviewable. The revised Methods section now provides an intuitive description of the two aims, units, network, direct-QT uncertainty, QT–RR reference, matching, and inferential hierarchy. Supplementary Sections S1–S3 give the exact input, layer channels, kernels, loss equations and coefficients, landmark-presence rule, optimizer, scheduler, batch size, stopping rule, seed, split logic, hysteresis equation, matching rule, statistical estimands, cluster definition, bootstrap/permutation procedure, and multiplicity family. The model has 5,982,928 trainable parameters. Code, tests, the software environment, machine-readable outputs, and the exact revision archive are supplied in a blinded review archive.

**Changes in the manuscript:** Methods, Sections 2.1–2.5, lines 50–121; Supplementary Sections S1–S3; Supplementary Figure S5; Data and Code Availability, lines 248–252.

> 2. The text of the manuscript is difficult to read and to understand. This reviewer respectfully suggests using an comprehensible human writing.

**Response:** We rewrote the complete manuscript. The revision separates the three scientific comparisons, defines “absolute residual” in plain language, moves implementation equations to the Supplement, removes rhetorical and mechanistic claims, and leads each Results paragraph with effect estimates and confidence intervals. The title was changed from “Detecting Ischemia-Specific” to the neutral “QT–RR Dynamics During Ischemic and Heart-Rate–Related ST Episodes.”

**Changes in the manuscript:** The manuscript was revised throughout; title and Highlights, lines 1–9; Abstract, lines 10–31; main text, lines 32–256; and tables, lines 301–307.

> 3. From a pathophysiological point of view, it seems very unlikely that ischemic events would have no impact on ventricular repolarization properties. Accordingly, the result stating that "ischemic vs rate-related contrast is null" is highly questionable. ECG strips during and outside ischemic episodes should be shown to corroborate the results.

**Response:** We agree with the concern and corrected the interpretation. The revised Results separately show that database-labeled ischemic episodes differed from matched baseline by 7.67 ms (95% CI, 5.06 to 10.95) in equal-subject mean absolute residual. Under the primary `.stb` protocol, the direct ischemic-versus-heart-rate-related estimate was 4.87 ms (95% CI, −0.34 to 10.23; p=0.065), which means only that this study did not demonstrate a larger ischemic departure under that protocol. It does not show that ischemia has no repolarization effect and does not establish equivalence. The limited paired analysis of nine both-label subjects was −1.36 ms (95% CI, −9.27 to 5.64), underscoring imprecision. Alternative `.sta` and `.stc` protocols produced intervals excluding zero, and this protocol dependence is now explicit.

We added new Figure 1. Case A shows baseline, database-labeled ischemic, and heart-rate-related ECG segments from the same subject; Case B shows baseline and a heart-rate-related episode in a subject without an annotated ischemic episode. QRS onset, T offset, model uncertainty, measured and predicted QT, signed and absolute residual, heart rate, ST deviation, and longer time-aligned trends are displayed. Cases were selected reproducibly as closest to prespecified subgroup medians, not by maximum effect. The selected identifiers and plotted source data are supplied.

**Changes in the manuscript:** Methods, Section 2.5, lines 99–121; Results, Sections 3.3–3.5, lines 142–186; Discussion and Limitations, lines 187–238; Figure 1 legend, lines 288–291.

## Reviewer 2

> Dear author(s),
>
> Congratulations on the interesting work and thorough statistical analysis. The secondary finding on the comparison between ischemic and heart-rate-related non-ischemic episodes provides some interesting discussion.
>
> I am unsure whether your discussion is complete in its consideration of potential explanations or confounders for the secondary finding. There seems to be an unwarranted confidence in the face value of results, without ever questioning the purity of labels or considering per-patient-group effects.
>
> Consider providing some additional context and discussion for the readers' evaluation:
>
> - The heart-rate-related episodes are "by construction explicable by heart rate". But then the finding is that they are not fully explicable by heart rate. Can you please provide some discussion on whether label purity comes into question for these events?

**Response:** We removed the quoted statement and all “pure negative control” language. The revised Methods and Discussion state that LTST labels classify ST patterns using ECG morphology and heart-rate context; they are not independent episode-level confirmation or exclusion of ischemia. A heart-rate-related ST label also does not imply that all simultaneous QT behavior must be explained by RR. We now discuss label uncertainty, autonomic co-activation, incomplete QT–RR adaptation, substrate, and morphology-dependent delineation error as plausible, non-exclusive explanations.

We also tested rate dynamics. Adjustment for dynamic rate preserved the ischemic-versus-baseline estimate at 5.51 ms (95% CI, 2.92 to 8.10), but attenuated heart-rate-related versus baseline to 2.23 ms (95% CI, −0.50 to 4.97). Across fixed 30–180-s and individualized hysteresis specifications, direct estimates ranged from 1.64 to 4.87 ms and their intervals included zero. The `.sta` and `.stc` annotation streams yielded larger direct estimates whose intervals excluded zero, so we explicitly report protocol dependence instead of selecting a favorable result.

**Changes in the manuscript:** Methods, Sections 2.4–2.5, lines 87–121; Results, Section 3.4, lines 155–178; Discussion, lines 187–225; Supplementary Sections S2 and S5; Figures S1, S2, and S4.

> - What is the fraction of rate-related non-ischemic episodes that come from patients with other ischemic episodes? Under limitations you impy that fraction may be small. An ischemic substrate may fully explain the consistency between the two kinds of events at different rates on the same patient. A better understanding of overlap in same patients would help orient the leader.

**Response:** We now answer this directly at each requested level. After all primary exclusions, 9/25 subjects contributing heart-rate-related episodes (36.0%) also had at least one database-annotated ischemic episode. These subjects contributed 9/25 records (36.0%), 20/52 record-leads (38.5%), 58/218 heart-rate-related episodes (26.6%), 51,295/172,444 s of heart-rate-related duration (29.7%), and 76,043/278,995 retained heart-rate-related beats (27.3%). Before quality/delineation exclusions, the corresponding values were 10/26 subjects (38.5%), 61/228 episodes (26.8%), 51,724/173,772 s (29.8%), and 76,754/280,930 annotated normal beats (27.3%). Full subject-level and overlap-group tables are provided.

The heart-rate-related-versus-baseline equal-subject effect was 6.20 ms (95% CI, 3.00 to 9.68) in nine subjects with any raw ischemic annotation and 3.66 ms (95% CI, 0.78 to 6.67) in 16 subjects without one. The interaction was 2.54 ms (95% CI, −2.50 to 7.57; p=0.305). Similar unadjusted associations suggest that same-subject overlap may not be the sole explanation, but the imprecise interaction and attenuation after rate-dynamic adjustment preclude a firm conclusion. The nine-subject within-subject direct comparison is presented as a limited sensitivity analysis.

**Changes in the manuscript:** Results, Sections 3.2–3.4, lines 135–178; Discussion, lines 187–225; Tables 1 and 4A, lines 301–305; Supplementary Section S4 and Tables S1–S2.

> - If there is a true consistency between (a) ischemic events and (b) rate-related non-ischemic events from patients without any ischemic episodes; then consider providing some discussion on the non-ischemic patients in the LTST DB: are they generally characterised by advanced disease and increased cardiac risk? Would you expect the consistency to be replicated in any Holter dataset?

**Response:** We no longer use “non-ischemic patients”; we use “subjects without an annotated ischemic episode.” We extracted historical clinical-header metadata using three categories: documented coronary disease, no coronary disease documented in the available header, and unknown/insufficient. Among the 16 heart-rate-related contributors without an annotated ischemic episode, these categories contained 1, 7, and 8 subjects, respectively. Across all 25 heart-rate-related contributors, the categories contained 8, 8, and 9 subjects; their exploratory heart-rate-related-versus-baseline estimates were 8.74 ms (95% CI, 5.46 to 12.07), 0.38 ms (95% CI, −1.83 to 3.03), and 4.61 ms (95% CI, 1.00 to 8.38). Because headers are historical and incomplete, these results cannot establish clinical substrate or episode mechanism.

We added a generalizability paragraph stating that LTST DB is a selected ambulatory ST-abnormality cohort and that neither substrate nor effect estimates should be expected automatically in an unselected Holter dataset. The EDB analysis is now described only as a generic ST-episode-versus-baseline association (9.07 ms; 95% CI, 5.32 to 13.58), not replication of ischemia specificity.

**Changes in the manuscript:** Results, Sections 3.4–3.5, lines 155–186; Discussion and Limitations, lines 187–238; Table 4A, line 305; Supplementary Sections S4 and S7 and Supplementary Table S2.

> Please consider providing some of the above discussion to steel-man the interpretation of your results, and orient the reader as to the range of their validity.

**Response:** The Discussion was reorganized around label meaning, subject overlap and substrate, rate dynamics/hysteresis, signed direction, measurement uncertainty, and generalizability. We explicitly state that the primary interval includes effects in both directions; a non-significant p value is not treated as equivalence. Signed analyses showed mixed directions—51.4% of ischemic and 57.8% of heart-rate-related episodes had negative median residual—so absolute residual is not called QT prolongation. We believe these changes define the validity range more accurately and transparently.

**Changes in the manuscript:** Discussion and Limitations, lines 187–238; Conclusion, lines 239–247; Supplementary Figures S1–S5.

## Additional data-integrity changes

During the cohort audit, an incomplete local LTST DB signal file was identified and replaced only after its official checksum was verified. Consequently, all 86 catalogued records were processed rather than the 85 reported previously. Official record identifiers mapped these to 80 unique subjects. The revised analysis contains 1,060 ischemic and 218 heart-rate-related episodes. All old 85-record results were replaced consistently. We also mapped repeated EDB recordings to subjects and clustered/equal-weighted at the unique-subject level.

The primary scientific comparison was unchanged. However, in response to the reviewers’ concerns regarding patient-level effects and unequal beat contribution, we changed the principal inferential unit from the originally submitted beat-level, record-lead-clustered model to an equal-subject analysis. This changed the point estimate from −1.78 ms in the submitted uncertainty-weighted beat-level model to +4.87 ms in the equal-subject analysis, although neither analysis demonstrated a statistically conclusive between-label difference. Because nine subjects contributed to both label groups, the final equal-subject confidence interval and p value use unique-subject bootstrap resampling that retains both summaries for overlapping subjects. The submitted beat-level model is now reported as a sensitivity analysis.

All continuous-line references above correspond to the final `manuscript_revised_numbered.pdf`, generated from the same source as the clean and marked DOCX files. Section names are provided first because journal-system conversion may repaginate Word files.
