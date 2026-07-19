"""Regenerate all manuscript + supplement figures as 300-dpi TIFF (LZW) for
Elsevier submission. Sources: saved summary CSVs / residual CSVs.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 11})
DPI = 300
FIGDIR = "paper/figures"
SAVE = dict(dpi=DPI, pil_kwargs={"compression": "tiff_lzw"})


def load_ltst_episode_means():
    df = pd.read_csv("results/ltstdb_residuals.csv", low_memory=False)
    df = df[df.episode_type.notna()]
    df = df[df.qt_ms.between(200, 700) & df.pred_qt_ms.between(200, 700)]
    return df


# ---- Fig 1: primary residuals by episode (LTST + EDB) ----
def fig1():
    ltst = load_ltst_episode_means()
    edb = pd.read_csv("results/edb_residuals.csv")
    edb = edb[edb.episode_type.notna()]
    edb = edb[edb.qt_ms.between(200, 700) & edb.pred_qt_ms.between(200, 700)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
    o = ["matched_baseline", "rate_related", "ischemic"]
    lab = ["Matched\nbaseline", "Rate-related\n(non-ischemic)", "Ischemic"]
    m = [ltst[ltst.episode_type == k].abs_resid_ms.mean() for k in o]
    se = [ltst[ltst.episode_type == k].abs_resid_ms.sem() for k in o]
    axes[0].bar(lab, m, yerr=[1.96 * s for s in se], capsize=4, color=["#4C72B0", "#DD8452", "#C44E52"])
    axes[0].set_ylabel("Mean |QT-RR baseline residual| (ms)")
    axes[0].set_title(f"LTST DB (primary), n={ltst.record.nunique()} records")
    oe = ["matched_baseline", "ischemic"]
    labe = ["Matched\nbaseline", "ST-change\nepisode"]
    me = [edb[edb.episode_type == k].abs_resid_ms.mean() for k in oe]
    see = [edb[edb.episode_type == k].abs_resid_ms.sem() for k in oe]
    axes[1].bar(labe, me, yerr=[1.96 * s for s in see], capsize=4, color=["#4C72B0", "#C44E52"])
    axes[1].set_title(f"EDB (replication), n={edb.record.nunique()} records")
    plt.tight_layout()
    plt.savefig(f"{FIGDIR}/fig1_residuals_by_episode.tiff", **SAVE)
    plt.close()


# ---- Fig 2: coverage PICP ----
def fig2():
    df = pd.read_csv("results/coverage_picp.csv")
    nominal = [50, 68, 80, 90, 95]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3), sharey=True)
    for ax, src in zip(axes, df.source.unique()):
        sub = df[df.source == src]
        ax.plot([0, 100], [0, 100], "k--", lw=1, label="ideal")
        for _, r in sub.iterrows():
            ax.plot(nominal, [r[f"PICP_{n}"] * 100 for n in nominal], marker="o", label=r["landmark"])
        ax.set_title(src, fontsize=10)
        ax.set_xlabel("Nominal coverage (%)")
        ax.set_xlim(45, 100); ax.set_ylim(30, 100)
    axes[0].set_ylabel("Empirical coverage PICP (%)")
    axes[0].legend(fontsize=8, loc="upper left")
    plt.tight_layout()
    plt.savefig(f"{FIGDIR}/fig2b_coverage_picp.tiff", **SAVE)
    plt.close()


# ---- Fig 3: tau distribution ----
def fig3():
    ltst = load_ltst_episode_means()
    tau = ltst.drop_duplicates(["record", "lead"])["tau_s"]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(tau, bins=[5, 12, 17, 22, 32, 47, 62, 92, 122, 152, 182, 242, 302],
            color="#4C72B0", edgecolor="white")
    ax.set_xlabel("Per-record-lead selected hysteresis time constant τ (s)")
    ax.set_ylabel("Number of record-leads")
    ax.set_title("Individualized QT-RR hysteresis window selection (LTST DB)")
    plt.tight_layout()
    plt.savefig(f"{FIGDIR}/fig3_tau_distribution.tiff", **SAVE)
    plt.close()


# ---- Fig S1/S2: sensitivity residuals from saved episode means ----
def figS(proto, fname, title):
    s = pd.read_csv(f"results/episode_means_{proto}.csv").set_index("episode_type")
    order = ["matched_baseline", "rate_related", "ischemic"]
    labels = ["Matched\nbaseline", "Rate-related\n(non-ischemic)", "Ischemic"]
    m = [s.loc[k, "mean_abs_resid_ms"] for k in order]
    se = [s.loc[k, "sem_ms"] for k in order]
    fig, ax = plt.subplots(figsize=(5.2, 4.5))
    ax.bar(labels, m, yerr=[1.96 * x for x in se], capsize=4, color=["#4C72B0", "#DD8452", "#C44E52"])
    ax.set_ylabel("Mean |QT-RR baseline residual| (ms)")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(f"{FIGDIR}/{fname}.tiff", **SAVE)
    plt.close()


if __name__ == "__main__":
    fig1(); fig2(); fig3()
    figS("sta", "figS1_residuals_sta", "LTST DB — .sta (Vmin=75 µV, Tmin=30 s; sensitive)\nn=85 records")
    figS("stc", "figS2_residuals_stc", "LTST DB — .stc (Vmin=100 µV, Tmin=60 s; specific)\nn=85 records")
    print("all 5 TIFF figures written to", FIGDIR)
