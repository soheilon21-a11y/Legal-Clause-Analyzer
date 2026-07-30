"""Tests for the playbook loader (``redlining.playbook``).

Exercises file discovery, validation, error handling for corrupt
files, and playbook-by-ID lookup.
"""

import json
from pathlib import Path

import pytest

from redlining.models import Playbook
from redlining.playbook import (
    load_all_playbooks,
    load_playbook,
    load_playbook_by_id,
)

PLAYBOOKS_DIR = Path("playbooks")


class TestLoadPlaybook:
    def test_loads_valid_playbook(self) -> None:
        path = PLAYBOOKS_DIR / "us_general_commercial.json"
        pb = load_playbook(path)
        assert isinstance(pb, Playbook)
        assert pb.playbook_id == "us_general_commercial"
        assert pb.jurisdiction == "US"
        assert len(pb.rules) >= 1

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="Playbook not found"):
            load_playbook(Path("playbooks/nonexistent.json"))

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_playbook(bad)

    def test_invalid_schema_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "schema_bad.json"
        bad.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
        with pytest.raises(Exception):
            load_playbook(bad)


class TestLoadAllPlaybooks:
    def test_loads_from_default_directory(self) -> None:
        playbooks = load_all_playbooks()
        assert len(playbooks) >= 2
        ids = {pb.playbook_id for pb in playbooks}
        assert "us_general_commercial" in ids
        assert "eu_general_commercial" in ids

    def test_nonexistent_directory_returns_empty(self) -> None:
        result = load_all_playbooks(Path("nonexistent_dir"))
        assert result == []

    def test_skips_corrupt_files(self, tmp_path: Path) -> None:
        valid = {
            "playbook_id": "valid",
            "playbook_name": "Valid",
            "rules": [
                {
                    "clause_type": "Test",
                    "detection_keywords": ["test"],
                    "preferred_wording": "replacement",
                    "reason": "reason",
                }
            ],
        }
        (tmp_path / "good.json").write_text(
            json.dumps(valid), encoding="utf-8"
        )
        (tmp_path / "bad.json").write_text("{broken", encoding="utf-8")

        playbooks = load_all_playbooks(tmp_path)
        assert len(playbooks) == 1
        assert playbooks[0].playbook_id == "valid"

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        assert load_all_playbooks(tmp_path) == []

    def test_results_sorted_by_filename(self, tmp_path: Path) -> None:
        for name, pb_id in [("b.json", "beta"), ("a.json", "alpha")]:
            data = {
                "playbook_id": pb_id,
                "playbook_name": pb_id,
                "rules": [
                    {
                        "clause_type": "X",
                        "detection_keywords": ["x"],
                        "preferred_wording": "y",
                        "reason": "z",
                    }
                ],
            }
            (tmp_path / name).write_text(
                json.dumps(data), encoding="utf-8"
            )

        playbooks = load_all_playbooks(tmp_path)
        assert [pb.playbook_id for pb in playbooks] == ["alpha", "beta"]


class TestLoadPlaybookById:
    def test_finds_existing_playbook(self) -> None:
        pb = load_playbook_by_id("us_general_commercial")
        assert pb.playbook_id == "us_general_commercial"

    def test_missing_id_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="No playbook with id"):
            load_playbook_by_id("nonexistent_playbook_id")
