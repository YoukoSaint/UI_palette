# UI Palette — PyQt5 Dynamic Theme Template

⚠️ AI AGENTS: Before writing any code, read REPRODUCE.md — this README is only an overview.

## Quick Start (for a NEW project)

1. Copy ALL 5 `.py` files into your project directory
2. `pip install pyqt5 pyqtgraph`
3. Edit window title, param labels, and curve names to match your domain
4. `settings.json` auto-generates on first save — it does NOT appear by itself

## Minimal Viable File Set — ALL 5 REQUIRED

| File | Required | Role |
|------|----------|------|
| `color_scheme.py` | **YES** | 10 color roles, QSS generator, `hex_to_rgba()`. Zero Qt imports — root dependency. |
| `color_panel.py` | **YES** | 170px sidebar: 10 `ColorPickerRow` widgets + Reset. Without it, colors exist but users cannot change them. |
| `plot_widgets.py` | **YES** | 3 pyqtgraph charts, `DraggableLabel` subclass, `DataSimulator`, `ChartPanel`. |
| `main_window.py` | **YES** | Host window: param panel, collapsible toggles, save orchestration. Entry point. |
| `settings_manager.py` | **YES** | JSON persistence: load/save with deep-merge. Without it, nothing survives restarts. |

## Architecture (all 5 files + runtime flow)

```
settings_manager.py ── DEFAULTS ──→ load_settings() / save_settings()
         │ (initial values)                    ▲ (MainWindow._save)
         ▼                                     │
  ┌──────────────┐  picker   ┌──────────────┐  signal  ┌───────────────┐
  │ ColorScheme  │◄──────────│ ColorPanel   │─────────►│ ChartPanel    │
  │ 10 class attrs│  change  │ 10 picker    │          │ 3 PlotWidgets │
  │ get_stylesheet│─────────►│ rows + Reset │          │ DraggableLabel│
  │ hex_to_rgba() │          └──────────────┘          │ DataSimulator │
  └──────┬───────┘                                     └───────────────┘
         │ QSS → QApplication.setStyleSheet()                   │
         ▼                                                      ▼
  main_window.py ────────────────────────────────────────────────
  QMainWindow: param(300px) │ charts │ color(170px) │ log(150px)
  _make_edge_btn()×3 → _toggle_*_panel() → _save()
  F10 fullscreen, Esc normal
```

Per-change: picker → set_color() → setStyleSheet() → refresh_colors() → _save()

## Color Roles (all 10 require user-facing pickers)

| Role | Default | Category |
|------|---------|----------|
| TEXT | #c0caf5 | Base — foreground text, status bar, labels, inputs |
| LIGHT | #1e1f2e | Base — GroupBox bg, combobox dropdown |
| DARK | #1a1b26 | Base — QMainWindow/chart background |
| LINE | #3b3d56 | Base — borders, splitter, scrollbar |
| BTN | #3b3d56 | Base — button bg/border (split from LINE for independent control) |
| SPECTRUM | #0db9d7 | Curve — spectrum line (w=2.2) + semi-transparent fill |
| TREND | #bb9af7 | Curve — trend line (w=2) + symbol markers |
| RESISTANCE | #f7768e | Curve — sourcemeter line (w=2.2, connect="finite") |
| GRID | #2c2d3f | Display — chart grid at alpha 0.4 |
| AXIS | #565f89 | Display — axis line + tick label pens |

## Patterns to Copy (the 3 gaps agents hit most often)

1. **Collapsible toggles** — `_make_edge_btn(text,tooltip)` → 12×30px QPushButton (hardcoded colors). Wire `.clicked` to `_toggle_*_panel()` which calls `_save()`. 3 instances: left/right/bottom.
2. **DraggableLabel** — QLabel subclass. `DraggableLabel(text, color, parent)`. Call `_label.set_color(hex)` in `refresh_color()`. Pos/size auto-persisted on release.
3. **Settings** — `from settings_manager import load_settings, save_settings`. `load_settings()` BEFORE building UI. `_save()` after every change.

## Key Design Rules
- Class attrs for colors → `ColorScheme.TEXT` in f-strings. `get_stylesheet()` re-reads every call.
- Pen/brush at `__init__`, re-created in `refresh_color()` — hot path zero-allocation.
- QSS on `QApplication` (not QMainWindow), applied LAST.
- Colors loaded BEFORE panel construction. Signals AFTER param restore → no redundant save.
- **Every color has a picker** — no orphan roles (REPRODUCE.md Design Philosophy).

## Where to Go Next (REPRODUCE.md)

| Section | Location |
|---------|----------|
| Integration checklist (11 steps) | Lines 1066–1078 |
| Full step-by-step with code blocks | Steps 1–7 |
| Settings JSON schema + merge logic | Lines 757–841 |
| Parameter panel design principles | Lines 900–977 |
| Extension points (add colors, replace simulator, wire hardware) | Lines 990–1064 |
| Performance checklist | Lines 1082–1093 |
