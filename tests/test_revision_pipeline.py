import numpy as np

from src.run_residual_pipeline import assign_matched_baseline
from src.revision_statistics import partially_paired_subject_bootstrap


def test_matched_baseline_ids_are_preserved_and_windows_not_reused():
    samples = np.arange(0, 1000, 10)
    label = np.array([None] * len(samples), dtype=object)
    label[(samples >= 300) & (samples <= 390)] = "ischemic"
    label[(samples >= 600) & (samples <= 690)] = "rate_related"
    spans = [(300, 390, "ischemic", 0), (600, 690, "rate_related", 1)]

    matched_label, matched_id = assign_matched_baseline(
        len(samples), samples, label, spans, fs=10.0)

    idx0 = np.where(matched_id == 0)[0]
    idx1 = np.where(matched_id == 1)[0]
    assert len(idx0) > 0 and len(idx1) > 0
    assert set(idx0).isdisjoint(set(idx1))
    assert np.all(matched_label[idx0] == "matched_baseline")
    assert np.all(matched_label[idx1] == "matched_baseline")
    assert np.all(label[idx0] == None)  # noqa: E711
    assert np.all(label[idx1] == None)  # noqa: E711


def test_partially_paired_bootstrap_keeps_overlap_and_estimand():
    import pandas as pd
    wide = pd.DataFrame({
        "ischemic": [10.0, 20.0, 30.0, np.nan],
        "rate_related": [5.0, np.nan, 15.0, 25.0],
    }, index=["both_a", "ischemic_only", "both_b", "hr_only"])
    result = partially_paired_subject_bootstrap(wide, "unused", seed=7, n_boot=2000)
    est, lo, hi, p, n_unique, n_isc, n_hr, n_both = result
    assert est == np.mean([10, 20, 30]) - np.mean([5, 15, 25])
    assert (n_unique, n_isc, n_hr, n_both) == (4, 3, 3, 2)
    assert lo < est < hi
    assert 0 <= p <= 1
