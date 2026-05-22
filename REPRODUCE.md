# Reproduce: Dynamic 4-Color Theme System for PyQt5

## Overview

A **user-customizable color theme system** for PyQt5 applications. The entire UI palette is derived from **4 base colors**:
- **TEXT** — primary text / foreground color
- **LIGHT** — panel / card / surface backgrounds
- **DARK** — main window / chart plot backgrounds
- **LINE** — borders / splitters / separators

Each color is independently adjustable via **HEX input** or **system color picker**. All QSS stylesheets and chart pen/brush objects update in real-time as the user changes colors.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              color_scheme.py                 │  ← single source of truth
│  ColorScheme class (4 base + chart colors)  │
│  get_stylesheet() → full QSS string         │
│  hex_to_rgba() → color math helper          │
└──────────────┬──────────────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
┌─────────┐ ┌──────┐ ┌──────────┐
│main_win │ │color │ │plot_wid  │
│dow.py   │ │panel │ │gets.py   │
│         │ │.py   │ │          │
│QSS ←─── │ │UI for│ │chart     │
│ColorSch │ │each  │ │pen/brush │
│eme      │ │color │ │← ColorSch│
└─────────┘ └──┬───┘ └──────────┘
               │
        color_changed signal
        (str role, str hex)
```

## File Structure

```
project/
├── color_scheme.py    # Color state + QSS generator (NO PyQt imports)
├── color_panel.py     # Compact color picker UI widget
├── main_window.py     # Host window with toggle button
├── plot_widgets.py    # pyqtgraph charts consuming dynamic colors
└── main.py            # Entry point
```

## Step-by-Step Integration

### Step 1 — `color_scheme.py` (Color Model)

This is the **single source of truth** for all colors. It has NO PyQt dependency — pure Python.

```python
class ColorScheme:
    # 4 user-customizable base colors
    TEXT  = "#c0caf5"
    LIGHT = "#1e1f2e"
    DARK  = "#1a1b26"
    LINE  = "#3b3d56"

    # Additional fixed/chart colors (also user-settable)
    SPECTRUM = "#0db9d7"
    TREND    = "#bb9af7"
    RESISTANCE = "#f7768e"
    GREEN  = "#9ece6a"
    RED    = "#f7768e"

    @classmethod
    def set_color(cls, role: str, hex_color: str) -> bool:
        """Set a color role. Returns True on success."""
        if not HEX_PATTERN.match(hex_color):
            return False
        if hasattr(cls, role.upper()):
            setattr(cls, role.upper(), hex_color.upper())
            return True
        return False
```

**Key design decision**: All colors are class-level strings (`str`) so they work in f-strings directly (e.g., `f"color: {ColorScheme.TEXT};"`). The `get_stylesheet()` function reads these values and returns a complete QSS string.

```python
# In get_stylesheet():
text  = ColorScheme.TEXT
light = ColorScheme.LIGHT
dark  = ColorScheme.DARK
line  = ColorScheme.LINE

return f"""
QWidget {{
    background-color: {dark};
    color: {text};
}}
QGroupBox {{
    background-color: {light};
    border: 1px solid {line};
}}
"""
```

**Derived colors** are computed from the 4 base colors using `_adjust_brightness()`:

```python
def _adjust(hex_color: str, amount: int) -> str:
    """Lighten (+) or darken (-) a hex color by amount."""
    # parse R, G, B → clamp to 0-255 → return new hex
```

### Step 2 — `color_panel.py` (Color Picker UI)

A compact `QWidget` containing one row per color:

```python
class ColorPickerRow(QWidget):
    color_changed = pyqtSignal(str)  # emits new hex value

    # Layout: [swatch] [label] [HEX input] [🎨 picker button]
    # - swatch: 10x10 QFrame with background-color
    # - hex_input: QLineEdit, 64px wide, Consolas font
    # - picker button: opens QColorDialog.getColor()
    #
    # _on_hex(): validates via editingFinished, reverts on bad input
    # _on_picker(): opens system dialog, calls set_color() on valid
    # set_color(): updates swatch + hex + emits color_changed signal
```

```python
class ColorPanel(QWidget):
    color_changed = pyqtSignal(str, str)  # (role, hex_color)

    # Layout:
    # ┌─ Base Colors ──────────┐
    # │ [■] Text    [#c0caf5] [🎨] │
    # │ [■] Light   [#1e1f2e] [🎨] │
    # │ [■] Dark    [#1a1b26] [🎨] │
    # │ [■] Line    [#3b3d56] [🎨] │
    # ├─ Chart Curves ─────────┤
    # │ [■] Spectrum [#0db9d7] [🎨] │
    # │ [■] Trend    [#bb9af7] [🎨] │
    # │ [■] R         [#f7768e] [🎨] │
    # ├────────────────────────┤
    # │      [↺ Reset]         │
    # └────────────────────────┘
    #
    # setFixedWidth(170) recommended for compact layout
```

### Step 3 — `main_window.py` (Host Window)

**Layout structure** (QHBoxLayout, no QSplitter for color area):

```
┌──────────┬─────────────────┬┬──────────┐
│ param    │ charts + log    │▶│ color    │
│ panel    │ (stretch=1)    │ │ panel    │
│ (300px)  │                 │ │ (170px)  │
└──────────┴─────────────────┴┴──────────┘
```

**Toggle button**: 12×20px QPushButton placed between charts and color panel in its own wrapper widget. Shows `▶` when panel visible, `◀` when hidden.

```python
def _on_color_changed(self, role, color):
    # 1. Refresh QSS (entire widget tree)
    self.setStyleSheet(get_stylesheet())
    # 2. Refresh chart pens/brushes
    self._charts.refresh_colors()
```

**Critical**: Changing `setStyleSheet()` on QApplication or QMainWindow resets ALL widget styles. Any `setStyleSheet()` calls on individual widgets will be overridden. So the QSS stylesheet must cover ALL widget types.

### Step 4 — `plot_widgets.py` (Dynamic Chart Colors)

**Performance-critical pattern — separate style from data**:

```python
class SpectrumChart(pg.PlotWidget):
    def __init__(self):
        # Create curve with pen ONCE at init
        self._curve = self.plot([], [], pen=pg.mkPen(ColorScheme.SPECTRUM, width=2.2))
        self._apply_fill()  # set fill brush once

    def refresh_color(self):
        """Called only when colors change (NOT on every data update)"""
        self._curve.setPen(pg.mkPen(ColorScheme.SPECTRUM, width=2.2))
        self._apply_fill()

    def update_spectrum(self, wl, spec):
        """Called on timer — only sets data, no style changes"""
        self._curve.setData(wl, spec)
```

**Same-color fill with 60% alpha**:

```python
def hex_to_rgba(hex_color: str, alpha: int) -> tuple:
    """Convert '#RRGGBB' to (r, g, b, alpha)"""
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )

# Usage:
r, g, b, a = hex_to_rgba(ColorScheme.SPECTRUM, 60)  # 60 = alpha
curve.setFillBrush(pg.mkBrush(r, g, b, a))
curve.setFillLevel(0)  # fill from y=0 up to curve
```

**Avoid 0-line in scrolling charts**:

```python
# Use "finite" connect mode + float("nan") for gaps
data.append(float("nan"))  # creates visual break
curve.setData(times, values, connect="finite")
```

## Key Design Decisions

| Decision | Why |
|----------|-----|
| Class variables, not dict | Works directly in f-strings: `f"color: {Colors.TEXT}"` |
| QSS from function, not file | `get_stylesheet()` re-reads `ColorScheme` each call |
| `enableAutoRange()` on all charts | Charts auto-scale on first data; prevents blank screens |
| Pen/brush created ONCE at init | `pg.mkPen()` allocates; avoid in hot path |
| Separate `refresh_color()` from `update_data()` | Data updates should NOT create new QPen objects |
| HBoxLayout (not QSplitter) for color panel | QSplitter keeps handle visible; hide() alone works with stretch |
| QSS via `QApplication.instance()` | Must use QApplication (not QMainWindow) for global coverage |

## Critical Gotchas

These caused real bugs during development — read before you write code.

### 1. QSS must target QApplication, not QMainWindow

```python
# WRONG — only affects MainWindow subtree, missing some widgets:
self.setStyleSheet(get_stylesheet())

# CORRECT — applies to every widget globally:
QApplication.instance().setStyleSheet(get_stylesheet())
```

### 2. QSS must be applied LAST (after all widgets exist)

Any widget that calls `setStyleSheet()` individually after the global QSS is applied will be overridden. Build the entire widget tree first, then apply QSS as the final step:

```python
def __init__(self):
    self._setup_ui()      # build all widgets
    QApplication.instance().setStyleSheet(get_stylesheet())  # apply QSS LAST
```

### 3. Do NOT call pyqtgraph theme at module import time

pyqtgraph's `setConfigOption("background", ...)` is global. If called at import time, it runs before settings are loaded and the color is stuck at the default:

```python
# WRONG — runs at import time with default colors:
_apply_pg_theme()  # module-level call

# CORRECT — run explicitly after colors are loaded:
def refresh_colors(self):
    _apply_pg_theme()           # update global defaults
    self.chart.setBackground(ColorScheme.DARK)  # update existing charts
```

### 4. Re-apply fill/pen after every `setData()` call

pyqtgraph's `setData()` can reset or clear pen/fill properties. Always re-apply them:

```python
def update_spectrum(self, wl, spec):
    self._curve.setData(wl, spec)
    self._apply_fill()  # MUST re-apply after setData
    self.autoRange()    # ensure viewport updates
```

### 5. `enableAutoRange()` + explicit `autoRange()` for reliability

`enableAutoRange()` alone can sometimes fail if the chart was initialized with empty data. Always call `autoRange()` explicitly on the first real data frame:

```python
def update_data(self, times, values):
    self._curve.setData(times, values)
    self.autoRange()  # safety net even with enableAutoRange()
```

### 6. Order of initialization matters

```
1. load_settings()              → read JSON
2. apply colors to ColorScheme  → set class variables
3. create widgets               → read ColorScheme during construction
4. build layout                 → all widgets in tree
5. apply QSS                    → LAST, via QApplication.instance()
6. call refresh_colors()        → update chart backgrounds + pens
```

## Adding More Customizable Colors

1. Add to `ColorScheme`: `NEW_COLOR = "#xxxxxx"`
2. Add row to `ColorPanel._init_ui()`: `("NEW_COLOR", "Label")`
3. Use in QSS: `{ColorScheme.NEW_COLOR}` in `get_stylesheet()`
4. Use in charts: `pg.mkPen(ColorScheme.NEW_COLOR, width=2)`

## Performance Checklist

- [ ] `QApplication.instance().setStyleSheet()` called only on color change (not on timer)
- [ ] `pg.mkPen()` / `pg.mkBrush()` only in `refresh_color()` (not in `update_data()`)
- [ ] `enableAutoRange()` on all charts (not `disableAutoRange()`)
- [ ] Max data points ≤ 1500
- [ ] Timer interval ≥ 400ms
- [ ] Only add 2-3 data points per tick
- [ ] Antialias off (`pg.setConfigOption("antialias", False)`)
