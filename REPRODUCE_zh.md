# REPRODUCE_zh.md — 面向 AI Agent 的集成指南

## 概述

本文档是**AI agent（或开发者）**基于此模板构建新 PyQt5 项目的**主要参考文档**。涵盖完整的颜色模型（5 个基础 + 5 个图表角色）、4 步集成界面、设置持久化、关键陷阱、扩展点和启动清单。修改任何文件前请先阅读本文。

**此模板提供的功能：** 一个用户可自定义的 PyQt5 动态颜色主题系统，包含 10 个独立可编辑的颜色角色、实时图表、可拖动图表标签和持久化设置 —— 全部围绕一个规则设计：系统使用的每个颜色都必须有用户可见的选择器。

**目标环境：** Python 3.6+、PyQt5、pyqtgraph。

---

## 设计理念

> **颜色可以少，但是一定要都有被用户管理的接口**

这是主导规则 —— 每个颜色必须满足全部四个一致性层次：

| 层次 | 文件 | 要求 |
|-------|------|-------------|
| 1. 类属性 | `color_scheme.py` | 在 `ColorScheme` 中定义为类级别字符串 |
| 2. 选择器行 | `color_panel.py` | 在三个区域之一中有一个 `ColorPickerRow` |
| 3. DEFAULTS 条目 | `settings_manager.py` | 在 `DEFAULTS["colors"]` 中列出以支持持久化 |
| 4. 消费者 | QSS 或图表代码 | 实际被渲染（QSS 规则、pen、brush 或标签样式） |

如果缺少任何一层，项目即处于违规状态 —— 要么接入孤立项，要么将其从所有层中移除。宁可减少颜色数量以保持完整性，也好过保留无效条目。

**BTN** 从 `LINE` 中分离出来作为一级基础颜色（v2），让用户可以独立控制按钮外观。`GRID` 和 `AXIS` 同样向用户暴露（位于 "Chart Display" 下），而非内部辅助项 —— 屏幕上出现的每个颜色都有相应的选择器。

### 已知一致性违规

**Start/Stop/Save 按钮（color_scheme.py 第 125-130 行）：** `#btn_start`、`#btn_stop` 和 `#btn_save` 的 objectName 选择器使用了 6 个硬编码的十六进制颜色，完全绕过了动态主题系统。这些颜色没有用户可见的选择器行、没有 DEFAULTS 条目、也没有 `ColorScheme` 类属性 —— 违反了全部四个一致性层次。这是有意为之的违规，因为 Start/Stop/Save 具有语义含义（绿色=启动、红色=停止、蓝色=保存），不应随用户的视觉主题变化。**如果需要完全一致性，请在部署到生产环境前替换。**

### 一致性检查

提交颜色相关更改前运行此脚本：

```python
from color_scheme import ColorScheme, ROLES_BASE, ROLES_CHART
from settings_manager import DEFAULTS

# ALL_ROLES 是规范列表 —— 通过 getattr 遍历它自然地
# 排除了 LABEL_ALPHA、LABEL_SIZE、AXIS_LABEL_SIZE 等可调常量，
# 无需使用 __dict__ 或 vars() 过滤。
ALL_ROLES = ROLES_BASE + ROLES_CHART
defined = {r for r in ALL_ROLES if isinstance(getattr(ColorScheme, r, None), str)}
persisted = set(DEFAULTS["colors"].keys())

# panel_rows 需要运行中的 QApplication；单独验证：
#   python -c "from PyQt5.QtWidgets import QApplication; app = QApplication([]);
#   from color_panel import ColorPanel; cp = ColorPanel();
#   print(set(cp._pickers.keys()))"
# 然后与 `defined` 和 `persisted` 比较。

missing_color_attr = persisted - defined
orphan_default = defined - persisted
assert not missing_color_attr, f"DEFAULTS 中有但 ColorScheme 中缺失的颜色: {missing_color_attr}"
assert not orphan_default, f"ColorScheme 中有但 DEFAULTS 中缺失的颜色: {orphan_default}"
print("OK: color_scheme.py <-> settings_manager.py 同步")
```

---

## 架构

```
┌─────────────────────────────────────────────┐
│              color_scheme.py                 │  ← 唯一真相源
│  ColorScheme（5 基础 + 5 图表颜色）           │     无 PyQt 导入
│  get_stylesheet() → 完整 QSS 字符串           │
│  hex_to_rgba() → (r,g,b,a) 用于图表画笔       │
└──────────────┬──────────────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
┌─────────┐ ┌──────┐ ┌──────────┐
│main_win │ │color │ │plot_wid  │
│dow.py   │ │panel │ │gets.py   │
│         │ │.py   │ │          │
│通过     │ │10 个 │ │来自      │
│QApp 的  │ │选择器│ │ColorSch  │
│QSS      │ │行    │ │的pen/brush│
└─────────┘ └──┬───┘ └──────────┘
               │
        color_changed(role, hex)
```

**数据流：**
1. `ColorPanel` 发出 `color_changed(role, hex)`
2. `MainWindow._on_color_changed()`：调用 `get_stylesheet()` → `QApplication.instance().setStyleSheet()`，然后 `self._charts.refresh_colors()`，然后 `self._save()`
3. 图表层：`_apply_pg_theme()` 设置全局背景/前景，每个图表从 `ColorScheme` 重建 pen/brush/label，`_apply_grid_axis()` 重新着色每个图表的网格+坐标轴

---

## 文件结构

```
project/
├── color_scheme.py        # 颜色状态 + QSS 生成器 + 颜色数学（零 Qt 导入）
├── color_panel.py         # 10 个 ColorPickerRow 控件，分 3 区域 + 重置
├── main_window.py         # 主窗口、参数面板、自动保存、键盘快捷键
├── plot_widgets.py        # 3 个 pyqtgraph 图表 + DraggableLabel + DataSimulator + ChartPanel
├── settings_manager.py    # JSON 持久化：DEFAULTS、深度合并加载、完整快照保存
└── settings.json           # 运行时自动生成（git 忽略）
```

`color_scheme.py` 是**根依赖** —— 被 `color_panel.py`、`plot_widgets.py` 和 `main_window.py` 导入。`settings_manager.py` 独立于 `color_scheme`（它只管理 JSON 持久化，导入 `json`、`os`、`sys`）。`color_panel.py` 和 `plot_widgets.py` 是同级模块，互不导入。

---

## 第 1 步：`color_scheme.py` — 颜色模型

这是所有颜色的唯一真相源。零 PyQt 导入 —— 纯 Python。

### 完整的 `ColorScheme` 类

```python
# color_scheme.py — 第 11-47 行

ROLES_BASE  = ["TEXT", "LIGHT", "DARK", "LINE", "BTN"]
ROLES_CHART = ["SPECTRUM", "TREND", "RESISTANCE", "GRID", "AXIS"]

class ColorScheme:
    # ── 5 个基础颜色（驱动 QSS） ──
    TEXT  = "#c0caf5"     # 文本 / 前景
    LIGHT = "#1e1f2e"     # 面板 / 表面背景
    DARK  = "#1a1b26"     # 主背景
    LINE  = "#3b3d56"     # 边框 / 分隔线
    BTN   = "#3b3d56"     # 按钮背景 + 边框（默认同 LINE）

    # ── 3 个图表曲线颜色 ──
    SPECTRUM   = "#0db9d7"
    TREND      = "#bb9af7"
    RESISTANCE = "#f7768e"

    # ── 2 个图表显示颜色 ──
    GRID = "#2c2d3f"      # 网格线
    AXIS = "#565f89"      # 坐标轴画笔 + 刻度标签

    # ── 3 个可调常量 ──
    LABEL_SIZE       = 14   # 图表标签字体大小（px）
    LABEL_ALPHA      = "ff" # 标签背景不透明度（十六进制：00=透明，ff=不透明）
    AXIS_LABEL_SIZE  = 13   # 坐标轴刻度字体大小（px）

    @classmethod
    def set_color(cls, role: str, hex_color: str) -> bool:
        if not HEX_PATTERN.match(hex_color):
            return False
        if hasattr(cls, role.upper()):
            setattr(cls, role.upper(), hex_color.upper())
            return True
        return False
```

**关键反模式：** 不要用字典替换类属性。`get_stylesheet()` 中的 f-string 人机工程学依赖于 `ColorScheme.TEXT` 语法。字典则需要到处使用 `ColorScheme.colors["TEXT"]`。

### `_adjust(hex, amount)` — 精确增量值

```python
# color_scheme.py — 第 49-54 行

def _adjust(hex_color: str, amount: int) -> str:
    """将 amount 加到每个 RGB 通道来调亮 (+) 或调暗 (-) 十六进制颜色。"""
    hex_color = hex_color.lstrip('#')
    r = max(0, min(255, int(hex_color[0:2], 16) + amount))
    g = max(0, min(255, int(hex_color[2:4], 16) + amount))
    b = max(0, min(255, int(hex_color[4:6], 16) + amount))
    return f"#{r:02x}{g:02x}{b:02x}"
```

`get_stylesheet()` 中的 6 个派生颜色（第 75-80 行）：

| 派生色 | 公式 | 用途 |
|---------|---------|----------|
| `text2` | `_adjust(TEXT, -30)` | QLabel 文本、QPlainTextEdit 文本、状态栏文本 |
| `text3` | `_adjust(TEXT, -50)` | 禁用按钮文本 |
| `dark2` | `_adjust(DARK, -6)` | QMainWindow 背景、QLineEdit/SpinBox 背景、状态栏背景 |
| `light2` | `_adjust(LIGHT, +10)` | （已定义但当前 QSS 中未使用） |
| `accent` | `_adjust(LIGHT, +30)` | GroupBox 标题、焦点边框、悬停高亮 |
| `btn_hover` | `_adjust(BTN, +10)` | QPushButton:hover 背景 |

### `get_stylesheet()` — QSS 生成

```python
# color_scheme.py — 第 68-197 行

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
    # 加上 btn_start/btn_stop/btn_save 的硬编码 #objectName 选择器（第 125-130 行）
```

**QSS 选择器覆盖范围：** 样式表针对 `QWidget`、`QMainWindow`、`QLabel`、`QGroupBox` + `::title`、`QPushButton`（含 `:hover`、`:pressed`、`:disabled` 伪状态）、`QLineEdit`（+ `:focus`）、`QSpinBox`/`QDoubleSpinBox`（+ `:focus`）、`QComboBox`（+ `:focus`）、`QComboBox QAbstractItemView`、`QSplitter::handle`（+ `:hover`）、`QPlainTextEdit`、`QStatusBar`、`QScrollBar:vertical`/`:horizontal`（handle + `:hover`，`add-line`/`sub-line` 隐藏）。

**硬编码的 Start/Stop/Save 按钮颜色**（第 125-130 行）完全绕过动态主题系统：
- `#btn_start`：绿色（#1a6b3c / #228b4a）
- `#btn_stop`：红色（#6b1a1a / #8b2222）
- `#btn_save`：蓝色（#1a4a6b / #225f8b）

**新领域的指导：** 要么删除这些硬编码选择器让按钮遵循动态 `QPushButton` 主题，要么将颜色替换为适合领域的语义（如数据采集的 "Arm"/"Trigger"/"Record"）。如果添加新的主题化按钮角色，必须增加完整的一致性（ColorScheme 属性 + 选择器行 + DEFAULTS 条目 + QSS 消费者）。

### `hex_to_rgba()` — 图表颜色数学

```python
# color_scheme.py — 第 57-65 行

def hex_to_rgba(hex_color: str, alpha: int) -> tuple:
    """将 '#RRGGBB' 转换为 (r, g, b, alpha) 供 pg.mkBrush() 使用。"""
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )
```

---

## 第 2 步：`color_panel.py` — 颜色选择器 UI

### `ColorPickerRow` — 单颜色行

```python
# color_panel.py — 第 16-75 行

class ColorPickerRow(QWidget):
    color_changed = pyqtSignal(str)  # 发出新的十六进制颜色

    # 布局：[10×10 色块] [28px 标签] [64px 十六进制 QLineEdit] [18px 🎨 QPushButton]
    #
    # 色块边框为硬编码的 '#555' —— 不遵循动态主题。
    # show_label 参数（默认 True）存在但从未被任何调用点设为 False
    # —— 保留供未来紧凑布局使用。
    #
    # _on_hex()：由 editingFinished 触发
    #   - 匹配 HEX_PATTERN → 调用 set_color()
    #   - 失败时 → 设置 border: 1px solid red，回退文本到上一个有效颜色
    # _on_picker()：打开 QColorDialog.getColor()，有效选择时调用 set_color()
    # set_color(c)：更新色块背景、十六进制文本，发出 color_changed
```

### `ColorPanel` — 10 个选择器行 + 重置

```python
# color_panel.py — 第 78-147 行

class ColorPanel(QWidget):
    color_changed = pyqtSignal(str, str)  # (role, hex_color)

    # 三个区域：
    #   "Base Colors":    TEXT, LIGHT, DARK, LINE, BTN
    #   "Chart Curves":   SPECTRUM, TREND, RESISTANCE
    #   "Chart Display":  GRID, AXIS
    #
    # setFixedWidth(170)
    # 重置按钮将所有 10 个角色恢复到 ColorScheme 类属性的默认值
    # （运行时读取 settings_manager.DEFAULTS["colors"]）
```

**重置默认值**（`color_panel.py` 第 139-143 行）必须同时匹配 `ColorScheme` 类属性和 `settings_manager.DEFAULTS`：

```python
defaults = {
    "TEXT":"#c0caf5","LIGHT":"#1e1f2e","DARK":"#1a1b26","LINE":"#3b3d56","BTN":"#3b3d56",
    "SPECTRUM":"#0db9d7","TREND":"#bb9af7","RESISTANCE":"#f7768e",
    "GRID":"#2c2d3f","AXIS":"#565f89",
}
```

**警告：** 这是出厂默认颜色值的第三个独立副本。如果更改了 `ColorScheme` 类属性或 `settings_manager.DEFAULTS` 中的默认值但忘记此处，重置按钮将静默地恢复到过时的错误颜色。这是已知的维护隐患 —— 正确做法见"自定义默认调色板"扩展点。

**反模式：** 添加 `ColorPickerRow` 而不在 `ColorScheme` 中添加相应的类属性会创建孤立选择器 —— `_on_change` 处理器调用 `ColorScheme.set_color()` 将静默失败（返回 `False`），且没有控件使用该颜色。

---

## 第 3 步：`main_window.py` — 主窗口

### 窗口默认值

| 设置 | 值 | 行号 |
|---------|-------|------|
| 窗口标题 | "OptoSync — Synchronized Acquisition System" | 25 |
| 默认大小 | 1440×920 | 26 |
| 最小大小 | 1100×700 | 27 |
| 日志面板最大行数 | 500（`setMaximumBlockCount`） | 140 |
| 日志占位文本 | "Log output — demo mode" | 141 |
| 状态栏消息 | "Ready — Demo Mode \| Simulated data" | 285 |

### 布局结构

```
┌──────────┬──┬──────────────────────┬──┬──────────┐
│ 参数     │◀ │ 图表（QSplitter）     │▶ │ 颜色     │
│ 面板     │  │ ┌──────────────────┐ │  │ 面板     │
│ (300px)  │  │ │ SpectrumChart    │ │  │ (170px)  │
│          │  │ │ TrendChart       │ │  │          │
│          │  │ │ SourceMeterChart │ │  │          │
│          │  │ └──────────────────┘ │  │          │
│          │  │ ▼ 日志面板 (150px)  │  │          │
└──────────┴──┴──────────────────────┴──┴──────────┘
```

切换按钮是 `QPushButton`，`setFixedSize(12, 30)`（第 161 行），箭头文本（`◀`/`▶`/`▼`/`▲`），放置在 `QHBoxLayout` 内容区域的面板之间。切换按钮颜色通过控件级 `setStyleSheet()` 硬编码（`color:#606060`，悬停 `#c0c0c0`，第 164-167 行），完全绕过动态主题 —— 控件级样式表的级联优先级高于 `QApplication.setStyleSheet()`。

### 初始化顺序（精确序列）

此顺序至关重要 —— 违反顺序会导致空白图表、未样式化的控件或多余的磁盘写入。当前代码没有运行时断言或防护来阻止重排序 —— 违反此序列会产生静默失败而非明确的错误：

```
1. load_settings()                        → 带合并默认值和已保存值的字典
2. _apply_loaded_colors()                 → 对所有 10 个角色调用 ColorScheme.set_color()
3. _setup_ui()                            → 创建所有控件（它们在 __init__ 期间读取 ColorScheme）
   └─ 包含 apply_label_positions()       → 来自 settings 的 chart_labels（第 121 行）
4. _apply_loaded_params()                 → 从 settings["params"] 恢复 spinbox/combo 值
5. _connect_param_signals()               → 将 valueChanged 连接到 _save（在步骤 4 之后，避免多余的首次写入）
6. QApplication.instance().setStyleSheet(get_stylesheet())  → 最后应用 QSS
7. self._charts.refresh_colors()          → 在 QSS 之后
8. 恢复面板状态                           → settings["panels"]（第 46-52 行）
```

实现参考：`main_window.py` 第 23-52 行。

**关于步骤 3 的说明：** 图表标签在控件构造期间从已保存的设置中定位（`_setup_ui()` 内第 121 行的 `apply_label_positions()`），而非如预期的在主题/颜色刷新之后。位置恢复期间 `DraggableLabel._apply_style()` 设置的标签样式使用当时 `ColorScheme` 的当前值 —— 在正确的顺序中，这些值已在步骤 2 中加载。

### 颜色更改处理器

```python
# main_window.py — 第 256-259 行

def _on_color_changed(self, role: str, color: str):
    QApplication.instance().setStyleSheet(get_stylesheet())  # 重新皮肤化所有控件
    self._charts.refresh_colors()                             # 重新着色图表
    self._save()                                              # 持久化到磁盘
```

### 自动保存（`_save()`）

```python
# main_window.py — 第 261-276 行

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

**每次 `_save()` 调用都是完整快照** —— 全部 10 个颜色、全部 7 个参数、全部 3 个面板布尔值，以及 chart_labels（由第 92 行的 `_save_chart_labels` 在第 93 行 `_save()` 运行之前写入）。

> **关键：** 第 262-263 行的颜色角色列表是**硬编码字面量** —— 并非从 `ROLES_BASE + ROLES_CHART` 派生。在 `ColorScheme` 和 `ROLES_BASE`/`ROLES_CHART` 中添加新颜色角色而不更新此列表，会导致新角色**被静默排除在持久化之外**（用户颜色在重启后丢失）。反之，从 `ColorScheme` 中移除角色但保留在此列表中，会导致 `_save()` 内部抛出 **AttributeError**，而 `_save()` 连接到每个参数控件的更改信号，使得任何用户交互都会导致 UI 无法操作。**修复方法：** 将硬编码列表替换为从 `color_scheme` 导入的 `ROLES_BASE + ROLES_CHART`：
> ```python
> from color_scheme import get_stylesheet, ColorScheme, ROLES_BASE, ROLES_CHART
> # 在 _save() 中：
> self._settings["colors"] = {r: getattr(ColorScheme, r) for r in ROLES_BASE + ROLES_CHART}
> ```

### 孤立按钮（Start/Stop/Save）

```python
# main_window.py — 第 204-209 行

for t, o in [("Start", "btn_start"), ("Stop", "btn_stop"), ("Save", "btn_save")]:
    b = QPushButton(t); b.setObjectName(o)
    b.setStyleSheet("padding:6px 10px;")
    bl.addWidget(b)
```

这些按钮有用于 QSS 定位的 `objectName`，但**没有 `clicked` 连接**。它们是硬件控制的自然接入点 —— 将它们连接到你的采集控制器。

### 键盘快捷键

```python
# main_window.py — 第 250-254 行

def keyPressEvent(self, event: QKeyEvent):
    if event.key() == Qt.Key_F10:
        self.showFullScreen()
    elif event.key() == Qt.Key_Escape:
        self.showNormal()
```

### 图表标签保存

```python
# main_window.py — 第 82-93 行

def _save_chart_labels(self, x, y, w, h):
    sender = self.sender()
    if sender is self._charts.spectrum._label        : key = "spectrum"
    elif sender is self._charts.trend._label          : key = "trend"
    elif sender is self._charts.sourcemeter._label    : key = "sourcemeter"
    else: return
    self._settings.setdefault("chart_labels", {})[key] = {"x": x, "y": y, "w": w, "h": h}
    self._save()
```

在第 124-126 行连接：每个图表的 `_label.pos_changed` → `_save_chart_labels`。

> **警告：** 此方法使用 `self.sender()` 来识别源图表，仅在通过 Qt 信号发出时有效。如果直接调用（如 `self._save_chart_labels(0,0,80,20)`），`sender()` 返回 `None`，整个 if/elif 链落空，函数静默退出，无保存也无错误。为了可扩展性，重构为接受显式的 chart_key 参数，并使用 `functools.partial` 进行信号连接：
> ```python
> from functools import partial
> def _save_chart_labels(self, chart_key: str, x, y, w, h):
>     self._settings.setdefault("chart_labels", {})[chart_key] = {"x": x, "y": y, "w": w, "h": h}
>     self._save()
> self._charts.spectrum._label.pos_changed.connect(partial(self._save_chart_labels, "spectrum"))
> ```

### 日志面板钩子

```python
# main_window.py — 第 287-291 行

def _append_log(self, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    self._log_panel.appendPlainText(f"{ts} {msg}")
    sb = self._log_panel.verticalScrollBar()
    sb.setValue(sb.maximum())
```

此方法作为集成钩子存在，但**当前代码库中没有任何地方调用它**。它在每次追加时自动滚动到底部，并使用 `%H:%M:%S` 时间戳格式。集成时将其连接到硬件状态事件。

---

## 第 4 步：`plot_widgets.py` — 动态图表

### 性能模式：样式与数据分离

```python
# 每个图表都遵循此模式：
class SomeChart(pg.PlotWidget):
    def __init__(self):
        # Pen/brush 在初始化时创建一次
        self._curve = self.plot([], [], pen=pg.mkPen(ColorScheme.SOME_COLOR, width=2))

    def refresh_color(self):
        # 仅在主题更改时调用 —— 重建 pen/brush/label/grid/axis
        self._curve.setPen(pg.mkPen(ColorScheme.SOME_COLOR, width=2))
        self._label.set_color(ColorScheme.SOME_COLOR)
        self._label._apply_style()
        _apply_grid_axis(self)
        self._apply_axis_font()

    def update_data(self, x, y):
        # 在定时器上调用 —— 仅设置数据，无样式更改
        self._curve.setData(x, y)
```

### 图表类样板代码 vs. 领域特定代码

三个图表类共享大量重复的样板代码，与领域特定细节混在一起：

**强制样板代码（每个图表都相同）：**
- `_apply_axis_font()` — 6 行方法，在三个类中原样复制粘贴
- `set_label_pos()` — 2 行方法，原样重复
- `refresh_color()` 框架 — 调用 `setPen`、`set_label color`、`_apply_style`、`_apply_grid_axis`、`_apply_axis_font`

**每图表可配置（领域特定）：**
- 坐标轴标签（`setLabel` 调用）
- Pen 宽度（2.0 vs 2.2）
- 颜色角色常量
- DraggableLabel 文本

**每图表可选：**
- 填充（SpectrumChart 的 `_apply_fill`）
- 符号标记（TrendChart 的 `symbol="o"`、`symbolSize=3`）
- 连接模式（SourceMeterChart 的 `connect="finite"`）
- X 轴链接拓扑（`setXLink`）

为了构建干净的模板，提取一个 `_BaseChart(pg.PlotWidget)` 父类来处理所有强制样板代码。每个具体图表只需定义约 15 行领域特定代码加上可选覆盖。

### `DraggableLabel` — 样式机制

```python
# plot_widgets.py — 第 37-127 行

class DraggableLabel(QLabel):
    pos_changed = pyqtSignal(int, int, int, int)  # 释放时 (x, y, w, h)

    # 背景：来自 ColorScheme.LIGHT 的 RGBA
    #   r = int(LIGHT[1:3], 16), g = int(LIGHT[3:5], 16), b = int(LIGHT[5:7], 16)
    #   alpha = int(ColorScheme.LABEL_ALPHA, 16)  → "ff" 变为 255
    # 边框：1px solid ColorScheme.LINE
    # 文本颜色：曲线的颜色（self._color）
    # 字体大小：max(8, int(height * 0.72))

    # 区域：
    #   右下角 20×20：调整大小（最小 40×20）
    #   其他位置：    拖动移动
```

样式表构造位于第 58-80 行 —— 注意直接解析 `ColorScheme.LIGHT` 字符的 `rgba()` 字符串格式化。

### `_apply_pg_theme()` 和 `_apply_grid_axis()`

```python
# plot_widgets.py — 第 14-34 行

def _apply_pg_theme():
    """必须显式调用，不能在模块级别调用。"""
    pg.setConfigOption("background", ColorScheme.DARK)
    pg.setConfigOption("foreground", ColorScheme.TEXT)
    pg.setConfigOption("antialias", False)
    pg.setConfigOptions(useOpenGL=False, leftButtonPan=False)

def _apply_grid_axis(chart):
    pg.setConfigOption("foreground", ColorScheme.GRID)
    chart.showGrid(x=True, y=True, alpha=0.4)
    pg.setConfigOption("foreground", ColorScheme.TEXT)  # 恢复

    pen = pg.mkPen(ColorScheme.AXIS, width=1)
    for name in ("left", "bottom"):
        ax = chart.getAxis(name)
        ax.setPen(pen)
        ax.setTextPen(pen)
    chart._apply_axis_font()
```

注意：`_apply_pg_theme()` 调用 `pg.setConfigOptions(useOpenGL=False, leftButtonPan=False)`（第 18 行）。OpenGL 已禁用；左键平移已禁用（仅右键可平移）。之前的文档均未提及这些 pg 配置选项 —— 它们影响用户与图表的交互方式。

### 图表类

| 图表 | X 标签 | Y 标签 | 曲线模式 | 缓冲区 | X 链接 | 节流 |
|-------|---------|---------|------------|--------|--------|----------|
| `SpectrumChart`（第 129 行） | "Wavelength (nm)" | "Intensity" | 默认 | 完整数据 | — | 每 5 tick |
| `TrendChart`（第 173 行） | "Time (s)" | "Intensity" | 默认，symbol="o" | 1000 点 | 链接到 SourceMeter | 无 |
| `SourceMeterChart`（第 216 行） | "Time (s)" | "Resistance (Ω)" | **connect="finite"** | 1000 点 | **驱动共享 X 轴** | 无 |

- `TrendChart` 底部轴已隐藏（第 310 行 `self.trend.hideAxis("bottom")`），因为 `SourceMeterChart` 通过 `setXLink` 驱动共享时间轴。
- 仅 `SourceMeterChart` 使用 `connect="finite"`（第 228 行）—— 电流为零时 `float("nan")` 值创建视觉断点。`TrendChart` 使用默认线条模式（无 `connect` 参数，第 183-187 行）。
- 60 秒滚动 X 窗口：`self.sourcemeter.setXRange(max(0, last_time - 60), last_time + 5)`（第 385 行）。

**图表拓扑（添加/删除图表时的关键信息）：**

三个图表形成 X 轴链接链，其中 `SourceMeterChart` 是 X 轴主节点：

```
TrendChart ── setXLink ──→ SourceMeterChart（X 轴主节点）
  ↑                            ↑
  │ 底部轴隐藏                  │ setXRange() 驱动共享自动滚动
  └────────────────────────────┘
```

`TrendChart` 和 `SourceMeterChart` 都在同一个 `QSplitter` 堆栈中。如果移除 `SourceMeterChart`（从 3 个图表减为 2 个），必须：
1. 从 TrendChart 移除 `setXLink` 和 `hideAxis("bottom")`
2. 将 `setXRange()` 自动滚动调用移至 TrendChart 自身（将 `self.sourcemeter.setXRange(...)` 替换为 `self.trend.setXRange(...)`）
3. 从 splitter 和全部 4 个标签键位置中移除 `SourceMeterChart`（参见"添加新图表"扩展点）
4. `_tick()` 方法的三个独立代码块也需要修剪

如果添加第 4 个图表且有独立的 X 轴，需决定它是否链接到现有 X 轴主节点还是独立驱动。

### `DataSimulator` — 占位实现

```python
# plot_widgets.py — 第 256-287 行

class DataSimulator:
    @staticmethod
    def spectrum(wavelengths=None) -> (list, list):
        # 1400 个波长区间（300-1000nm，步长 0.5nm）
        # 3 个高斯峰：
        #   - 450nm，sigma=30，amplitude=800
        #   - 550nm，sigma=25，amplitude=500
        #   - 680nm，sigma=20，amplitude=300
        # 噪声：gauss(0, 15)，裁剪到 >= 0

    @staticmethod
    def trend(n_points) -> (list, list):
        # 信号：500 + 200*sin(t*0.5)*exp(-t*0.01)
        # 噪声：gauss(0, 10)，n_points

    @staticmethod
    def sourcemeter(n_points) -> (list, list):
        # V(t) = 5.0 + 0.1*sin(t*2)
        # I(t) = 0.003 + 0.0002*cos(t*3)
        # R = V/I，I=0 时为 NaN，n_points
```

**替换** 3 个静态方法为一个基于 QObject 的硬件驱动，发出类型化信号（每图表一个）。`ChartPanel._tick()` 定时器循环（第 363-396 行）以 500ms 驱动轮询 —— 对于信号驱动的采集，将定时器替换为连接到逐图表 `update_*` 方法的工作线程信号。

**真实硬件的具体集成模式（基于 QThread 的 SensorWorker）：**

```python
# plot_widgets.py — 替换 DataSimulator + ChartPanel._tick() QTimer

from PyQt5.QtCore import QObject, pyqtSignal, QThread

class SensorWorker(QObject):
    """硬件传感器读取器 —— 在专用 QThread 中运行。
    替换 DataSimulator 静态方法 + ChartPanel._tick() QTimer。
    发出三个类型化信号，每图表一个。
    """
    spectrum_ready = pyqtSignal(list, list)       # (wavelengths, intensities)
    trend_ready = pyqtSignal(list, list)          # (times, values)
    sourcemeter_ready = pyqtSignal(list, list)    # (times, resistance)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    SPECTRUM_THROTTLE = 5  # 每 N 个 tick 发出一次 spectrum

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
        self.status_changed.emit("采集已启动")
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

    # ---------- 硬件桩（替换为真实驱动调用） ----------
    def _read_spectrometer(self):
        return DataSimulator.spectrum(self._wl_cache)

    def _read_trend(self, n_points):
        return DataSimulator.trend(n_points)

    def _read_sourcemeter(self, n_points):
        return DataSimulator.sourcemeter(n_points)
```

**ChartPanel 集成（需要更改的内容）：**

```python
# 从 ChartPanel.__init__() 中删除：
#   self._timer = QTimer(self)
#   self._timer.timeout.connect(self._tick)
#   self._timer.start(500)

# 添加工作线程设置：
self._worker_thread = QThread(self)
self._sensor = SensorWorker()
self._sensor.moveToThread(self._worker_thread)
self._sensor.spectrum_ready.connect(self.spectrum.update_spectrum)
self._sensor.trend_ready.connect(self._on_trend_data)
self._sensor.sourcemeter_ready.connect(self._on_sourcemeter_data)
self._worker_thread.started.connect(self._sensor.start_acquisition)

# 添加分发方法（缓冲区管理保留在 ChartPanel 中）：
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

**关键设计说明：**
- **推送替代轮询：** QTimer 已移除；worker 通过 while 循环中的 `QThread.msleep(500)` 驱动
- **Spectrum 节流保留：** `SPECTRUM_THROTTLE = 5` 常量和 `_tick_count` 计数器
- **线程安全：** pyqtgraph 方法（`setData`、`setXRange`、`autoRange`）通过 `moveToThread` 的信号-槽传递自动在 GUI 线程中调用
- **优雅关闭：** `stop_acquisition()` 设置 `_running=False`，while 循环退出，然后 `quit()` + `wait()` 清理 QThread
- **缓冲区管理保留在 ChartPanel 中：** worker 发出原始点；ChartPanel 处理 MAX_POINTS 截断和 X 轴范围
- **`_data_counter` 已移除：** 时间跟踪移至 worker 的 `_tick_count`

### `ChartPanel` — 容器

```python
# plot_widgets.py — 第 290-405 行

class ChartPanel(QWidget):
    # 垂直 QSplitter，含 3 个图表
    # QTimer 每 500ms → _tick()（第 322 行）
    # showEvent → 通过 QTimer.singleShot(0, ...) 一次性 _align_y_axes()（第 324-328 行）
    #   延迟执行原理：在 Qt 绘制控件之前，坐标轴宽度不可用，
    #   因此 singleShot(0) 在首个事件循环周期完成后调度对齐。
    # apply_label_positions(positions: dict) — 逐图表恢复 {x,y,w,h}（第 342-361 行）
```

**Spectrum 节流原理**（第 368 行）：

Spectrum 图表被节流到每 5 个 tick（`self._data_counter <= 1 or self._data_counter % 5 == 0`），因为 `DataSimulator.spectrum()` 每次更新生成 1400 个波长点（范围 300-1000nm，步长 0.5nm）。滚动图表（Trend、SourceMeter）每次仅添加 2 个点。每 500ms 完整重绘 1400 个点的 spectrum 会饱和 Qt 事件循环。**新图表的决策规则：** 如果每次更新的点数超过约 500，则节流；否则每个 tick 更新。`<= 1` 条件确保首个 tick 始终立即渲染（启动时无空白图表）。

**已知限制 — QSplitter 未持久化：**

第 299 行持有三个图表的 `QSplitter` 是局部变量（`splitter = pg.QtWidgets.QSplitter(...)`），未存储为实例属性。没有分割器手柄位置的保存/恢复逻辑。图表分割器位置在重启时丢失 —— 用户每次会话需重新拖动手柄。要修复，赋值给 `self._chart_splitter` 并添加 `sizes()` 的 get/set 方法。

---

## 设置持久化 — 完整模式

### `DEFAULTS` 字典（`settings_manager.py` 第 28-55 行）

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

### 仅运行时键（不在 DEFAULTS 中，由 `setdefault` 添加）

```json
"panels": {
  "left":  true,
  "right": true,
  "log":   true
}
```

### 合并逻辑（`load_settings()` — 第 58-75 行）

1. 如果 `settings.json` 不存在 → 原样返回 `DEFAULTS`（**警告：返回的是模块级常量引用，而非副本 —— 见下方"已知问题"**）
2. 从磁盘解析 JSON
3. 将 `DEFAULTS` 浅拷贝到 `merged`
4. 顶层 `merged.update(data)`（保留未知键）
5. 逐子字典浅合并：`merged["colors"] = {**DEFAULTS["colors"], **data["colors"]}`（`params`、`chart_labels` 同理）
6. 遇到 `JSONDecodeError` 或 `IOError` → 返回 `DEFAULTS`（**静默 —— 无日志、无警告、无用户通知**）

这是一个增量/宽容的合并：未来版本中添加到 DEFAULTS 的新键自动出现；从 DEFAULTS 移除但在 JSON 文件中存在的键在内存中保留（潜在的陈旧配置内存泄漏 —— 如 `"LIGHTT"` 这样的拼写错误会永久累积且无清理机制）。

**已知问题：**

1. **文件未找到时按引用返回：** `load_settings()` 在 `settings.json` 缺失时直接返回模块级 `DEFAULTS` 字典（而非副本）。如果调用方修改返回的字典（如 `_save()` 执行 `self._settings["colors"] = {...}`），全局 `DEFAULTS` 常量被永久破坏。后续 `load_settings()` 调用返回用户上次保存的颜色而非出厂默认值。**这是首次运行时 `_reset()` 按钮恢复用户颜色而非出厂默认值的根本原因。** 修复方法：返回 `DEFAULTS.copy()` 而非 `DEFAULTS`。

2. **静默 JSON 错误抑制：** 遇到 `JSONDecodeError` 或 `IOError` 时，函数返回 `DEFAULTS`，零日志或用户通知。带有尾随逗号的手动编辑 `settings.json` 被静默丢弃。更糟的是，自动保存链（`_save()` → `save_settings()`）立即**覆盖**损坏的文件为基于默认值的新状态，永久销毁所有可挽救的数据。**诊断方法：** 如果应用在编辑 settings.json 后以出厂默认值启动，请使用 `python -m json.tool settings.json` 检查 JSON 语法错误。

3. **从 DEFAULTS 移除的键永久保留：** 由于增量合并逻辑（步骤 5 使用 `{**DEFAULTS, **data}`），任何存在于用户 `settings.json` 中但随后从 `DEFAULTS` 移除的键（如重命名或删除的颜色角色）都会在内存中保留并在每次保存时写回磁盘。没有清理机制。定期检查 `settings.json` 中的陈旧条目。

### 文件路径解析（`_get_settings_dir()` — 第 8-23 行）

- **开发环境**（`sys.frozen` 为 False）：`os.path.dirname(__file__)` → 项目目录
- **冻结/PyInstaller**（`sys.frozen` 为 True）：`os.path.dirname(sys.executable)` → 包含 `.exe` 的目录

**关键：** 使用 `sys.executable`，而非 `sys._MEIPASS`。`_MEIPASS` 是临时解压目录，只读且在退出时删除。它仅适用于定位打包的资源文件（图标、图片），绝不用于写入数据。

**注意：** `SETTINGS_FILE` 在模块导入时解析（第 26 行），而非在保存/加载调用时。如果工作目录或 `sys.executable` 在导入后发生变化，路径将过期。

### 保存触发器（全部调用 `MainWindow._save()`）

| 触发器 | 来源 | 行号 |
|---------|--------|------|
| 颜色更改 | `_on_color_changed` | 259 |
| 参数控件更改 | `_connect_param_signals`（7 个控件） | 74-80 |
| 面板切换 | `_toggle_left/right/log_panel` | 224,236,248 |
| 标签拖动/释放 | `_save_chart_labels` | 93 |
| 窗口关闭 | `closeEvent` | 279 |

每个触发器写入所有颜色、参数、面板和 chart_labels 的**完整快照**。

---

## 关键陷阱

### 1. QSS 必须应用于 QApplication，而非 QMainWindow

```python
# 错误 — 仅影响 MainWindow 子树，遗漏部分控件：
self.setStyleSheet(get_stylesheet())

# 正确 — 全局应用于每个控件：
QApplication.instance().setStyleSheet(get_stylesheet())
```

### 2. QSS 必须最后应用

先构建完整的控件树，恢复参数，连接信号，然后再应用 QSS。全局 QSS 之后对任何单个控件的 `setStyleSheet()` 调用都会被覆盖。参见第 3 步的初始化顺序。

**另外：** 切换按钮（`_left_toggle`、`_right_toggle`、`_log_toggle`）使用控件级 `setStyleSheet()` 调用（main_window.py 第 164-167 行），其级联优先级高于 `QApplication.setStyleSheet()`。更改任何 `ColorScheme` 颜色对这三个按钮零影响 —— 它们有意独立于主题。

### 3. 不要在模块导入时调用 pyqtgraph 主题

```python
# 错误 — 导入时以默认颜色运行，在设置加载之前：
_apply_pg_theme()  # 模块级调用

# 正确 — 定义函数，在颜色加载后显式调用：
def refresh_colors(self):
    _apply_pg_theme()
    # 然后逐图表 refresh_color()
```

`_apply_pg_theme()` 在 `plot_widgets.py` 第 14 行定义，但仅从 `ChartPanel.refresh_colors()`（第 399 行）调用。

### 4. SpectrumChart 在 `setData()` 后重新应用填充

pyqtgraph 的 `setData()` 可能重置填充画刷。对于 `SpectrumChart`，在每次 `setData()` 后重新应用填充：

```python
# plot_widgets.py 第 167-170 行
def update_spectrum(self, wl, spec):
    self._curve.setData(wl, spec)
    self._apply_fill()   # 必须在 setData 后重新应用（填充画刷可能被重置）
    self.autoRange()
```

Pen **不需要**重新应用 —— 一旦设置，它在 `setData()` 调用之间持续存在。`TrendChart` 和 `SourceMeterChart` 在 `setData()` 后既不重新应用填充也不重新应用 pen（它们没有填充，且 pen 的持久性足够）。

### 5. `enableAutoRange()` + 显式 `autoRange()` 以确保可靠性

仅使用 `enableAutoRange()` 可能在图表以空数据初始化时失败。始终在首个真实数据帧（或安全起见每帧）上调用 `autoRange()`：

```python
# 三个图表都在 __init__ 中调用 enableAutoRange()
# SpectrumChart 在 update_spectrum() 中调用 autoRange()（第 170 行）
# TrendChart 和 SourceMeterChart 依赖 enableAutoRange() + 链接的 X 范围（第 385 行）
```

### 6. 初始化顺序很重要

参见第 3 步的 8 步编号列表。顺序 `load → apply colors → create widgets (incl. labels) → apply params → connect signals → QSS → refresh charts → panels` 是不可协商的。违反它会导致：
- 控件在颜色加载前构造：过时的默认值
- 信号在参数恢复前连接：启动时多余的保存
- QSS 在控件树完成前应用：未样式化的控件
- `refresh_colors()` 在 QSS 之前：图表背景/前景不匹配

没有运行时断言或防护强制此顺序 —— 违反产生静默失败而非明确的错误。

### 7. 冻结 exe 路径：`sys.executable`，而非 `sys._MEIPASS`

```python
# settings_manager.py 第 8-23 行
def _get_settings_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)  # 持久、可写
    return os.path.dirname(__file__)
```

`sys._MEIPASS` 是临时解压目录 —— 只读且在退出时删除。仅用于定位打包的资源文件。

### 8. BTN 默认值与 LINE 相同

`BTN` 默认为 `#3b3d56`，与 `LINE` 相同。更改 `LINE` **不会**自动更新 `BTN` —— 用户必须分别更改两者。这种通过默认值的耦合在 UI 中不可见：两个选择器最初都显示 `#3b3d56`。要保持按钮边框与其他边框匹配，请同时更新 `LINE` 和 `BTN`。

### 9. `sample_rate` 参数未连接到定时器

`DEFAULTS["params"]` 中的 `sample_rate` 参数（settings_manager.py 第 48 行）跨会话存储和恢复，但从未在运行时用于更改 `QTimer` 间隔（在 ChartPanel 第 322 行固定为 500ms）。它作为用户可见的硬件配置参考参数存在，而非运行时控制。如需动态速率控制，将其连接到 `ChartPanel._timer.setInterval(sample_rate * 1000)`。

### 10. `refresh_colors()` 冗余设置每图表背景

在 `plot_widgets.py` 第 400-402 行，`refresh_colors()` 在 `_apply_pg_theme()` 已设置全局背景后，显式对每个图表调用 `ch.setBackground(ColorScheme.DARK)`。这在正常操作下是冗余的，但作为安全网，防止个别图表被单独样式化。

---

## 扩展点

### 添加新颜色角色

1. 在 `ColorScheme` 中添加类属性（如 `NEW_COLOR = "#xxxxxx"`）
2. 添加到 `ROLES_BASE` 或 `ROLES_CHART` 列表（color_scheme.py 第 11-12 行）
3. 在 `ColorPanel._init_ui()` 的适当区域中添加 `ColorPickerRow`（color_panel.py 第 98-126 行）并附带标签
4. 添加到 `settings_manager.DEFAULTS["colors"]`（第 29-40 行）
5. 添加到 `ColorPanel._reset()` 默认值（第 139-143 行）
6. 在 `get_stylesheet()` 或 `refresh_color()`/`_apply_pg_theme()`/`_apply_grid_axis()` 中使用
7. **关键：** 将新角色名称添加到 `MainWindow._save()` 中的硬编码列表（main_window.py 第 262-263 行）—— 此列表不会在运行时从 `ROLES_BASE + ROLES_CHART` 派生。缺少此步骤会导致静默数据丢失（新角色颜色不会跨重启持久化）。

### 将 DataSimulator 替换为真实硬件

1. 将 `plot_widgets.py` 中的 3 个静态方法（第 256-287 行）替换为发出类型化信号的基于 QObject 的 worker（参见上面第 4 步的 `SensorWorker` 模式 —— 包含信号签名、线程设置和 ChartPanel 集成的完整代码模板）
2. 将 worker 信号连接到 `ChartPanel` 中处理缓冲区管理（MAX_POINTS 截断）和 X 轴范围的分发方法
3. 移除 `ChartPanel.__init__()` 中的 `QTimer(500ms)`（第 322 行）—— 替换为 `QThread + moveToThread` 推送模型
4. 将 Start/Stop 按钮（main_window.py 第 205-208 行）连接到 `worker.start_acquisition()` / `worker.stop_acquisition()`
5. 将 `MainWindow._append_log(msg)`（第 287 行）连接到硬件状态事件（`SensorWorker.status_changed` / `error_occurred`）

**如果将光谱仪替换为温度传感器：** 创建新的数据生成器，发出逼真的温度信号（环境温度约 25°C，随机游走漂移约 0.01°C/s，高斯噪声约 0.05°C）。对于压力：典型范围 0-100 kPa，慢速漂移和高频噪声。参见第 4 步 DataSimulator 部分以了解需要替换的精确信号公式。

### 添加新图表

1. 遵循 `SpectrumChart` 模式子类化 `pg.PlotWidget`：init 时创建 pen、`refresh_color()`、`update_data()`。参见第 4 步的图表类样板代码分解，了解强制、可配置和可选代码部分。
2. 添加相应的颜色角色 + 选择器行 + DEFAULTS 条目（参见上文）
3. 添加到 `ChartPanel` splitter（第 299-306 行），如需要链接 X 轴，添加 `DraggableLabel`
   - **3a.** 将新图表的键添加到 `ChartPanel.apply_label_positions()`（当前在 plot_widgets.py 第 344-361 行检查 "spectrum"、"trend"、"sourcemeter"），以便在启动时恢复已保存的标签位置
4. 在 `settings_manager.DEFAULTS["chart_labels"]` 中添加 `chart_labels` 默认位置
5. 连接标签 `pos_changed` → `MainWindow._save_chart_labels`（扩展第 84-91 行的发送者身份检查）。**警告：** `_save_chart_labels` 使用 `self.sender()`，仅在信号调用时有效，直接调用无效。参见第 3 步图表标签保存部分了解重构后的 `functools.partial` 模式。
6. 扩展 `MainWindow._save_chart_labels` 添加新的发送者检查

> **添加/删除图表时：** 图表标签键（"spectrum"、"trend"、"sourcemeter"）在 3 个文件的 **4 个不同位置** 硬编码：
> - `settings_manager.py` DEFAULTS `chart_labels`（第 50-54 行）
> - `plot_widgets.py` `ChartPanel.apply_label_positions()`（第 344-361 行）
> - `main_window.py` `_save_chart_labels()`（第 84-89 行）
> - `main_window.py` 信号连接（第 124-126 行）
>
> 所有 4 个位置必须同时更新。缺少任意一个会导致已保存的标签位置在启动时静默无法恢复（无错误，只是标签弹回默认位置）。X 轴链接依赖关系见第 4 步的图表拓扑图。

### 更改参数控件

> **警告：** 参数控件在 **5 个不同代码位置** 之间紧密耦合。更改参数面板需要同时编辑全部 5 个位置 —— 缺少任意一个会导致静默数据丢失（参数值跨重启丢失，无崩溃或错误）：

| 控件 | `_build_param_panel()` | `DEFAULTS["params"]` | `_apply_loaded_params()` | `_connect_param_signals()` | `_save()` |
|--------|------------------------|---------------------|--------------------------|---------------------------|-----------|
| `self._si` | 第 180 行 | `"integration_ms"` 第 42 行 | 第 60 行 | 第 74 行 | 第 265 行 |
| `self._sa` | 第 181 行 | `"averages"` 第 43 行 | 第 61 行 | 第 75 行 | 第 266 行 |
| `self._sw` | 第 182 行 | `"monitor_wl"` 第 44 行 | 第 62 行 | 第 76 行 | 第 267 行 |
| `self._mc` | 第 190 行 | `"source_type"` 第 45 行 | 第 63 行 | 第 77 行 | 第 268 行 |
| `self._mv` | 第 191 行 | `"source_value"` 第 46 行 | 第 64 行 | 第 78 行 | 第 269 行 |
| `self._mn` | 第 192 行 | `"nplc"` 第 47 行 | 第 65 行 | 第 79 行 | 第 270 行 |
| `self._sr` | 第 200 行 | `"sample_rate"` 第 48 行 | 第 66 行 | 第 80 行 | 第 271 行 |

步骤：
1. 在 `_build_param_panel()` 中添加/删除控件（main_window.py 第 170-212 行）
2. 在 `DEFAULTS["params"]` 中更新新键（settings_manager.py 第 41-49 行）
3. 更新 `_apply_loaded_params()` 以读写新键（main_window.py 第 58-66 行）
4. 更新 `_connect_param_signals()` 将新控件连接到 `_save`（第 68-80 行）
5. 更新 `_save()` 以序列化新控件值（第 264-272 行）

### 参数面板设计原则

将参数面板适配到新的传感器领域（温度、压力、湿度等）时：

**控件类型选择：**

| 参数语义 | 推荐控件 | 示例 |
|---------------------|--------------------|--------|
| 具有已知工作范围的连续物理量 | `QDoubleSpinBox` 带后缀单位 | `self._temp = QDoubleSpinBox(); self._temp.setSuffix(" °C")` |
| 整数计数/迭代次数 | `QSpinBox` | `self._scans = QSpinBox(); self._scans.setRange(1, 1000)` |
| 恰好 N 个选项的离散模式 | `QComboBox` | `self._unit = QComboBox(); self._unit.addItems(["Celsius", "Fahrenheit", "Kelvin"])` |
| 布尔开/关 | `QCheckBox` | `self._enable_alarm = QCheckBox("Enable Alarm")` |
| 粗略视觉调整 | `QSlider` + 配套 `QLabel` | 此模板中当前未使用 |

**范围和默认值启发式方法：**
- 从数据表限制推导范围（工作范围/绝对最大额定值），添加 5-10% 安全边距
- 选择代表安全空闲状态的默认值 —— 非零，非最大
- 添加后缀单位使 UI 自文档化（`°C`、`bar`、`%RH`、`kPa`）
- 将相关参数分组到单独的 `QGroupBox` 标签下（如 "Temperature"、"Pressure"、"Alarms"）

**完整示例 — 通用传感器监控应用：**

```python
# settings_manager.py — 温度和压力的 DEFAULTS["params"]
"params": {
    "temp_sample_rate": 1.0,       # Hz
    "temp_alarm_high": 80.0,       # °C
    "temp_alarm_low": -10.0,       # °C
    "pressure_unit": 0,            # 下拉索引：0=bar，1=psi，2=kPa
    "pressure_range_max": 10.0,    # bar
    "log_interval": 5.0,           # 日志写入间隔秒数
},

# main_window.py — _build_param_panel() 摘录
tg = QGroupBox("Temperature")
tf = QFormLayout(tg)
self._temp_rate = QDoubleSpinBox(); self._temp_rate.setRange(0.1, 100)
self._temp_rate.setSuffix(" Hz")
tf.addRow("Sample Rate:", self._temp_rate)
self._temp_high = QDoubleSpinBox(); self._temp_high.setRange(-50, 500)
self._temp_high.setSuffix(" °C")
tf.addRow("Alarm High:", self._temp_high)
# ... 等等
```

五个更新点（build_panel、DEFAULTS、apply_loaded_params、connect_signals、_save）保持相同的机械模式 —— 只有控件类型、范围和语义变化。

### 自定义默认调色板

仅编辑**两个位置**（而非三个 —— 重置按钮应在运行时从 `DEFAULTS["colors"]` 读取）：

1. `ColorScheme` 类属性（color_scheme.py 第 19-37 行）
2. `settings_manager.DEFAULTS["colors"]`（第 29-40 行）

**对于重置按钮：** 重构 `ColorPanel._reset()` 使其在运行时从 `settings_manager.DEFAULTS["colors"]` 读取，而非维护默认值的第三个独立副本。当前 `_reset()` 在 color_panel.py 第 139-143 行硬编码了第三个副本。如果 DEFAULTS 和 ColorScheme 属性已更新但忘记此第三个副本，重置按钮将静默恢复到过时的错误颜色。最简单的修复：

```python
def _reset(self):
    from settings_manager import DEFAULTS
    for r, c in DEFAULTS["colors"].items():
        ColorScheme.set_color(r, c)
        self._pickers[r].set_color(c)
        self.color_changed.emit(r, c)
```

**注意：** 这需要先修复 `load_settings()` 返回 `DEFAULTS.copy()` 而非引用形式的 `DEFAULTS`（参见设置持久化 — 已知问题 #1）。否则 `DEFAULTS["colors"]` 在首次保存时被静默覆盖为用户颜色，重置按钮恢复用户颜色而非出厂默认值。

---

## 集成清单 — 启动新项目

1. 将所有 5 个 `.py` 文件复制到新项目目录
2. 删除任何现有的 `settings.json`（它会自动以默认值生成）
3. 在 `color_scheme.py` 中：将 `SPECTRUM`、`TREND`、`RESISTANCE` 重命名/重新着色为你的领域。更新 `ROLES_CHART` 列表。根据需要添加/删除图表颜色角色
4. 在 `color_panel.py` 中：更新 `_init_ui()` 中的角色-标签对（第 98-126 行）和 `_reset()` 中的默认值（第 139-143 行）
5. 在 `settings_manager.py` 中：更新 `DEFAULTS["colors"]` 和 `DEFAULTS["params"]` 以匹配你的硬件。控件类型和范围指导参见参数面板设计原则部分。
6. 在 `plot_widgets.py` 中：将 `DataSimulator` 替换为你的信号源。更新坐标轴标签、`DraggableLabel` 文本、曲线数量以及 `apply_label_positions` 键。添加或删除图表前参见第 4 步的图表拓扑部分。
7. 在 `main_window.py` 中：更新窗口标题（第 25 行）、状态栏消息（第 285 行）、日志面板占位文本（第 141 行）、参数 GroupBox 标签/范围、切换按钮工具提示。将 Start/Stop/Save 按钮连接到你的硬件控制器
8. 应用你自己的默认调色板（编辑上述"自定义默认调色板"中的两个位置）
9. 运行一致性检查（来自设计理念部分）
10. 测试：更改颜色 → 验证 QSS 全局更新。更改参数 → 验证 `settings.json` 出现。重启 → 验证所有设置恢复
11. 删除 `settings.json` → 重启 → 验证默认值从 `DEFAULTS` 字典重新出现

---

## 性能清单

- [ ] `QApplication.instance().setStyleSheet()` 仅在颜色更改时调用（不在定时器上）
- [ ] `pg.mkPen()` / `pg.mkBrush()` 仅在 `refresh_color()` 中（不在 `update_data()` 中）
- [ ] 所有图表使用 `enableAutoRange()`（非 `disableAutoRange()`）
- [ ] 最大数据点数 <= 1500（当前：1400 spectrum、1000 trend、1000 sourcemeter）
- [ ] 定时器间隔 >= 400ms（当前：500ms）
- [ ] 滚动图表每次 tick 仅添加 2 个数据点
- [ ] 抗锯齿关闭（`pg.setConfigOption("antialias", False)` — 第 17 行）
- [ ] Spectrum 每 5 个 tick 节流（第 368 行）。**原理：** Spectrum 每次更新生成 1400 个点，而滚动图表仅 2 个点。对每次更新点数超过约 500 的图表进行节流。
- [ ] Spectrum 首帧立即渲染（第 368 行的 `_data_counter <= 1` 条件）
