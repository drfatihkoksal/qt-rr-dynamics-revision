"""Generate supplementary architecture, analysis-workflow, and cohort-flow figure."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import pandas as pd

OUT = Path("paper/figures_revision")
SRC = Path("revision_work/figure_source")
OUT.mkdir(parents=True, exist_ok=True)
SRC.mkdir(parents=True, exist_ok=True)


def box(ax, xy, wh, text, color="#d9eaf7", fontsize=8):
    x, y = xy; w, h = wh
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015",
                       facecolor=color, edgecolor="#3f5364", linewidth=.8)
    ax.add_patch(p)
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fontsize)


def arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9,
                                color="#526573", linewidth=.9))


def main():
    fig, axs = plt.subplots(3, 1, figsize=(10, 11), layout="constrained")
    for ax in axs:
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    ax = axs[0]
    ax.set_title("A  Delineator architecture", loc="left", fontweight="bold")
    labels = [
        ("1×500 ECG\n2.0 s, 250 Hz", "#f2f2f2"),
        ("Encoder\n32→64→128→256\n2×Conv7+BN+ReLU", "#d9eaf7"),
        ("Bottleneck\n512 channels", "#c7dcef"),
        ("Decoder + skips\n256→128→64→32", "#d9eaf7"),
        ("Segmentation\nBG/P/QRS/T", "#dff0d8"),
    ]
    xs = [.02, .18, .41, .58, .82]
    widths = [.13, .19, .14, .19, .15]
    for i, ((lab, col), x, w) in enumerate(zip(labels, xs, widths)):
        box(ax, (x, .52), (w, .25), lab, col)
        if i: arrow(ax, (xs[i-1]+widths[i-1], .645), (x, .645))
    box(ax, (.43, .10), (.25, .22), "Pooled landmark head\n4 × (location, log variance, presence)\n5,982,928 total parameters", "#fce5cd")
    arrow(ax, (.48, .52), (.53, .32))

    ax = axs[1]
    ax.set_title("B  Dataset roles and analysis workflow", loc="left", fontweight="bold")
    top = [("LUDB\npretraining", .02), ("QTDB 93\nfine-tuning", .22),
           ("QTDB validation +\n11 held-out records\naccuracy and coverage", .44),
           ("Frozen model", .75)]
    for text, x in top: box(ax, (x, .67), (.18 if x < .7 else .17, .20), text, "#d9eaf7")
    for a, b in [((.20,.77),(.22,.77)), ((.40,.77),(.44,.77)), ((.62,.77),(.75,.77))]: arrow(ax,a,b)
    bottom = [("LTST DB\n86 records / 80 subjects", .02),
              ("Beat delineation +\nindividual QT–RR/hysteresis", .27),
              ("Episode–baseline\nmatching", .53),
              ("Beat / episode /\nequal-subject inference", .76)]
    for text, x in bottom: box(ax, (x, .18), (.20, .22), text, "#dff0d8")
    for a, b in [((.22,.29),(.27,.29)), ((.47,.29),(.53,.29)), ((.73,.29),(.76,.29))]: arrow(ax,a,b)
    arrow(ax, (.835,.67), (.12,.40))
    ax.text(.50, .05, "Reviewer sensitivities: overlap • signed residual • rate dynamics • tau grid • annotation protocol • lead concordance",
            ha="center", fontsize=8)

    ax = axs[2]
    ax.set_title("C  Primary LTST DB cohort flow", loc="left", fontweight="bold")
    flow = [
        ("86 catalogued and checksum-verified records\n80 unique subjects • 190 record-leads", .78),
        ("86 records processed\n19,801,021 beat-lead annotations", .56),
        ("19,281,040 normal-beat annotations\n19,280,285 retained delineations", .34),
        ("19,278,075 analysis-eligible measurements\n81 records • 76 subjects • 1,278 episodes", .12),
    ]
    for text, y in flow: box(ax, (.20, y), (.60, .14), text, "#f2f2f2")
    for y1, y2 in [(1,.70),(.78,.48),(.56,.26)]:
        if y1 <= 1: arrow(ax, (.50, y1), (.50, y2))
    ax.text(.83, .45, "Excluded by reason code:\nnon-normal beat; edge; signal quality;\nabsent delineation; QT plausibility",
            fontsize=8, va="center")

    fig.savefig(OUT/"figureS5_architecture_workflow.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT/"figureS5_architecture_workflow.tiff", dpi=300, bbox_inches="tight",
                pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)

    pd.DataFrame([
        {"panel":"architecture", "item":"input", "value":"1x500 at 250 Hz"},
        {"panel":"architecture", "item":"channels", "value":"32,64,128,256,512"},
        {"panel":"architecture", "item":"parameters", "value":"5982928"},
        {"panel":"cohort", "item":"catalogued_records", "value":"86"},
        {"panel":"cohort", "item":"unique_subjects", "value":"80"},
        {"panel":"cohort", "item":"analysis_episodes", "value":"1278"},
        {"panel":"cohort", "item":"analysis_eligible_beat_leads", "value":"19278075"},
    ]).to_csv(SRC/"figureS5_architecture_workflow.csv", index=False)
    print(OUT/"figureS5_architecture_workflow.tiff")


if __name__ == "__main__":
    main()
