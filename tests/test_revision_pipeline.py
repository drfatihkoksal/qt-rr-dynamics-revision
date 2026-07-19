import numpy as np

from src.run_residual_pipeline import assign_matched_baseline


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

