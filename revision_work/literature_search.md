# Literature verification log

**Search date:** 2026-07-19  
**Purpose:** verify canonical metadata and identify peer-reviewed sources needed for the revised framing. No “no study has” claim was retained.

## Method

Targeted title/DOI searches used Crossref/PubMed/publisher records and official database pages. Inclusion required a peer-reviewed article directly supporting dataset provenance, ECG delineation, QT/RR hysteresis, or clustered inference. Titles, journal, year, pagination/article number, and DOI were checked against a canonical or publisher record. PhysioNet dataset descriptions were used for database counts and repeated-subject mappings, not as substitutes for peer-reviewed clinical claims.

## Retained and verified records

- Kalyakulina et al., *IEEE Access* 2020, LUDB delineation database. DOI: 10.1109/ACCESS.2020.3029211. Dataset DOI: 10.13026/eegm-h675.
- Laguna et al., *Computers in Cardiology* 1997, QTDB. DOI: 10.1109/CIC.1997.648140.
- Jiménez-Pérez et al., *Computing in Cardiology* 2019, U-Net ECG delineation. DOI: 10.23919/CinC49843.2019.9005824.
- Peimankar and Puthusserypady, *Expert Systems with Applications* 2020, DENS-ECG. DOI: 10.1016/j.eswa.2020.113911.
- Doggart et al., ISSC 2024, uncertainty-calibrated QT regression. DOI: 10.1109/ISSC61953.2024.10603025.
- Jager, Moody, and Mark, *Computers in Cardiology* 1995, transient ischemic/non-ischemic ST changes. DOI: 10.1109/CIC.1995.482766.
- Jager et al., *Medical & Biological Engineering & Computing* 2003, LTST DB, pages corrected to 172–182. DOI: 10.1007/BF02344885; PubMed PMID 12691437.
- Faganeli and Jager, *Physiological Measurement* 2010, LTST episode classification. DOI: 10.1088/0967-3334/31/3/004.
- Malik et al., *Drug Safety* 2016, universal QT/RR hysteresis correction. DOI: 10.1007/s40264-016-0406-0; PubMed PMID 26968541.
- Gravel et al., *Annals of Noninvasive Electrocardiology* 2017;22:e12463, QT/RR hysteresis systematic review. DOI: 10.1111/anec.12463.
- Taddei et al., *European Heart Journal* 1992, EDB. DOI: 10.1093/oxfordjournals.eurheartj.a060332.
- Goldberger et al., *Circulation* 2000, PhysioNet. DOI: 10.1161/01.CIR.101.23.e215.
- Cameron and Miller, *Journal of Human Resources* 2015, cluster-robust inference. DOI: 10.3368/jhr.50.2.317.

## Exclusions/changes

- The LUDB preprint citation was replaced by the peer-reviewed IEEE Access paper.
- The earlier LTST DB page range 172–183 was corrected to 172–182.
- ICH E14 was removed because the revised manuscript does not compare an absolute dynamic residual with directional regulatory QTc treatment effects.
- Sources concerning manual QT disagreement and TOST were removed from the shortened revision because those claims no longer drive the interpretation.
- A wild-cluster-bootstrap citation was not used because the final pipeline used subject bootstrap/permutation and cluster-robust models rather than a wild cluster procedure.
