"""Subject-overlap, clinical-substrate, interaction, and rate-adjusted models."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf


OUTCOMES = ("mean_abs_resid_ms", "median_abs_resid_ms",
            "mean_signed_resid_ms", "median_signed_resid_ms")


def mean_ci(arr: np.ndarray, seed: int, n_boot: int = 10000):
    arr = np.asarray(arr, float); rng = np.random.default_rng(seed)
    boot = rng.choice(arr, (n_boot, len(arr)), replace=True).mean(axis=1)
    lo, hi = np.quantile(boot, [.025, .975])
    return float(arr.mean()), float(lo), float(hi)


def welch_diff(a: np.ndarray, b: np.ndarray):
    a=np.asarray(a,float); b=np.asarray(b,float)
    est=a.mean()-b.mean(); va=a.var(ddof=1)/len(a); vb=b.var(ddof=1)/len(b)
    se=np.sqrt(va+vb); df=(va+vb)**2/(va**2/(len(a)-1)+vb**2/(len(b)-1))
    crit=stats.t.ppf(.975,df)
    return float(est),float(est-crit*se),float(est+crit*se),float(2*stats.t.sf(abs(est/se),df))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--episode-effects",type=Path,default=Path("revision_work/analysis/episode_matched_effects.csv"))
    ap.add_argument("--raw-episodes",type=Path,default=Path("revision_work/audit/ltstdb_raw_episodes_stb.csv"))
    ap.add_argument("--clinical",type=Path,default=Path("revision_work/audit/subject_clinical_metadata.csv"))
    ap.add_argument("--out",type=Path,default=Path("revision_work/analysis/subgroup_effects.csv"))
    args=ap.parse_args()
    effects=pd.read_csv(args.episode_effects)
    raw=pd.read_csv(args.raw_episodes)
    clinical=pd.read_csv(args.clinical)
    ischemic_subjects=set(raw.loc[raw.episode_type=="ischemic","subject_id"])
    effects["has_any_raw_ischemic_episode"]=effects.subject_id.isin(ischemic_subjects)
    retained_ischemic=set(effects.loc[effects.episode_type=="ischemic","subject_id"])
    effects["has_any_retained_ischemic_episode"]=effects.subject_id.isin(retained_ischemic)
    effects=effects.merge(clinical,on="subject_id",how="left",validate="many_to_one")
    rows=[]
    hr=effects[effects.episode_type=="rate_related"].copy()
    for oi,outcome in enumerate(OUTCOMES):
        value=f"delta_{outcome}"
        for definition in ("raw", "retained"):
            flag_col=f"has_any_{definition}_ischemic_episode"
            subject=hr.groupby(["subject_id",flag_col],as_index=False)[value].mean()
            for flag,label in ((True,f"any_{definition}_ischemic_episode"),
                               (False,"no_annotated_ischemic_episode")):
                arr=subject.loc[subject[flag_col]==flag,value].to_numpy()
                est,lo,hi=mean_ci(arr,20260719+oi)
                rows.append({"analysis":"hr_episode_vs_baseline","subgroup_variable":f"{definition}_ischemic_overlap",
                             "subgroup":label,"outcome":outcome,"effect_ms":est,"ci_low_ms":lo,
                             "ci_high_ms":hi,"p_value":np.nan,"subjects":len(arr),
                             "episodes":len(hr[hr[flag_col]==flag])})
            a=subject.loc[subject[flag_col],value].to_numpy()
            b=subject.loc[~subject[flag_col],value].to_numpy()
            est,lo,hi,p=welch_diff(a,b)
            rows.append({"analysis":f"episode_state_x_{definition}_ischemic_overlap",
                         "subgroup_variable":"interaction",
                         "subgroup":"difference_in_hr_episode_effect","outcome":outcome,"effect_ms":est,
                         "ci_low_ms":lo,"ci_high_ms":hi,"p_value":p,"subjects":len(subject),
                         "episodes":len(hr)})
        for status,sub in hr.groupby("coronary_disease_status"):
            arr=sub.groupby("subject_id")[value].mean().to_numpy()
            if len(arr)<2: continue
            est,lo,hi=mean_ci(arr,20260800+oi)
            rows.append({"analysis":"hr_episode_vs_baseline_exploratory_clinical",
                         "subgroup_variable":"coronary_disease_status","subgroup":status,
                         "outcome":outcome,"effect_ms":est,"ci_low_ms":lo,"ci_high_ms":hi,
                         "p_value":np.nan,"subjects":len(arr),"episodes":len(sub)})

    # Episode-level rate-dynamic adjustment, clustered by unique subject.
    long_rows=[]
    for _,r in effects.iterrows():
        for state,suffix in ((1,"episode"),(0,"baseline")):
            item={"subject_id":r.subject_id,"episode_type":r.episode_type,"state":state}
            for outcome in OUTCOMES:
                item[outcome]=r[f"{outcome}_{suffix}"]
            item["rr_smoothed_ms"]=r[f"median_rr_smoothed_ms_{suffix}"]
            item["dhr_dt_bpm_per_s"]=r[f"median_dhr_dt_bpm_per_s_{suffix}"]
            long_rows.append(item)
    long=pd.DataFrame(long_rows)
    for kind in ("ischemic","rate_related"):
        sub=long[long.episode_type==kind].dropna()
        for outcome in OUTCOMES:
            model=smf.ols(f"{outcome} ~ state + rr_smoothed_ms + dhr_dt_bpm_per_s",sub).fit(
                cov_type="cluster",cov_kwds={"groups":sub.subject_id,"use_correction":True})
            ci=model.conf_int().loc["state"]
            rows.append({"analysis":"episode_vs_baseline_rate_dynamic_adjusted",
                         "subgroup_variable":"episode_type","subgroup":kind,"outcome":outcome,
                         "effect_ms":model.params["state"],"ci_low_ms":ci.iloc[0],
                         "ci_high_ms":ci.iloc[1],"p_value":model.pvalues["state"],
                         "subjects":sub.subject_id.nunique(),"episodes":len(sub)//2})
    event=pd.DataFrame({"subject_id":effects.subject_id,
                        "ischemic_indicator":(effects.episode_type=="ischemic").astype(int),
                        "rr_smoothed_ms":effects.median_rr_smoothed_ms_episode,
                        "dhr_dt_bpm_per_s":effects.median_dhr_dt_bpm_per_s_episode,
                        **{outcome:effects[f"{outcome}_episode"] for outcome in OUTCOMES}}).dropna()
    for outcome in OUTCOMES:
        model=smf.ols(f"{outcome} ~ ischemic_indicator + rr_smoothed_ms + dhr_dt_bpm_per_s",event).fit(
            use_t=True,cov_type="cluster",cov_kwds={"groups":event.subject_id,"use_correction":True})
        ci=model.conf_int().loc["ischemic_indicator"]
        rows.append({"analysis":"ischemic_vs_hr_rate_dynamic_adjusted",
                     "subgroup_variable":"episode_label","subgroup":"ischemic_minus_hr",
                     "outcome":outcome,"effect_ms":model.params["ischemic_indicator"],
                     "ci_low_ms":ci.iloc[0],"ci_high_ms":ci.iloc[1],
                     "p_value":model.pvalues["ischemic_indicator"],
                     "subjects":event.subject_id.nunique(),"episodes":len(event)})
    pd.DataFrame(rows).to_csv(args.out,index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=="__main__": main()
