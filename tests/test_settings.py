# -*- coding: utf-8 -*-
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import settings_manager as sm  # noqa: E402
from color_scheme import ColorScheme  # noqa: E402


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(sm, "SETTINGS_FILE", str(path))
    return path


def test_missing_file_returns_defaults_copy(settings_file):
    loaded = sm.load_settings()
    loaded["colors"]["TEXT"] = "#000000"
    assert sm.DEFAULTS["colors"]["TEXT"] == "#c0caf5"


def test_corrupt_file_returns_defaults(settings_file):
    settings_file.write_text("{not json", encoding="utf-8")
    assert sm.load_settings() == sm.DEFAULTS


def test_non_dict_json_returns_defaults(settings_file):
    settings_file.write_text("[1, 2]", encoding="utf-8")
    assert sm.load_settings() == sm.DEFAULTS


def test_partial_section_is_merged_with_defaults(settings_file):
    settings_file.write_text(json.dumps({"colors": {"TEXT": "#111111"}}), encoding="utf-8")
    loaded = sm.load_settings()
    assert loaded["colors"]["TEXT"] == "#111111"
    assert loaded["colors"]["DARK"] == sm.DEFAULTS["colors"]["DARK"]


def test_malformed_section_is_ignored(settings_file):
    settings_file.write_text(json.dumps({"params": "oops"}), encoding="utf-8")
    assert sm.load_settings()["params"] == sm.DEFAULTS["params"]


def test_save_roundtrip_leaves_no_temp_files(settings_file):
    data = sm.load_settings()
    data["params"]["nplc"] = 2.5
    sm.save_settings(data)
    assert sm.load_settings()["params"]["nplc"] == 2.5
    assert [p.name for p in settings_file.parent.iterdir()] == ["settings.json"]


def test_set_color_accepts_known_role():
    old = ColorScheme.TEXT
    try:
        assert ColorScheme.set_color("text", "#aabbcc")
        assert ColorScheme.TEXT == "#AABBCC"
    finally:
        ColorScheme.TEXT = old


@pytest.mark.parametrize("role", ["LABEL_SIZE", "set_color", "NOPE"])
def test_set_color_rejects_non_color_roles(role):
    before = ColorScheme.LABEL_SIZE
    assert not ColorScheme.set_color(role, "#aabbcc")
    assert ColorScheme.LABEL_SIZE == before


def test_set_color_rejects_bad_hex():
    assert not ColorScheme.set_color("TEXT", "red")
