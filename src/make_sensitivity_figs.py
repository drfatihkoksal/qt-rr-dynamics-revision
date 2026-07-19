"""Regenerate .sta/.stc residuals, build per-episode residual figures, save a
compact per-episode summary, and delete the large intermediate CSV. Run after
the pipeline has written results/ltstdb_residuals_<proto>.csv.
"""
import sys
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 11})

PROTO_LABEL = {
    "sta": ".sta (Vmin=75 µV, Tmin=30 s; sensitive)",
    "stc": ".stc (Vmin=100 µV, Tmin=60 s; specific)",
}
FIG_NAME = {"sta": "figS1_residuals_sta.png", "stc": "figS2_residuals_stc.png"}


def main(proto):
    csv = f"results/ltstdb_residuals_{proto}.csv"
    df = pd.read_csv(csv, low_memory=False)
    df = df[df.episode_type.notna()]
    df = df[df.qt_ms.between(200, 700) & df.pred_qt_ms.between(200, 700)]

    order = ["matched_baseline", "rate_related", "ischemic"]
    labels = ["Matched\nbaseline", "Rate-related\n(non-ischemic)", "Ischemic"]
    m = [df[df.episode_type == k].abs_resid_ms.mean() for k in order]
    se = [df[df.episode_type == k].abs_resid_ms.sem() for k in order]
    n = [int((df.episode_type == k).sum()) for k in order]

    fig, ax = plt.subplots(figsize=(5.2, 4.5))
    ax.bar(labels, m, yerr=[1.96 * s for s in se], capsize=4,
           color=["#4C72B0", "#DD8452", "#C44E52"])
    ax.set_ylabel("Mean |QT-RR baseline residual| (ms)")
    ax.set_title(f"LTST DB — {PROTO_LABEL[proto]}\nn={df.record.nunique()} records")
    plt.tight_layout()
    plt.savefig(f"paper/figures/{FIG_NAME[proto]}", dpi=150)

    summ = pd.DataFrame(dict(episode_type=order, mean_abs_resid_ms=m,
                             sem_ms=se, n_beats=n))
    summ.to_csv(f"results/episode_means_{proto}.csv", index=False)
    print(f"{proto}: means", {k: round(v, 2) for k, v in zip(order, m)})
    print(f"saved paper/figures/{FIG_NAME[proto]} and results/episode_means_{proto}.csv")


if __name__ == "__main__":
    main(sys.argv[1])
