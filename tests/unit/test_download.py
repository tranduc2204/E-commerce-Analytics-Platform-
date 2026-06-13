"""Unit test phát hiện file thiếu (không gọi Kaggle thật)."""

from extract.download_olist import EXPECTED_FILES, missing_files


def test_all_missing_on_empty_dir(tmp_path):
    assert missing_files(tmp_path) == EXPECTED_FILES


def test_none_missing_when_all_present(tmp_path):
    for f in EXPECTED_FILES:
        (tmp_path / f).write_text("col\n")
    assert missing_files(tmp_path) == []


def test_detects_partial(tmp_path):
    (tmp_path / EXPECTED_FILES[0]).write_text("col\n")
    missing = missing_files(tmp_path)
    assert EXPECTED_FILES[0] not in missing
    assert EXPECTED_FILES[1] in missing
