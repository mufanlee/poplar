"""Tests for trust.py — workspace trust management."""

import json
from pathlib import Path

from poplar.core.trust import (
    is_workspace_trusted,
    trust_workspace,
    untrust_workspace,
    get_trusted_workspaces,
    _trust_file_path,
    _load_trusted,
    _save_trusted,
    _TRUST_FILE_NAME,
)


class TestTrustCore:
    def test_trust_file_name(self):
        assert _TRUST_FILE_NAME == "trusted.json"

    def test_trust_file_path_in_poplar_dir(self):
        path = _trust_file_path()
        assert path.name == "trusted.json"
        assert ".poplar" in str(path)

    def test_load_trusted_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        assert _load_trusted() == set()

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        _save_trusted({"/a", "/b"})
        loaded = _load_trusted()
        assert loaded == {"/a", "/b"}

    def test_load_trusted_corrupted_file(self, tmp_path, monkeypatch):
        p = tmp_path / "trusted.json"
        p.write_text("not json", encoding="utf-8")
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: p)
        assert _load_trusted() == set()


class TestTrustWorkspace:
    def test_not_trusted_initially(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        assert not is_workspace_trusted(Path(tmp_path))

    def test_trust_and_check(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        d = tmp_path / "myproject"
        d.mkdir()
        trust_workspace(d)
        assert is_workspace_trusted(d)

    def test_subdirectory_inherits_trust(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        parent = tmp_path / "project"
        parent.mkdir()
        child = parent / "src"
        child.mkdir(parents=True)
        trust_workspace(parent)
        assert is_workspace_trusted(child)

    def test_untrust_removes(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        d = tmp_path / "temp"
        d.mkdir()
        trust_workspace(d)
        assert is_workspace_trusted(d)
        untrust_workspace(d)
        assert not is_workspace_trusted(d)

    def test_untrust_nonexistent_noop(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        d = tmp_path / "never_trusted"
        d.mkdir()
        untrust_workspace(d)  # should not raise

    def test_double_trust_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        d = tmp_path / "proj"
        d.mkdir()
        trust_workspace(d)
        trust_workspace(d)  # idempotent
        assert len(get_trusted_workspaces()) == 1

    def test_get_trusted_workspaces_sorted(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        for name in ["/c", "/a", "/b"]:
            # Directly save to avoid path resolution issues
            _save_trusted(set(get_trusted_workspaces()) | {name})
        ws = get_trusted_workspaces()
        # Should be sorted
        assert ws == ["/a", "/b", "/c"]

    def test_non_trusted_sibling_not_trusted(self, tmp_path, monkeypatch):
        monkeypatch.setattr("poplar.core.trust._trust_file_path", lambda: tmp_path / "trusted.json")
        proj_a = tmp_path / "proj_a"
        proj_b = tmp_path / "proj_b"
        proj_a.mkdir()
        proj_b.mkdir()
        trust_workspace(proj_a)
        assert not is_workspace_trusted(proj_b)
