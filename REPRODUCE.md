# REPRODUCE.md — Agent-Oriented Integration Guide

## Overview

This document is the **primary reference for an AI agent (or developer)** building a new PyQt5 project from this template. It covers the complete color model (5 base + 5 chart roles), the 4-step integration surface, settings persistence, critical gotchas, extension points, and a startup checklist. Read this before modifying any file.

**What this template provides:** A user-customizable dynamic color theme system for PyQt5 with 10 independently editable color roles, real-time charting, draggable chart labels, and persistent settings — all designed around the rule that every color the system uses must have a user-facing picker.

**Target:** Python 3.6+, PyQt5, pyqtgraph.

---

## Design Philosophy

> **颜色可以少，但是一定要都有被用户管理的接口**
> *(Colors can be few, but every one of them must have a user-manageable interface.)*

This is the governing rule — every color must satisfy all four conformance layers:

| Layer | File | Requirement |
|-------|------|-------------|
| 1. Class attribute | `color_scheme.py` | Defined in `ColorScheme` as a class-level string |
| 2. Picker row | `color_panel.py` | Has a `ColorPickerRow` in one of the three sections |
| 3. DEFAULTS entry | `settings_manager.py` | Listed in `DEFAULTS["colors"]` for persistence |
| 4. Consumer | QSS or chart code | Actually rendered (QSS rule, pen, brush, or label style) |

If any one layer is missing, the project is in a violated state — either wire up the orphan or remove it from all layers. Reducing color count to maintain integrity is preferred over carrying dead entries.

**BTN** was split from `LINE` as a first-class base color (v2) to give the user independent control over button appearance. `GRID` and `AXIS` are similarly user-exposed (under "Chart Display"), not internal helpers — every color that appears on screen has a picker.

### Known Conformance Violations

**Start/Stop/Save buttons (color_scheme.py lines 125-130):** The `#btn_start`, `#btn_stop`, and `#btn_save` objectName selectors use 6 hardcoded hex colors that bypass the dynamic theme system entirely. These colors have no user-facing picker rows, no DEFAULTS entries, and no `ColorScheme` class attributes — violating all four conformance layers. This is an intentional breach because Start/Stop/Save carry semantic meaning (green=go, red=stop, blue=save) that should not vary with the user's visual theme. **Replace before production deployment if full conformance is required.**

### Conformance Check

Run this before committing color-related changes:

```python
from color_scheme import ColorScheme, ROLES_BASE, ROLES_CHART
from settings_manager import DEFAULTS

# ALL_ROLES is the canonical list — iterating it via getattr naturally
# excludes tunable constants like LABEL_ALPHA, LABEL_SIZE, AXIS_LABEL_SIZE
# without needing __dict__ or vars() filtering.
ALL_ROLES = ROLES_BASE + ROLES_CHART
defined = {r for r in ALL_ROLES if isinstance(getattr(ColorScheme, r, None), str)}
persisted = set(DEFAULTS["colors"].keys())

# panel_rows requires a running QApplication; verify separately:
#   python -c "from PyQt5.QtWidgets import QApplication; app = QApplication([]);
#   from color_panel import ColorPanel; cp = ColorPanel();
#   print(set(cp._pickers.keys()))"
# Then compare against `defined` and `persisted`.

missing_color_attr = persisted - defined
orphan_default = defined - persisted
assert not missing_color_attr, f"Colors in DEFAULTS missing from ColorScheme: {missing_color_attr}"
assert not orphan_default, f"Colors in ColorScheme missing from DEFAULTS: {orphan_default}"
print("OK: color_scheme.py <-> settings_manager.py in sync")
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              color_scheme.py                 │  ← single source of truth
│  ColorScheme (5 base + 5 chart colors)      │     NO PyQt imports
│  get_stylesheet() → full QSS string         │
│  hex_to_rgba() → (r,g,b,a) for chart pens   │
└──────────────┬──────────────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
┌─────────┐ ┌──────┐ ┌──────────┐
│main_win │ │color │ │plot_wid  │
│dow.py   │ │panel │ │gets.py   │
│         │ │.py   │ │          │
│QSS via  │ │10    │ │pen/brush │
│QApp     │ │picker│ │from      │
│         │ │rows  │ │ColorSch  │
└─────────┘ └──┬───┘ └──────────┘
               │
        color_changed(role, hex)
```

**Data flow:**
1. `ColorPanel` emits `color_changed(role, hex)`
2. `MainWindow._on_color_changed()`: calls `get_stylesheet()` → `QApplication.instance().setStyleSheet()`, then `self._charts.refresh_colors()`, then `self._save()`
3. Chart layer: `_apply_pg_theme()` sets global bg/fg, each chart re-creates pen/brush/label from `ColorScheme`, `_apply_grid_axis()` re-colors grid+axis per chart

---

## File Structure

```
project/
├── color_scheme.py        # Color state + QSS generator + color math (zero Qt imports)
├── color_panel.py         # 10 ColorPickerRow widgets in 3 sections + Reset
├── main_window.py         # Host window, param panel, auto-save, keyboard shortcuts
├── plot_widgets.py        # 3 pyqtgraph charts + DraggableLabel + DataSimulator + ChartPanel
├── settings_manager.py    # JSON persistence: DEFAULTS, deep-merge load, full-snapshot save
└── settings.json           # Auto-generated at runtime (git-ignored)
```

`color_scheme.py` is the **root dependency** — imported by `color_panel.py`, `plot_widgets.py`, and `main_window.py`. `settings_manager.py` is independent of `color_scheme` (it only manages JSON persistence, importing `json`, `os`, `sys`). `color_panel.py` and `plot_widgets.py` are siblings, neither imports the other.

---

## Step 1: `color_scheme.py` — Color Model

This is the single source of truth for all colors. It has zero PyQt imports — pure Python.

### Complete `ColorScheme` class

```python
# color_scheme.py — lines 11-47

ROLES_BASE  = ["TEXT", "LIGHT", "DARK", "LINE", "BTN"]
ROLES_CHART = ["SPECTRUM", "TREND", "RESISTANCE", "GRID", "AXIS"]

class ColorScheme:
    # ── 5 base colors (drive QSS) ──
    TEXT  = "#c0caf5"     # text / foreground
    LIGHT = "#1e1f2e"     # panel / surface backgrounds
    DARK  = "#1a1b26"     # main background
    LINE  = "#3b3d56"     # borders / separators
    BTN   = "#3b3d56"     # button background + border (defaults to LINE)

    # ── 3 chart curve colors ──
    SPECTRUM   = "#0db9d7"
    TREND      = "#bb9af7"
    RESISTANCE = "#f7768e"

    # ── 2 chart display colors ──
    GRID = "#2c2d3f"      # grid lines
    AXIS = "#565f89"      # axis pen + tick labels

    # ── 3 tunable constants ──
    LABEL_SIZE       = 14   # chart label font size (px)
    LABEL_ALPHA      = "ff" # label background opacity (hex: 00=transparent, ff=opaque)
    AXIS_LABEL_SIZE  = 13   # axis tick font size (px)

    @classmethod
    def set_color(cls, role: str, hex_color: str) -> bool:
        if not HEX_PATTERN.match(hex_color):
            return False
        if hasattr(cls, role.upper()):
            setattr(cls, role.upper(), hex_color.upper())
            return True
        return False
```

**Key anti-pattern:** Do NOT replace class attributes with a dict. The f-string ergonomics in `get_stylesheet()` depend on `ColorScheme.TEXT` syntax. A dict would require `ColorScheme.colors["TEXT"]` everywhere.

### `_adjust(hex, amount)` — exact delta values

```python
# color_scheme.py — lines 49-54

def _adjust(hex_color: str, amount: int) -> str:
    """Lighten (+) or darken (-) a hex color by adding `amount` to each RGB channel."""
    hex_color = hex_color.lstrip('#')
    r = max(0, min(255, int(hex_color[0:2], 16) + amount))
    g = max(0, min(255, int(hex_color[2:4], 16) + amount))
    b = max(0, min(255, int(hex_color[4:6], 16) + amount))
    return f"#{r:02x}{g:02x}{b:02x}"
```

The 6 derived colors in `get_stylesheet()` (lines 75-80):

| Derived | Formula | Used for |
|---------|---------|----------|
| `text2` | `_adjust(TEXT, -30)` | QLabel text, QPlainTextEdit text, status bar text |
| `text3` | `_adjust(TEXT, -50)` | Disabled button text |
| `dark2` | `_adjust(DARK, -6)` | QMainWindow bg, QLineEdit/SpinBox bg, status bar bg |
| `light2` | `_adjust(LIGHT, +10)` | (defined but not consumed in current QSS) |
| `accent` | `_adjust(LIGHT, +30)` | GroupBox title, focus border, hover highlight |
| `btn_hover` | `_adjust(BTN, +10)` | QPushButton:hover background |

### `get_stylesheet()` — QSS generation

```python
# color_scheme.py — lines 68-197

def get_stylesheet() -> str:
    text  = ColorScheme.TEXT
    light = ColorScheme.LIGHT
    dark  = ColorScheme.DARK
    line  = ColorScheme.LINE
    btn   = ColorScheme.BTN

    text2 = _adjust(text, -30)
    text3 = _adjust(text, -50)
    dark2 = _adjust(dark, -6)
    accent = _adjust(light, 30)
    btn_hover = _adjust(btn, 10)

    return f"""
    QWidget {{ background-color: {dark}; color: {text}; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; font-size: 13px; }}
    QMainWindow {{ background-color: {dark2}; }}
    QLabel {{ background-color: transparent; color: {text2}; border: none; }}
    QGroupBox {{ background-color: {light}; border: 1px solid {line}; border-radius: 8px; ... }}
    QGroupBox::title {{ ... color: {accent}; }}
    QPushButton {{ background-color: {btn}; color: {text}; border: 1px solid {btn}; ... }}
    QPushButton:hover {{ background-color: {btn_hover}; border-color: {accent}; }}
    QPushButton:pressed {{ background-color: {dark}; }}
    QPushButton:disabled {{ background-color: {light}; color: {text3}; }}
    QLineEdit {{ background-color: {dark2}; color: {text}; border: 1px solid {line}; ... }}
    QLineEdit:focus {{ border-color: {accent}; }}
    QSpinBox, QDoubleSpinBox {{ background-color: {dark2}; color: {text}; border: 1px solid {line}; ... }}
    QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {accent}; }}
    QComboBox {{ background-color: {dark2}; color: {text}; border: 1px solid {line}; ... }}
    QComboBox:focus {{ border-color: {accent}; }}
    QComboBox QAbstractItemView {{ background-color: {light}; color: {text}; ... }}
    QSplitter::handle {{ background-color: {line}; ... }}
    QSplitter::handle:hover {{ background-color: {accent}; }}
    QPlainTextEdit {{ background-color: {dark2}; color: {text2}; border: 1px solid {line}; ... }}
    QStatusBar {{ background-color: {dark2}; color: {text2}; border-top: 1px solid {line}; ... }}
    QScrollBar:vertical {{ background-color: {dark2}; ... }}
    QScrollBar::handle:vertical {{ background-color: {line}; ... }}
    QScrollBar::handle:vertical:hover {{ background-color: {accent}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height:0; border:none; }}
    ...
    """
    # Plus hardcoded #objectName selectors for btn_start/btn_stop/btn_save (lines 125-130)
```

**QSS selector coverage:** The stylesheet targets `QWidget`, `QMainWindow`, `QLabel`, `QGroupBox` + `::title`, `QPushButton` (with `:hover`, `:pressed`, `:disabled` pseudo-states), `QLineEdit` (+ `:focus`), `QSpinBox`/`QDoubleSpinBox` (+ `:focus`), `QComboBox` (+ `:focus`), `QComboBox QAbstractItemView`, `QSplitter::handle` (+ `:hover`), `QPlainTextEdit`, `QStatusBar`, `QScrollBar:vertical`/`:horizontal` (handle + `:hover`, `add-line`/`sub-line` hidden).

The **hardcoded Start/Stop/Save button colors** (lines 125-130) bypass the dynamic theme system entirely:
- `#btn_start`: green (#1a6b3c / #228b4a)
- `#btn_stop`: red (#6b1a1a / #8b2222)
- `#btn_save`: blue (#1a4a6b / #225f8b)

**Guidance for new domain:** Either remove these hardcoded selectors to let the buttons follow the dynamic `QPushButton` theme, or replace the colors with domain-appropriate semantics (e.g., "Arm"/"Trigger"/"Record" for data acquisition). If you add new themed button roles, you must add full conformance (ColorScheme attr + picker row + DEFAULTS entry + QSS consumer).

### `hex_to_rgba()` — chart color math

```python
# color_scheme.py — lines 57-65

def hex_to_rgba(hex_color: str, alpha: int) -> tuple:
    """Convert '#RRGGBB' to (r, g, b, alpha) for pg.mkBrush()."""
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )
```

---

## Step 2: `color_panel.py` — Color Picker UI

### `ColorPickerRow` — single color row

```python
# color_panel.py — lines 16-75

class ColorPickerRow(QWidget):
    color_changed = pyqtSignal(str)  # emits new hex color

    # Layout: [10×10 swatch] [28px label] [64px hex QLineEdit] [18px 🎨 QPushButton]
    #
    # Swatch border is hardcoded '#555' — does not follow dynamic theme.
    # The show_label parameter (default True) exists but is never set to False
    # by any call site — reserved for future compact-layout use.
    #
    # _on_hex(): triggered by editingFinished
    #   - matches HEX_PATTERN → calls set_color()
    #   - on failure → sets border: 1px solid red, reverts text to previous valid color
    # _on_picker(): opens QColorDialog.getColor(), calls set_color() on valid selection
    # set_color(c): updates swatch bg, hex text, emits color_changed
```

### `ColorPanel` — 10 picker rows + Reset

```python
# color_panel.py — lines 78-147

class ColorPanel(QWidget):
    color_changed = pyqtSignal(str, str)  # (role, hex_color)

    # Three sections:
    #   "Base Colors":    TEXT, LIGHT, DARK, LINE, BTN
    #   "Chart Curves":   SPECTRUM, TREND, RESISTANCE
    #   "Chart Display":  GRID, AXIS
    #
    # setFixedWidth(170)
    # Reset button restores all 10 roles to defaults from ColorScheme class attrs
    # (reads settings_manager.DEFAULTS["colors"] at runtime)
```

**Reset defaults** (`color_panel.py` lines 139-143) must match BOTH `ColorScheme` class attrs AND `settings_manager.DEFAULTS`:

```python
defaults = {
    "TEXT":"#c0caf5","LIGHT":"#1e1f2e","DARK":"#1a1b26","LINE":"#3b3d56","BTN":"#3b3d56",
    "SPECTRUM":"#0db9d7","TREND":"#bb9af7","RESISTANCE":"#f7768e",
    "GRID":"#2c2d3f","AXIS":"#565f89",
}
```

**WARNING:** This is a third independent copy of the factory default color values. If you change defaults in `ColorScheme` class attrs or `settings_manager.DEFAULTS` but forget this location, the Reset button silently restores stale wrong colors. This is a known maintenance hazard — see the "To customize the default color palette" extension point for the correct approach.

**Anti-pattern:** Adding a `ColorPickerRow` without adding the corresponding class attribute to `ColorScheme` creates an orphan picker — the `_on_change` handler calls `ColorScheme.set_color()` which will silently fail (return `False`), and no widget consumes the color.

---

## Step 3: `main_window.py` — Host Window

### Window defaults

| Setting | Value | Line |
|---------|-------|------|
| Window title | "OptoSync — Synchronized Acquisition System" | 25 |
| Default size | 1440×920 | 26 |
| Minimum size | 1100×700 | 27 |
| Log panel max lines | 500 (`setMaximumBlockCount`) | 140 |
| Log placeholder | "Log output — demo mode" | 141 |
| Status bar message | "Ready — Demo Mode \| Simulated data" | 285 |

### Layout structure

```
┌──────────┬──┬──────────────────────┬──┬──────────┐
│ param    │◀ │ charts (QSplitter)   │▶ │ color    │
│ panel    │  │ ┌──────────────────┐ │  │ panel    │
│ (300px)  │  │ │ SpectrumChart    │ │  │ (170px)  │
│          │  │ │ TrendChart       │ │  │          │
│          │  │ │ SourceMeterChart │ │  │          │
│          │  │ └──────────────────┘ │  │          │
│          │  │ ▼ log panel (150px) │  │          │
└──────────┴──┴──────────────────────┴──┴──────────┘
```

Toggle buttons are `QPushButton` with `setFixedSize(12, 30)` (line 161), arrow text (`◀`/`▶`/`▼`/`▲`), placed between panels in `QHBoxLayout` content area. Toggle button colors are hardcoded (`color:#606060`, hover `#c0c0c0`) via widget-level `setStyleSheet()` at lines 164-167, bypassing the dynamic theme entirely — widget-level stylesheets have higher cascade priority than `QApplication.setStyleSheet()`.

### Initialization order (exact sequence)

This order is critical — violated ordering causes blank charts, unstyled widgets, or redundant disk writes. The current code has no runtime assertions or guards against reordering — violating this sequence produces silent failures rather than clear errors:

```
1. load_settings()                        → dict with merged defaults + saved values
2. _apply_loaded_colors()                 → ColorScheme.set_color() for all 10 roles
3. _setup_ui()                            → create all widgets (they read ColorScheme during __init__)
   └─ Includes apply_label_positions()    → chart_labels from settings (line 121)
4. _apply_loaded_params()                 → restore spinbox/combo values from settings["params"]
5. _connect_param_signals()               → wire valueChanged → _save (AFTER step 4, avoids redundant first write)
6. QApplication.instance().setStyleSheet(get_stylesheet())  → apply QSS LAST
7. self._charts.refresh_colors()          → after QSS
8. restore panel states                   → settings["panels"] (lines 46-52)
```

Implementation reference: `main_window.py` lines 23-52.

**Note on step 3:** Chart labels are positioned from saved settings during widget construction (`apply_label_positions()` at line 121 inside `_setup_ui()`), NOT after theme/color refresh as might be expected. Label styling set by `DraggableLabel._apply_style()` during position restore uses whatever `ColorScheme` values are current at that moment — in the correct sequence these are already loaded from step 2.

### Color change handler

```python
# main_window.py — lines 256-259

def _on_color_changed(self, role: str, color: str):
    QApplication.instance().setStyleSheet(get_stylesheet())  # re-skin all widgets
    self._charts.refresh_colors()                             # re-color charts
    self._save()                                              # persist to disk
```

### Auto-save (`_save()`)

```python
# main_window.py — lines 261-276

def _save(self):
    self._settings["colors"] = {r: getattr(ColorScheme, r) for r in [
        "TEXT", "LIGHT", "DARK", "LINE", "BTN", "SPECTRUM", "TREND", "RESISTANCE", "GRID", "AXIS"]}
    self._settings["params"] = {
        "integration_ms": self._si.value(),
        "averages": self._sa.value(),
        "monitor_wl": self._sw.value(),
        "source_type": self._mc.currentIndex(),
        "source_value": self._mv.value(),
        "nplc": self._mn.value(),
        "sample_rate": self._sr.value(),
    }
    self._settings.setdefault("panels", {})["left"]  = self._left_panel_visible
    self._settings.setdefault("panels", {})["right"] = self._color_panel_visible
    self._settings.setdefault("panels", {})["log"]   = self._log_panel_visible
    save_settings(self._settings)
```

**Every `_save()` call is a full snapshot** — all 10 colors, all 7 params, all 3 panel booleans, and chart_labels (written by `_save_chart_labels` at line 92 before `_save()` runs at line 93).

> **CRITICAL:** The color role list at lines 262-263 is a **hardcoded literal** — NOT derived from `ROLES_BASE + ROLES_CHART`. Adding a new color role to `ColorScheme` and `ROLES_BASE`/`ROLES_CHART` without updating this list causes the new role to be **silently excluded from persistence** (user colors lost on restart). Conversely, removing a role from `ColorScheme` but leaving it in this list causes an **AttributeError** inside `_save()`, which is connected to every parameter widget's change signal, rendering the UI inoperable on any user interaction. **Fix:** Replace the hardcoded list with `ROLES_BASE + ROLES_CHART` imported from `color_scheme`:
> ```python
> from color_scheme import get_stylesheet, ColorScheme, ROLES_BASE, ROLES_CHART
> # in _save():
> self._settings["colors"] = {r: getattr(ColorScheme, r) for r in ROLES_BASE + ROLES_CHART}
> ```

### Orphan buttons (Start/Stop/Save)

```python
# main_window.py — lines 204-209

for t, o in [("Start", "btn_start"), ("Stop", "btn_stop"), ("Save", "btn_save")]:
    b = QPushButton(t); b.setObjectName(o)
    b.setStyleSheet("padding:6px 10px;")
    bl.addWidget(b)
```

These buttons have `objectName` for QSS targeting but **no `clicked` connections**. They are the natural attachment points for hardware control — wire them to your acquisition controller.

### Keyboard shortcuts

```python
# main_window.py — lines 250-254

def keyPressEvent(self, event: QKeyEvent):
    if event.key() == Qt.Key_F10:
        self.showFullScreen()
    elif event.key() == Qt.Key_Escape:
        self.showNormal()
```

### Chart label save

```python
# main_window.py — lines 82-93

def _save_chart_labels(self, x, y, w, h):
    sender = self.sender()
    if sender is self._charts.spectrum._label        : key = "spectrum"
    elif sender is self._charts.trend._label          : key = "trend"
    elif sender is self._charts.sourcemeter._label    : key = "sourcemeter"
    else: return
    self._settings.setdefault("chart_labels", {})[key] = {"x": x, "y": y, "w": w, "h": h}
    self._save()
```

Connected at lines 124-126: each chart's `_label.pos_changed` → `_save_chart_labels`.

> **WARNING:** This method uses `self.sender()` to identify the source chart, which only works when invoked via a Qt signal emission. If called directly (e.g., `self._save_chart_labels(0,0,80,20)`), `sender()` returns `None`, the entire if/elif chain falls through, and the function silently exits with no save and no error. For extensibility, refactor to accept an explicit chart_key parameter and use `functools.partial` for signal connections:
> ```python
> from functools import partial
> def _save_chart_labels(self, chart_key: str, x, y, w, h):
>     self._settings.setdefault("chart_labels", {})[chart_key] = {"x": x, "y": y, "w": w, "h": h}
>     self._save()
> self._charts.spectrum._label.pos_changed.connect(partial(self._save_chart_labels, "spectrum"))
> ```

### Log panel hook

```python
# main_window.py — lines 287-291

def _append_log(self, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    self._log_panel.appendPlainText(f"{ts} {msg}")
    sb = self._log_panel.verticalScrollBar()
    sb.setValue(sb.maximum())
```

This method exists as an integration hook but is **never called from anywhere in the current codebase**. It auto-scrolls to bottom on every append and uses `%H:%M:%S` timestamp format. Wire it to hardware status events during integration.

---

## Step 4: `plot_widgets.py` — Dynamic Charts

### Performance pattern: separate style from data

```python
# Every chart follows this pattern:
class SomeChart(pg.PlotWidget):
    def __init__(self):
        # Pen/brush created ONCE at init
        self._curve = self.plot([], [], pen=pg.mkPen(ColorScheme.SOME_COLOR, width=2))

    def refresh_color(self):
        # Called ONLY on theme change — re-creates pen/brush/label/grid/axis
        self._curve.setPen(pg.mkPen(ColorScheme.SOME_COLOR, width=2))
        self._label.set_color(ColorScheme.SOME_COLOR)
        self._label._apply_style()
        _apply_grid_axis(self)
        self._apply_axis_font()

    def update_data(self, x, y):
        # Called on timer — ONLY sets data, no style changes
        self._curve.setData(x, y)
```

### Chart class boilerplate vs. domain-specific

All three chart classes share significant duplicated boilerplate that is mixed with domain-specific details:

**Mandatory boilerplate (same in every chart):**
- `_apply_axis_font()` — 6-line method copy-pasted identically into all three classes
- `set_label_pos()` — 2-line method duplicated identically
- `refresh_color()` framework — calls `setPen`, `set_label color`, `_apply_style`, `_apply_grid_axis`, `_apply_axis_font`

**Configurable per chart (domain-specific):**
- Axis labels (`setLabel` calls)
- Pen width (2.0 vs 2.2)
- Color role constant
- DraggableLabel text

**Optional per chart:**
- Fill (`_apply_fill` for SpectrumChart)
- Symbol markers (`symbol="o"`, `symbolSize=3` for TrendChart)
- Connect mode (`connect="finite"` for SourceMeterChart)
- X-link topology (`setXLink`)

For a clean template, extract a `_BaseChart(pg.PlotWidget)` superclass that handles all mandatory boilerplate. Each concrete chart then only defines ~15 lines of domain-specific code plus optional overrides.

### `DraggableLabel` — style mechanics

```python
# plot_widgets.py — lines 37-127

class DraggableLabel(QLabel):
    pos_changed = pyqtSignal(int, int, int, int)  # (x, y, w, h) on release

    # Background: RGBA from ColorScheme.LIGHT
    #   r = int(LIGHT[1:3], 16), g = int(LIGHT[3:5], 16), b = int(LIGHT[5:7], 16)
    #   alpha = int(ColorScheme.LABEL_ALPHA, 16)  → "ff" becomes 255
    # Border: 1px solid ColorScheme.LINE
    # Text color: the curve's color (self._color)
    # Font size: max(8, int(height * 0.72))

    # Zones:
    #   Bottom-right 20×20: resize (min 40×20)
    #   Everywhere else:    drag to move
```

The stylesheet construction is at lines 58-80 — note the `rgba()` string formatting that parses `ColorScheme.LIGHT` characters directly.

### `_apply_pg_theme()` and `_apply_grid_axis()`

```python
# plot_widgets.py — lines 14-34

def _apply_pg_theme():
    """Must be called explicitly, NOT at module level."""
    pg.setConfigOption("background", ColorScheme.DARK)
    pg.setConfigOption("foreground", ColorScheme.TEXT)
    pg.setConfigOption("antialias", False)
    pg.setConfigOptions(useOpenGL=False, leftButtonPan=False)

def _apply_grid_axis(chart):
    pg.setConfigOption("foreground", ColorScheme.GRID)
    chart.showGrid(x=True, y=True, alpha=0.4)
    pg.setConfigOption("foreground", ColorScheme.TEXT)  # restore

    pen = pg.mkPen(ColorScheme.AXIS, width=1)
    for name in ("left", "bottom"):
        ax = chart.getAxis(name)
        ax.setPen(pen)
        ax.setTextPen(pen)
    chart._apply_axis_font()
```

Note: `_apply_pg_theme()` calls `pg.setConfigOptions(useOpenGL=False, leftButtonPan=False)` (line 18). OpenGL is disabled; left-button panning is disabled (only right-click pans). Neither doc previously mentioned these pg configuration options — they affect how users interact with charts.

### Chart classes

| Chart | X label | Y label | Curve mode | Buffer | X link | Throttle |
|-------|---------|---------|------------|--------|--------|----------|
| `SpectrumChart` (line 129) | "Wavelength (nm)" | "Intensity" | default | full data | — | every 5th tick |
| `TrendChart` (line 173) | "Time (s)" | "Intensity" | default, symbol="o" | 1000 pts | linked to SourceMeter | none |
| `SourceMeterChart` (line 216) | "Time (s)" | "Resistance (Ω)" | **connect="finite"** | 1000 pts | **drives shared X** | none |

- `TrendChart` bottom axis is hidden (`self.trend.hideAxis("bottom")` at line 310) because `SourceMeterChart` drives the shared time axis via `setXLink`.
- Only `SourceMeterChart` uses `connect="finite"` (line 228) — `float("nan")` values create visual breaks when current is zero. `TrendChart` uses default line mode (no `connect` parameter, lines 183-187).
- 60-second rolling X window: `self.sourcemeter.setXRange(max(0, last_time - 60), last_time + 5)` (line 385).

**Chart topology (critical for adding/removing charts):**

The three charts form an X-linked chain where `SourceMeterChart` is the X-axis master:

```
TrendChart ── setXLink ──→ SourceMeterChart (X-axis master)
  ↑                            ↑
  │ bottom axis hidden         │ setXRange() drives shared auto-scroll
  └────────────────────────────┘
```

Both `TrendChart` and `SourceMeterChart` are in the same `QSplitter` stack. If you remove `SourceMeterChart` (reducing from 3 to 2 charts), you must:
1. Remove `setXLink` and `hideAxis("bottom")` from TrendChart
2. Move the `setXRange()` auto-scroll call to TrendChart itself (replace `self.sourcemeter.setXRange(...)` with `self.trend.setXRange(...)`)
3. Remove `SourceMeterChart` from the splitter and all 4 label-key locations (see "To add a new chart" extension point)
4. The `_tick()` method's three separate blocks also need pruning

If adding a 4th chart with its own X-axis, decide whether it links to the existing X-axis master or drives independently.

### `DataSimulator` — THE PLACEHOLDER

```python
# plot_widgets.py — lines 256-287

class DataSimulator:
    @staticmethod
    def spectrum(wavelengths=None) -> (list, list):
        # 1400 wavelength bins (300-1000nm, step 0.5nm)
        # 3 Gaussian peaks:
        #   - 450nm, sigma=30, amplitude=800
        #   - 550nm, sigma=25, amplitude=500
        #   - 680nm, sigma=20, amplitude=300
        # noise: gauss(0, 15), clipped to >= 0

    @staticmethod
    def trend(n_points) -> (list, list):
        # Signal: 500 + 200*sin(t*0.5)*exp(-t*0.01)
        # noise: gauss(0, 10), n_points

    @staticmethod
    def sourcemeter(n_points) -> (list, list):
        # V(t) = 5.0 + 0.1*sin(t*2)
        # I(t) = 0.003 + 0.0002*cos(t*3)
        # R = V/I, NaN when I=0, n_points
```

**Replace** the 3 static methods with a QObject-based hardware driver that emits typed signals (one per chart). The `ChartPanel._tick()` timer loop (lines 363-396) drives polling at 500ms — for signal-driven acquisition, replace the timer with a worker thread signal connected to per-chart `update_*` methods.

**Concrete integration pattern for real hardware (QThread-based SensorWorker):**

```python
# plot_widgets.py — replace DataSimulator + ChartPanel._tick() QTimer

from PyQt5.QtCore import QObject, pyqtSignal, QThread

class SensorWorker(QObject):
    """Hardware sensor reader — runs in a dedicated QThread.
    Replaces DataSimulator static methods + ChartPanel._tick() QTimer.
    Emits three typed signals, one per chart.
    """
    spectrum_ready = pyqtSignal(list, list)       # (wavelengths, intensities)
    trend_ready = pyqtSignal(list, list)          # (times, values)
    sourcemeter_ready = pyqtSignal(list, list)    # (times, resistance)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    SPECTRUM_THROTTLE = 5  # emit spectrum every Nth tick

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._tick_count = 0
        self._wl_cache = None

    @pyqtSlot()
    def start_acquisition(self):
        self._running = True
        self._tick_count = 0
        self._wl_cache = None
        self.status_changed.emit("acquisition started")
        while self._running:
            try:
                self._tick_count += 1
                if self._tick_count <= 1 or self._tick_count % self.SPECTRUM_THROTTLE == 0:
                    wl, intensities = self._read_spectrometer()
                    if self._wl_cache is None:
                        self._wl_cache = wl
                    self.spectrum_ready.emit(self._wl_cache, intensities)
                times, values = self._read_trend(2)
                self.trend_ready.emit(times, values)
                times, resistance = self._read_sourcemeter(2)
                self.sourcemeter_ready.emit(times, resistance)
            except Exception as exc:
                self.error_occurred.emit(str(exc))
            QThread.msleep(500)

    @pyqtSlot()
    def stop_acquisition(self):
        self._running = False

    # ---------- hardware stubs (replace with real driver calls) ----------
    def _read_spectrometer(self):
        return DataSimulator.spectrum(self._wl_cache)

    def _read_trend(self, n_points):
        return DataSimulator.trend(n_points)

    def _read_sourcemeter(self, n_points):
        return DataSimulator.sourcemeter(n_points)
```

**ChartPanel integration (what to change):**

```python
# REMOVE from ChartPanel.__init__():
#   self._timer = QTimer(self)
#   self._timer.timeout.connect(self._tick)
#   self._timer.start(500)

# ADD worker thread setup:
self._worker_thread = QThread(self)
self._sensor = SensorWorker()
self._sensor.moveToThread(self._worker_thread)
self._sensor.spectrum_ready.connect(self.spectrum.update_spectrum)
self._sensor.trend_ready.connect(self._on_trend_data)
self._sensor.sourcemeter_ready.connect(self._on_sourcemeter_data)
self._worker_thread.started.connect(self._sensor.start_acquisition)

# ADD dispatch methods (buffer management stays in ChartPanel):
def _on_trend_data(self, times, values):
    for t, v in zip(times, values):
        self._times.append(t)
        self._trend_vals.append(v)
    if len(self._times) > self.trend.MAX_POINTS:
        cut = len(self._times) - self.trend.MAX_POINTS
        self._times = self._times[cut:]
        self._trend_vals = self._trend_vals[cut:]
    self.trend.update_data(self._times, self._trend_vals)
    if self._times:
        self.sourcemeter.setXRange(max(0, self._times[-1] - 60), self._times[-1] + 5)
```

**Key design notes:**
- **Push replaces poll:** QTimer removed; worker drives via `QThread.msleep(500)` in a while-loop
- **Spectrum throttling preserved:** `SPECTRUM_THROTTLE = 5` constant and `_tick_count` counter
- **Thread safety:** pyqtgraph methods (`setData`, `setXRange`, `autoRange`) are called from the GUI thread automatically via signal-slot delivery with `moveToThread`
- **Graceful shutdown:** `stop_acquisition()` sets `_running=False`, while-loop exits, then `quit()` + `wait()` clean up the QThread
- **Buffer management stays in ChartPanel:** worker emits raw points; ChartPanel handles MAX_POINTS truncation and X-axis range
- **`_data_counter` is removed:** time tracking moves to worker's `_tick_count`

### `ChartPanel` — container

```python
# plot_widgets.py — lines 290-405

class ChartPanel(QWidget):
    # Vertical QSplitter with 3 charts
    # QTimer at 500ms → _tick() (line 322)
    # showEvent → one-shot _align_y_axes() via QTimer.singleShot(0, ...) (lines 324-328)
    #   Deferred-execution rationale: axis widths are not available until Qt
    #   paints the widget, so singleShot(0) schedules alignment after the first
    #   event-loop cycle completes.
    # apply_label_positions(positions: dict) — restores {x,y,w,h} per chart (lines 342-361)
```

**Spectrum throttling rationale** (line 368):

The spectrum chart is throttled to every 5th tick (`self._data_counter <= 1 or self._data_counter % 5 == 0`) because `DataSimulator.spectrum()` generates 1400 wavelength points per update (range 300-1000nm at 0.5nm steps). Scrolling charts (Trend, SourceMeter) add only 2 points each. A full 1400-point spectrum redraw every 500ms would saturate the Qt event loop. **Decision rule for new charts:** throttle if per-update point count exceeds ~500; otherwise update on every tick. The `<= 1` condition ensures the first tick always renders immediately (no blank chart on startup).

**Known limitation — QSplitter not persisted:**

The `QSplitter` holding the three charts at line 299 is a local variable (`splitter = pg.QtWidgets.QSplitter(...)`), not stored as an instance attribute. There is no save/restore logic for splitter handle positions. Chart splitter positions are lost across restarts — users must re-drag handles each session. To fix, assign to `self._chart_splitter` and add get/set methods for `sizes()`.

---

## Settings Persistence — Complete Schema

### `DEFAULTS` dict (`settings_manager.py` lines 28-55)

```json
{
  "colors": {
    "TEXT":        "#c0caf5",
    "LIGHT":       "#1e1f2e",
    "DARK":        "#1a1b26",
    "LINE":        "#3b3d56",
    "BTN":         "#3b3d56",
    "SPECTRUM":    "#0db9d7",
    "TREND":       "#bb9af7",
    "RESISTANCE":  "#f7768e",
    "GRID":        "#2c2d3f",
    "AXIS":        "#565f89"
  },
  "params": {
    "integration_ms": 10.0,
    "averages":        2,
    "monitor_wl":    632.0,
    "source_type":      0,
    "source_value":   0.003,
    "nplc":            1.0,
    "sample_rate":     5.0
  },
  "chart_labels": {
    "spectrum":    {"x": 8, "y": 8, "w":  80, "h": 24},
    "trend":       {"x": 8, "y": 8, "w": 110, "h": 24},
    "sourcemeter": {"x": 8, "y": 8, "w": 100, "h": 24}
  }
}
```

### Runtime-only key (not in DEFAULTS, added by `setdefault`)

```json
"panels": {
  "left":  true,
  "right": true,
  "log":   true
}
```

### Merge logic (`load_settings()` — lines 58-75)

1. If `settings.json` does not exist → return `DEFAULTS` verbatim (**warning: returns the module-level constant by reference, not a copy — see "Known issue" below**)
2. Parse JSON from disk
3. Shallow-copy `DEFAULTS` into `merged`
4. Top-level `merged.update(data)` (preserves unknown keys)
5. Per-sub-dict shallow merge: `merged["colors"] = {**DEFAULTS["colors"], **data["colors"]}` (same for `params`, `chart_labels`)
6. On `JSONDecodeError` or `IOError` → return `DEFAULTS` (**silently — no logging, no warning, no user notification**)

This is an additive/forgiving merge: new keys added to DEFAULTS in a future version appear automatically; keys removed from DEFAULTS but present in the JSON file persist in memory (a potential memory leak of stale configuration — typos like `"LIGHTT"` accumulate permanently with no purge mechanism).

**Known issues:**

1. **Return-by-reference on file-not-found:** `load_settings()` returns the module-level `DEFAULTS` dict directly (not a copy) when `settings.json` is missing. If the caller mutates the returned dict (e.g., `_save()` does `self._settings["colors"] = {...}`), the global `DEFAULTS` constant is permanently corrupted. Subsequent `load_settings()` calls return the user's last-saved colors instead of factory defaults. **This is the root cause of the `_reset()` button restoring user colors instead of factory defaults on first run.** Fix: return `DEFAULTS.copy()` instead of `DEFAULTS`.

2. **Silent JSON error suppression:** On `JSONDecodeError` or `IOError`, the function returns `DEFAULTS` with zero logging or user notification. A manually edited `settings.json` with a trailing comma is silently discarded. Worse, the auto-save chain (`_save()` → `save_settings()`) immediately **overwrites** the corrupt file with default-based state, permanently destroying all salvageable data. **Diagnostic:** if the app starts with factory defaults after editing settings.json, check for JSON syntax errors with `python -m json.tool settings.json`.

3. **Keys removed from DEFAULTS persist forever:** Due to the additive merge logic (step 5 uses `{**DEFAULTS, **data}`), any key present in the user's `settings.json` that was subsequently removed from `DEFAULTS` (e.g., a renamed or deleted color role) is preserved in memory and written back to disk on every save. There is no cleanup mechanism. Review `settings.json` periodically for stale entries.

### File path resolution (`_get_settings_dir()` — lines 8-23)

- **Development** (`sys.frozen` is False): `os.path.dirname(__file__)` → project directory
- **Frozen/PyInstaller** (`sys.frozen` is True): `os.path.dirname(sys.executable)` → directory containing the `.exe`

**Critical:** Use `sys.executable`, NOT `sys._MEIPASS`. `_MEIPASS` is a temporary extraction directory that is read-only and deleted on exit. It is only suitable for locating bundled resource files (icons, images), never for writing data.

**Note:** `SETTINGS_FILE` is resolved at module import time (line 26), not at save/load call time. If the working directory or `sys.executable` changes after import, the path is stale.

### Save triggers (all call `MainWindow._save()`)

| Trigger | Source | Line |
|---------|--------|------|
| Color changed | `_on_color_changed` | 259 |
| Param widget changed | `_connect_param_signals` (7 widgets) | 74-80 |
| Panel toggled | `_toggle_left/right/log_panel` | 224,236,248 |
| Label drag/release | `_save_chart_labels` | 93 |
| Window close | `closeEvent` | 279 |

Every trigger writes a **full snapshot** of all colors, params, panels, and chart_labels.

---

## Critical Gotchas

### 1. QSS must target QApplication, not QMainWindow

```python
# WRONG — only affects MainWindow subtree, misses some widgets:
self.setStyleSheet(get_stylesheet())

# CORRECT — applies to every widget globally:
QApplication.instance().setStyleSheet(get_stylesheet())
```

### 2. QSS must be applied LAST

Build the entire widget tree first, restore params, connect signals, THEN apply QSS. Any `setStyleSheet()` call on an individual widget after the global QSS will be overridden. See initialization order in Step 3.

**Also:** Toggle buttons (`_left_toggle`, `_right_toggle`, `_log_toggle`) use widget-level `setStyleSheet()` calls (main_window.py lines 164-167) which have higher cascade priority than `QApplication.setStyleSheet()`. Changing any `ColorScheme` color has zero effect on these three buttons — they are deliberately independent of the theme.

### 3. Do NOT call pyqtgraph theme at module import time

```python
# WRONG — runs at import time with default colors, before settings loaded:
_apply_pg_theme()  # module-level call

# CORRECT — define function, call explicitly after colors loaded:
def refresh_colors(self):
    _apply_pg_theme()
    # then per-chart refresh_color()
```

`_apply_pg_theme()` is defined at `plot_widgets.py` line 14 but only called from `ChartPanel.refresh_colors()` (line 399).

### 4. Re-apply fill after `setData()` for SpectrumChart

pyqtgraph's `setData()` can reset the fill brush. For `SpectrumChart`, re-apply fill after every `setData()`:

```python
# plot_widgets.py lines 167-170
def update_spectrum(self, wl, spec):
    self._curve.setData(wl, spec)
    self._apply_fill()   # MUST re-apply after setData (fill brush can be reset)
    self.autoRange()
```

Pen does **not** need re-application — it persists across `setData()` calls once set. `TrendChart` and `SourceMeterChart` re-apply neither fill nor pen after `setData()` (they have no fill and pen persistence is sufficient).

### 5. `enableAutoRange()` + explicit `autoRange()` for reliability

`enableAutoRange()` alone can fail if the chart was initialized with empty data. Always call `autoRange()` on the first real data frame (or every frame for safety):

```python
# All three charts call enableAutoRange() in __init__
# SpectrumChart calls autoRange() in update_spectrum() (line 170)
# TrendChart and SourceMeterChart rely on enableAutoRange() + linked X range (line 385)
```

### 6. Initialization order matters

See the 8-step numbered list in Step 3. The sequence `load → apply colors → create widgets (incl. labels) → apply params → connect signals → QSS → refresh charts → panels` is non-negotiable. Violating it causes:
- Widgets constructed before colors loaded: stale defaults
- Signals connected before params restored: redundant save on startup
- QSS applied before widget tree complete: unstyled widgets
- `refresh_colors()` before QSS: chart bg/fg mismatch

There are no runtime assertions or guards enforcing this order — violations produce silent failures rather than clear errors.

### 7. Frozen exe path: `sys.executable`, not `sys._MEIPASS`

```python
# settings_manager.py lines 8-23
def _get_settings_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)  # persistent, writable
    return os.path.dirname(__file__)
```

`sys._MEIPASS` is the temp extraction directory — read-only and deleted on exit. Use only for locating bundled resource files.

### 8. BTN default is identical to LINE

`BTN` defaults to `#3b3d56`, which is the same as `LINE`. Changing `LINE` does NOT auto-update `BTN` — the user must change both separately. This coupling through the default value is invisible in the UI: both pickers initially show `#3b3d56`. To keep button borders matching other borders, update both `LINE` and `BTN` together.

### 9. `sample_rate` parameter is not wired to the timer

The `sample_rate` param in `DEFAULTS["params"]` (settings_manager.py line 48) is stored and restored across sessions but never used at runtime to change the `QTimer` interval (fixed at 500ms in ChartPanel line 322). It exists as a user-facing reference parameter for hardware configuration, not a runtime control. If you want dynamic rate control, wire it to `ChartPanel._timer.setInterval(sample_rate * 1000)`.

### 10. `refresh_colors()` sets per-chart backgrounds redundantly

At `plot_widgets.py` lines 400-402, `refresh_colors()` explicitly calls `ch.setBackground(ColorScheme.DARK)` on each chart after `_apply_pg_theme()` already sets the global background. This is redundant under normal operation but acts as a safety net if individual charts were styled separately.

---

## Extension Points

### To add a new color role

1. Add class attr to `ColorScheme` (e.g., `NEW_COLOR = "#xxxxxx"`)
2. Add to `ROLES_BASE` or `ROLES_CHART` list (color_scheme.py lines 11-12)
3. Add `ColorPickerRow` to the appropriate section in `ColorPanel._init_ui()` (color_panel.py lines 98-126) with a label
4. Add to `settings_manager.DEFAULTS["colors"]` (line 29-40)
5. Add to `ColorPanel._reset()` defaults (lines 139-143)
6. Consume in `get_stylesheet()` OR `refresh_color()`/`_apply_pg_theme()`/`_apply_grid_axis()`
7. **CRITICAL:** Add the new role name to the hardcoded list in `MainWindow._save()` (main_window.py line 262-263) — this list is NOT derived from `ROLES_BASE + ROLES_CHART` at runtime. Missing this step causes silent data loss (new role colors not persisted across restarts).

### To replace DataSimulator with real hardware

1. Replace the 3 static methods in `plot_widgets.py` (lines 256-287) with a QObject-based worker that emits typed signals (see the `SensorWorker` pattern in Step 4 above — complete code template with signal signatures, thread setup, and ChartPanel integration)
2. Connect the worker signals to dispatch methods in `ChartPanel` that handle buffer management (MAX_POINTS truncation) and X-axis range
3. Remove the `QTimer(500ms)` in `ChartPanel.__init__()` (line 322) — replace with `QThread + moveToThread` push model
4. Wire Start/Stop buttons (main_window.py lines 205-208) to `worker.start_acquisition()` / `worker.stop_acquisition()`
5. Wire `MainWindow._append_log(msg)` (line 287) to hardware status events (`SensorWorker.status_changed` / `error_occurred`)

**If replacing the spectrometer with a temperature sensor:** Create a new data generator that emits realistic temperature signals (ambient ~25C with random walk drift of ~0.01C/s and gauss noise ~0.05C). For pressure: typical range 0-100 kPa with slow drift and high-frequency noise. See the DataSimulator section in Step 4 for the exact signal formulas to replace.

### To add a new chart

1. Subclass `pg.PlotWidget` following `SpectrumChart` pattern: pen at init, `refresh_color()`, `update_data()`. See chart class boilerplate breakdown in Step 4 for mandatory vs. configurable vs. optional code sections.
2. Add corresponding color role + picker row + DEFAULTS entry (see above)
3. Add to `ChartPanel` splitter (line 299-306), link X axes if needed, add `DraggableLabel`
   - **3a.** Add the new chart's key to `ChartPanel.apply_label_positions()` (currently checks for "spectrum", "trend", "sourcemeter" at lines 344-361 of `plot_widgets.py`) so saved label positions are restored on startup
4. Add `chart_labels` default position to `settings_manager.DEFAULTS["chart_labels"]`
5. Connect label `pos_changed` → `MainWindow._save_chart_labels` (extend sender-identity check at line 84-91). **WARNING:** `_save_chart_labels` uses `self.sender()` which only works from signal invocations, not direct calls. See Step 3 chart label save section for the refactored `functools.partial` pattern.
6. Extend `MainWindow._save_chart_labels` with new sender check

> **When adding/removing charts:** The chart-label keys ("spectrum", "trend", "sourcemeter") are hardcoded in **4 separate locations** across 3 files:
> - `settings_manager.py` DEFAULTS `chart_labels` (lines 50-54)
> - `plot_widgets.py` `ChartPanel.apply_label_positions()` (lines 344-361)
> - `main_window.py` `_save_chart_labels()` (lines 84-89)
> - `main_window.py` signal connections (lines 124-126)
>
> All 4 locations must be updated together. Missing any one causes saved label positions to silently fail to restore on startup (no error, just the label snaps back to default position). See the chart topology diagram in Step 4 for X-linking dependencies.

### To change parameter widgets

> **WARNING:** Parameter widgets are tightly coupled across **5 separate code locations**. Changing the parameter panel requires simultaneous edits to all 5 — missing any one causes silent data loss (parameter values lost across restarts with no crash or error):

| Widget | `_build_param_panel()` | `DEFAULTS["params"]` | `_apply_loaded_params()` | `_connect_param_signals()` | `_save()` |
|--------|------------------------|---------------------|--------------------------|---------------------------|-----------|
| `self._si` | line 180 | `"integration_ms"` line 42 | line 60 | line 74 | line 265 |
| `self._sa` | line 181 | `"averages"` line 43 | line 61 | line 75 | line 266 |
| `self._sw` | line 182 | `"monitor_wl"` line 44 | line 62 | line 76 | line 267 |
| `self._mc` | line 190 | `"source_type"` line 45 | line 63 | line 77 | line 268 |
| `self._mv` | line 191 | `"source_value"` line 46 | line 64 | line 78 | line 269 |
| `self._mn` | line 192 | `"nplc"` line 47 | line 65 | line 79 | line 270 |
| `self._sr` | line 200 | `"sample_rate"` line 48 | line 66 | line 80 | line 271 |

Procedure:
1. Add/remove widgets in `_build_param_panel()` (main_window.py lines 170-212)
2. Update `DEFAULTS["params"]` with new keys (settings_manager.py lines 41-49)
3. Update `_apply_loaded_params()` to read/write new keys (main_window.py lines 58-66)
4. Update `_connect_param_signals()` to wire new widgets to `_save` (lines 68-80)
5. Update `_save()` to serialize new widget values (lines 264-272)

### Parameter Panel Design Principles

When adapting the parameter panel to a new sensor domain (temperature, pressure, humidity, etc.):

**Widget type selection:**

| Parameter semantics | Recommended widget | Example |
|---------------------|--------------------|--------|
| Continuous physical quantity with known operating range | `QDoubleSpinBox` with suffix units | `self._temp = QDoubleSpinBox(); self._temp.setSuffix(" °C")` |
| Integer count / iterations | `QSpinBox` | `self._scans = QSpinBox(); self._scans.setRange(1, 1000)` |
| Discrete modes with exactly N options | `QComboBox` | `self._unit = QComboBox(); self._unit.addItems(["Celsius", "Fahrenheit", "Kelvin"])` |
| Boolean on/off | `QCheckBox` | `self._enable_alarm = QCheckBox("Enable Alarm")` |
| Coarse visual adjustment | `QSlider` + companion `QLabel` | Not currently used in this template |

**Range and default heuristics:**
- Derive ranges from datasheet limits (operating range / absolute max ratings), adding a 5-10% safety margin
- Pick defaults that represent a safe idle state — not zero, not max
- Add suffix units so the UI self-documents (`°C`, `bar`, `%RH`, `kPa`)
- Group related parameters under separate `QGroupBox` labels (e.g., "Temperature", "Pressure", "Alarms")

**Worked example — generic sensor monitoring app:**

```python
# settings_manager.py — DEFAULTS["params"] for temperature + pressure
"params": {
    "temp_sample_rate": 1.0,       # Hz
    "temp_alarm_high": 80.0,       # °C
    "temp_alarm_low": -10.0,       # °C
    "pressure_unit": 0,            # combo index: 0=bar, 1=psi, 2=kPa
    "pressure_range_max": 10.0,    # bar
    "log_interval": 5.0,           # seconds between log writes
},

# main_window.py — _build_param_panel() excerpt
tg = QGroupBox("Temperature")
tf = QFormLayout(tg)
self._temp_rate = QDoubleSpinBox(); self._temp_rate.setRange(0.1, 100)
self._temp_rate.setSuffix(" Hz")
tf.addRow("Sample Rate:", self._temp_rate)
self._temp_high = QDoubleSpinBox(); self._temp_high.setRange(-50, 500)
self._temp_high.setSuffix(" °C")
tf.addRow("Alarm High:", self._temp_high)
# ... etc.
```

The five update points (build_panel, DEFAULTS, apply_loaded_params, connect_signals, _save) remain the same mechanical pattern — only the widget types, ranges, and semantics change.

### To customize the default color palette

Edit only **TWO places** (not three — the Reset button should read from `DEFAULTS["colors"]` at runtime):

1. `ColorScheme` class attributes (color_scheme.py lines 19-37)
2. `settings_manager.DEFAULTS["colors"]` (lines 29-40)

**For the Reset button:** Refactor `ColorPanel._reset()` to read from `settings_manager.DEFAULTS["colors"]` at runtime instead of maintaining a third independent copy of the defaults. Currently, `_reset()` hardcodes a third copy at color_panel.py lines 139-143. If DEFAULTS and ColorScheme attrs are updated but this third copy is forgotten, the Reset button silently restores stale wrong colors. The simplest fix:

```python
def _reset(self):
    from settings_manager import DEFAULTS
    for r, c in DEFAULTS["colors"].items():
        ColorScheme.set_color(r, c)
        self._pickers[r].set_color(c)
        self.color_changed.emit(r, c)
```

**Note:** This requires fixing `load_settings()` to return `DEFAULTS.copy()` instead of `DEFAULTS` by reference (see Settings Persistence — Known Issues #1). Otherwise, `DEFAULTS["colors"]` gets silently overwritten with user colors on first save, and the Reset button restores user colors instead of factory defaults.

---

## Integration Checklist — Starting a New Project

1. Copy all 5 `.py` files to new project directory
2. Delete any existing `settings.json` (it auto-generates with defaults)
3. In `color_scheme.py`: rename/recolor `SPECTRUM`, `TREND`, `RESISTANCE` to your domain. Update `ROLES_CHART` list. Add/remove chart color roles as needed
4. In `color_panel.py`: update role-label pairs in `_init_ui()` (lines 98-126) and defaults in `_reset()` (lines 139-143)
5. In `settings_manager.py`: update `DEFAULTS["colors"]` and `DEFAULTS["params"]` to match your hardware. Consult the Parameter Panel Design Principles section for widget type and range guidance.
6. In `plot_widgets.py`: replace `DataSimulator` with your signal source. Update axis labels, `DraggableLabel` text, curve counts, and `apply_label_positions` keys. Consult the chart topology section in Step 4 before adding or removing charts.
7. In `main_window.py`: update window title (line 25), status bar message (line 285), log panel placeholder text (line 141), parameter GroupBox labels/ranges, toggle button tooltips. Wire Start/Stop/Save buttons to your hardware controller
8. Apply your own default color palette (edit the two locations from "To customize the default color palette" above)
9. Run the conformance check (from Design Philosophy section)
10. Test: change a color → verify QSS updates globally. Change a parameter → verify `settings.json` appears. Restart → verify all settings restored
11. Delete `settings.json` → restart → verify defaults reappear from `DEFAULTS` dict

---

## Performance Checklist

- [ ] `QApplication.instance().setStyleSheet()` called only on color change (not on timer)
- [ ] `pg.mkPen()` / `pg.mkBrush()` only in `refresh_color()` (not in `update_data()`)
- [ ] `enableAutoRange()` on all charts (not `disableAutoRange()`)
- [ ] Max data points <= 1500 (current: 1400 spectrum, 1000 trend, 1000 sourcemeter)
- [ ] Timer interval >= 400ms (current: 500ms)
- [ ] Only 2 data points added per tick for scrolling charts
- [ ] Antialias off (`pg.setConfigOption("antialias", False)` — line 17)
- [ ] Spectrum throttled to every 5th tick (line 368). **Rationale:** Spectrum generates 1400 points per update vs. 2 for scrolling charts. Throttle any chart whose per-update point count exceeds ~500.
- [ ] Spectrum first frame renders immediately (`_data_counter <= 1` condition at line 368)
