# -*- coding: utf-8 -*-
"""Settings persistence — save/load all user preferences to JSON"""
import json
import os
import sys


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
    return os.path.dirname(__file__)


SETTINGS_FILE = os.path.join(_get_settings_dir(), "settings.json")

DEFAULTS = {
    "colors": {
        "TEXT": "#c0caf5",
        "LIGHT": "#1e1f2e",
        "DARK": "#1a1b26",
        "LINE": "#3b3d56",
        "SPECTRUM": "#0db9d7",
        "TREND": "#bb9af7",
        "RESISTANCE": "#f7768e",
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
    "chart_labels": {
        "spectrum": {"x": 8, "y": 8, "w": 80, "h": 24},
        "trend": {"x": 8, "y": 8, "w": 110, "h": 24},
        "sourcemeter": {"x": 8, "y": 8, "w": 100, "h": 24},
    },
}


def load_settings() -> dict:
    """Load settings from JSON, falling back to defaults"""
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULTS
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = DEFAULTS.copy()
        merged.update(data)
        if "colors" in data:
            merged["colors"] = {**DEFAULTS["colors"], **data["colors"]}
        if "params" in data:
            merged["params"] = {**DEFAULTS["params"], **data["params"]}
        if "chart_labels" in data:
            merged["chart_labels"] = {**DEFAULTS["chart_labels"], **data["chart_labels"]}
        return merged
    except (json.JSONDecodeError, IOError):
        return DEFAULTS


def save_settings(settings: dict) -> None:
    """Save settings to JSON"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
