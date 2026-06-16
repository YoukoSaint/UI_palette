# UI Palette

A user-customizable dynamic color theme system for PyQt5 — 10 independently editable color roles, real-time pyqtgraph charts, and persistent settings.

## Quick Start

```bash
git clone https://github.com/YoukoSaint/UI_palette.git
cd UI_palette
pip install pyqt5 pyqtgraph
python main_window.py
```
Requires Python 3.6+. No database — `settings.json` is auto-generated on first save.

## Architecture

```
ColorScheme (class attrs — single source of truth, zero PyQt imports)
  ├─ get_stylesheet() ──→ QApplication.setStyleSheet()   ← QSS (every widget)
  └─ hex_to_rgba()    ──→ pg.mkPen() / pg.mkBrush()      ← chart pens/brushes

Runtime flow (4 steps per color change):
  ColorPanel picker ──→ ColorScheme.set_color(role, hex)
    ──→ get_stylesheet() → QApplication.instance().setStyleSheet()  ⚠ not QMainWindow
    ──→ ChartPanel.refresh_colors() → _apply_pg_theme() + per-chart pen/brush/fill/label
    ──→ MainWindow._save() → full snapshot to settings.json
```

## Files

| File | Role |
|------|------|
| `color_scheme.py` | Color registry (10 class attrs), QSS generator, `hex_to_rgba()`. Zero Qt imports — root dependency. |
| `color_panel.py` | 170px right sidebar: 10 `ColorPickerRow` widgets in 3 sections + Reset button. |
| `plot_widgets.py` | 3 pyqtgraph charts, `DraggableLabel`, `DataSimulator`, `ChartPanel` container + timer. |
| `main_window.py` | Application entry, full layout, parameter panel, panel toggling, settings orchestration. |
| `settings_manager.py` | JSON persistence: save/load with deep-merge, frozen-exe path resolution. |

## Color System

**5 base colors** (TEXT, LIGHT, DARK, LINE, BTN) drive all QSS via `get_stylesheet()`. **3 chart curve** roles (SPECTRUM, TREND, RESISTANCE) drive plot pens, fills, and DraggableLabel text. **2 chart display** roles (GRID, AXIS) drive grid lines and axis styling — both user-editable in the Color Panel.

Six derived colors are computed inline by `_adjust(hex, amount)` which adds a signed integer to each RGB component:

| Derived | Formula | Controls |
|---------|---------|----------|
| `text2` | `_adjust(TEXT, -30)` | QLabel, QPlainTextEdit, QStatusBar text |
| `text3` | `_adjust(TEXT, -50)` | QPushButton:disabled text |
| `dark2` | `_adjust(DARK, -6)` | QMainWindow, QLineEdit, QSpinBox, QComboBox background |
| `light2` | `_adjust(LIGHT, +10)` | (defined but not consumed in current QSS — reserved for future use) |
| `accent` | `_adjust(LIGHT, +30)` | GroupBox title, focus borders, splitter/scrollbar hover |
| `btn_hover` | `_adjust(BTN, +10)` | QPushButton:hover background |

Three tunable constants on `ColorScheme`: `LABEL_SIZE=14` (chart label font px), `LABEL_ALPHA="ff"` (label background opacity — hex string, parsed at runtime via `int(..., 16)` yielding 0–255), `AXIS_LABEL_SIZE=13` (axis tick font px).

## Color Roles Reference

| Role | Default | Category | Controls |
|------|---------|----------|----------|
| `TEXT` | `#c0caf5` | Base | Foreground text, status bar, chart foreground, labels, inputs |
| `LIGHT` | `#1e1f2e` | Base | GroupBox background, QComboBox dropdown, ScrollBar, disabled buttons |
| `DARK` | `#1a1b26` | Base | QWidget/QMainWindow background, pyqtgraph chart background |
| `LINE` | `#3b3d56` | Base | Borders on GroupBox, QLineEdit, SpinBox, ComboBox, Splitter, ScrollBar |
| `BTN`  | `#3b3d56` | Base | QPushButton background/border (defaults to `LINE`; split for independent control — changing LINE does NOT auto-update BTN) |
| `SPECTRUM` | `#0db9d7` | Chart Curve | Spectrum line (width 2.2) + fill (alpha 60) + DraggableLabel text |
| `TREND` | `#bb9af7` | Chart Curve | Trend line (width 2) + symbol brush (size 3) + DraggableLabel text |
| `RESISTANCE` | `#f7768e` | Chart Curve | SourceMeter line (width 2.2, `connect="finite"`) + DraggableLabel text |
| `GRID` | `#2c2d3f` | Chart Display | Chart grid lines at alpha 0.4 |
| `AXIS` | `#565f89` | Chart Display | Axis line pen + tick label pen |

## Features

- **Dynamic Theme:** All widgets restyled from current `ColorScheme` values via a single `get_stylesheet()` string applied to `QApplication`. Covers QMainWindow, QWidget, QLabel, QGroupBox, QPushButton (including `:hover`, `:pressed`, `:disabled` pseudo-states), QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QSplitter, QPlainTextEdit, QStatusBar, QScrollBar (vertical + horizontal, arrow buttons hidden via `height:0; border:none`). Any color change instantly propagates to every widget and all 3 charts.
- **Color Panel:** 170px right sidebar. 3 labeled sections — "Base Colors" (5 rows), "Chart Curves" (3 rows), "Chart Display" (2 rows). Each row: 10x10 swatch (border `#555`, independent of theme), 28px role label, 64px hex QLineEdit (Enter to apply, red border on invalid), 18px `QColorDialog` picker button. Reset button restores all 10 defaults from `settings_manager.DEFAULTS["colors"]`. **BTN** default is identical to LINE — users should update both together to keep button borders consistent; see REPRODUCE.md for the coupling explanation.
- **Collapsible Panels:** Left (300px parameters), Right (170px colors), Bottom (150px log). Arrow toggle buttons 12x30px placed between panels. Visibility persisted as `"panels": {"left": bool, "right": bool, "log": bool}` — a runtime-only key added by `setdefault`, not in DEFAULTS. **Note:** Toggle buttons use hardcoded colors (`#606060` / `#c0c0c0`) that bypass the dynamic theme. This is a known limitation — they remain visually stable regardless of the selected theme.
- **Parameter Settings:** 7 hardware parameters in 3 GroupBoxes — Spectrometer (integration_ms 1–60000, averages 2–100, monitor_wl 0–10000), SourceMeter (source_type combo Voltage/Current, source_value -100–100, nplc 0.01–10), Acquisition (sample_rate 0.01–1000 Hz). **Note:** `sample_rate` is a user-facing parameter for reference/hardware configuration — it does NOT dynamically control the simulator timer interval (fixed at 500ms). Orphan Start/Stop/Save buttons have `objectName` selectors for hardcoded QSS styling (green/red/blue, bypassing the dynamic theme) but no `clicked` connections — natural attachment points for hardware control.
- **Three Charts:** Vertical `QSplitter` stack. `SpectrumChart` — auto-range, semi-transparent fill (`hex_to_rgba(SPECTRUM, 60)`), throttled every 5th tick (first frame renders immediately; rationale: 1400 data points vs. 2 for scrolling charts — throttled at every 5th tick to avoid saturating the Qt event loop). `TrendChart` — 1000-pt rolling buffer, symbol markers, X linked to SourceMeter via `setXLink`, bottom axis hidden. `SourceMeterChart` — 1000-pt buffer, `connect="finite"`, drives shared X with 60s rolling window. Y-axis widths unified on first show via deferred `QTimer.singleShot(0, ...)`. **Note:** The QSplitter holding the three charts is a local variable (not stored as `self._splitter`), so splitter handle positions are NOT persisted across restarts — users must re-drag handles each session.
- **Draggable Labels:** Per-chart `DraggableLabel` (QLabel subclass). Drag anywhere to move; bottom-right 20x20 corner to resize (min 40x20). Auto font scaling `max(8, height * 0.72)` on every resize. Background composed from `ColorScheme.LIGHT` RGB + `LABEL_ALPHA` opacity, border from `ColorScheme.LINE`, text from curve color. Position/size persisted to `chart_labels` key on mouse release.
- **Data Simulator:** `DataSimulator` static methods — 3 Gaussian peaks (450nm sigma=30 amp=800, 550nm sigma=25 amp=500, 680nm sigma=20 amp=300) with noise `gauss(0,15)`, damped sine `500+200*sin(t*0.5)*exp(-t*0.01)` with noise `gauss(0,10)`, V/I resistance `V=5+0.1*sin(2t)`, `I=0.003+0.0002*cos(3t)` with NaN when I=0. `QTimer` at 500ms, 2 pts/tick. **Replace with real hardware signals** (see REPRODUCE.md).
- **Settings Persistence:** `settings.json` alongside source (or next to `.exe` when frozen via `sys.executable`, not `sys._MEIPASS` — see REPRODUCE.md critical gotcha #7). Full snapshot on every change: 10 colors, 7 params, 3 panel booleans, 3 label positions. Deep-merge on load — per-sub-dict shallow merge so missing keys get defaults and unknown keys survive. **Warning:** On a missing/missing file, `load_settings()` returns the module-level `DEFAULTS` dict **by reference** (not a copy). Any subsequent mutation of the returned dict corrupts the global constant — see REPRODUCE.md for the full explanation and mitigation.
- **Keyboard:** `F10` fullscreen, `Escape` return to normal.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Class attributes for colors (not dict) | `ColorScheme.TEXT` syntax usable directly in f-strings throughout QSS |
| `get_stylesheet()` as function (not file) | Re-reads `ColorScheme` attrs on every call — always reflects current state |
| Pen/brush at `__init__`, re-created in `refresh_color()` | Theme changes are rare; `update_data()` is the hot path — no allocation there |
| `QHBoxLayout` with toggle buttons between panels | Toggle lives at the seam between panel and content, not inside either |
| `sys.executable` for frozen-exe settings path | `sys._MEIPASS` is a temp read-only directory deleted on exit |
| Signal connections AFTER param restore | Prevents `_apply_loaded_params()` from triggering a redundant `_save()` |
| QSS applied LAST (after all widgets + params + signals) | Widget construction can set inline styles that would override the theme |
| PyQt5 `pyqtSignal(dict)` for per-chart data | Signal-driven architecture replaces timer polling for real hardware — see REPRODUCE.md |

## Window & UI Defaults

| Setting | Value | Location |
|---------|-------|----------|
| Window title | "OptoSync — Synchronized Acquisition System" | `main_window.py` line 25 |
| Default size | 1440×920 | `main_window.py` line 26 |
| Minimum size | 1100×700 | `main_window.py` line 27 |
| Log panel buffer | 500 lines max (`setMaximumBlockCount`) | `main_window.py` line 140 |
| Log placeholder text | "Log output — demo mode" | `main_window.py` line 141 |
| Status bar message | "Ready — Demo Mode \| Simulated data" | `main_window.py` line 285 |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'PyQt5'` | Missing dependency | `pip install pyqt5 pyqtgraph` |
| Blank charts on startup | pyqtgraph theme not applied, or chart background mismatch | Verify `_apply_pg_theme()` is called before `refresh_colors()` |
| Settings lost on restart | Frozen exe writing to `sys._MEIPASS` (temp/read-only) | Verify `_get_settings_dir()` uses `sys.executable` |
| Settings lost on restart | Directory write permissions | Check writability of directory containing `settings.json` |
| Custom settings not applied (app uses defaults or crashes on startup) | Manually edited `settings.json` with JSON syntax errors (e.g., trailing comma) or incorrect value types | The app safely falls back to defaults when JSON is unparseable — your data is not lost, only not applied. FIRST validate and fix the JSON (use `python -m json.tool settings.json`). If irrecoverable, RENAME to `settings.json.bak` (do NOT delete — colors, params, and label positions are preserved). Defaults regenerate on next launch. Manually copy values from the `.bak` file back into the fresh settings.json. |
| `QWidget: Must construct a QApplication...` | QWidget instantiated before `QApplication()` | Ensure `QApplication(sys.argv)` runs first in `__main__` |
| Wrong initial colors in picker | `_apply_loaded_colors()` called after `ColorPanel` construction | Colors must be restored before `_setup_ui()` creates the panel |
| Splitter handle positions lost on restart | QSplitter is a local variable, not stored as instance attribute (plot_widgets.py line 299) | Known limitation — re-drag handles after restart. See REPRODUCE.md for the structural reason. |

## License

MIT

---

For step-by-step integration into a new PyQt5 project, see **REPRODUCE.md**.
For the complete settings JSON schema and save/load merge logic, see **REPRODUCE.md**.
For the extension point checklist (adding colors, replacing the simulator, wiring hardware), see **REPRODUCE.md**.
