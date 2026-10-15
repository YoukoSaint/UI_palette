# -*- coding: utf-8 -*-
"""Settings persistence — save/load all user preferences to JSON"""
import copy
import json
import os
import sys
import tempfile
from typing import Any, Dict


def _get_settings_dir() -> str:
    """Return the writable directory for settings.json.

    In development (``python main_window.py``), ``__file__`` points to the
    project directory so settings are written alongside the source.

    When compiled with PyInstaller (``sys.frozen`` is True), ``__file__``
    points inside the *temporary* extraction directory which is deleted on
    exit.  We therefore resolve to the directory containing the executable,
    which is persistent and writable.
    """
    if getattr(sys, "frozen", False):
        # Compiled — write settings next to the .exe
        return os.path.dirname(sys.executable)
    # Development — write settings in the project directory
    return os.path.dirname(os.path.abspath(__file__))


SETTINGS_FILE = os.path.join(_get_settings_dir(), "settings.json")

DEFAULTS: Dict[str, Any] = {
    "colors": {
        "TEXT": "#c0caf5",
        "LIGHT": "#1e1f2e",
        "DARK": "#1a1b26",
        "LINE": "#3b3d56",
        "BTN": "#3b3d56",
        "SPECTRUM": "#0db9d7",
        "TREND": "#bb9af7",
        "RESISTANCE": "#f7768e",
        "GRID": "#2c2d3f",
        "AXIS": "#565f89",
    },
    "params": {
        "integration_ms": 10.0,
        "averages": 2,
        "monitor_wl": 632.0,
        "source_type": 0,
        "source_value": 0.003,
        "nplc": 1.0,
        "sample_rate": 5.0,
    },
    # Desktop (PyQt) label geometry — pixels
    "chart_labels": {
        "spectrum": {"x": 8, "y": 8, "w": 80, "h": 24},
        "trend": {"x": 8, "y": 8, "w": 110, "h": 24},
        "sourcemeter": {"x": 8, "y": 8, "w": 100, "h": 24},
    },
    # Web (Plotly) annotation positions — paper coordinates (0-1).
    # Kept separate from "chart_labels" so the two front-ends sharing this
    # file never misread each other's units.
    "chart_labels_web": {
        "spectrum": {"x": 0.02, "y": 0.97},
        "trend": {"x": 0.02, "y": 0.64},
        "sourcemeter": {"x": 0.02, "y": 0.31},
    },
    "panels": {"left": True, "right": True, "log": True},
}


def load_settings() -> dict:
    """Load settings from JSON, falling back to defaults.

    Always returns a fresh deep copy, so callers may mutate the result
    without corrupting ``DEFAULTS``.  Sections with a dict default are
    merged key-by-key; malformed sections in the file are ignored.
    """
    merged = copy.deepcopy(DEFAULTS)
    if not os.path.exists(SETTINGS_FILE):
        return merged
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):  # JSONDecodeError / UnicodeDecodeError / IO
        return merged
    if not isinstance(data, dict):
        return merged

    for key, value in data.items():
        default = merged.get(key)
        if isinstance(default, dict):
            if isinstance(value, dict):
                default.update(value)
        else:
            merged[key] = value
    return merged


def save_settings(settings: dict) -> None:
    """Save settings to JSON atomically (temp file + rename).

    A crash mid-write can no longer leave a truncated settings.json behind.
    """
    directory = os.path.dirname(SETTINGS_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix="settings.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SETTINGS_FILE)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
