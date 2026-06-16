# UI Palette

一个用户可自定义的动态颜色主题系统，基于 PyQt5 —— 10 个独立可编辑的颜色角色、实时 pyqtgraph 图表以及持久化设置。

## 快速开始

```bash
git clone https://github.com/YoukoSaint/UI_palette.git
cd UI_palette
pip install pyqt5 pyqtgraph
python main_window.py
```
需要 Python 3.6+。无需数据库 —— `settings.json` 会在首次保存时自动生成。

## 架构

```
ColorScheme（类属性 —— 唯一真相源，零 PyQt 导入）
  ├─ get_stylesheet() ──→ QApplication.setStyleSheet()   ← QSS（覆盖所有控件）
  └─ hex_to_rgba()    ──→ pg.mkPen() / pg.mkBrush()      ← 图表画笔/画刷

运行时流程（每次颜色变更共 4 步）：
  ColorPanel 选择器 ──→ ColorScheme.set_color(role, hex)
    ──→ get_stylesheet() → QApplication.instance().setStyleSheet()  ⚠ 不是 QMainWindow
    ──→ ChartPanel.refresh_colors() → _apply_pg_theme() + 逐图表 pen/brush/fill/label
    ──→ MainWindow._save() → 完整快照写入 settings.json
```

## 文件

| 文件 | 职责 |
|------|------|
| `color_scheme.py` | 颜色注册表（10 个类属性）、QSS 生成器、`hex_to_rgba()`。零 Qt 导入 —— 根依赖。 |
| `color_panel.py` | 170px 右侧边栏：10 个 `ColorPickerRow` 控件，分为 3 个区域 + 重置按钮。 |
| `plot_widgets.py` | 3 个 pyqtgraph 图表、`DraggableLabel`、`DataSimulator`、`ChartPanel` 容器 + 定时器。 |
| `main_window.py` | 应用入口、完整布局、参数面板、面板切换、设置编排。 |
| `settings_manager.py` | JSON 持久化：带深度合并的保存/加载、冻结 exe 路径解析。 |

## 颜色系统

**5 个基础颜色**（TEXT、LIGHT、DARK、LINE、BTN）通过 `get_stylesheet()` 驱动所有 QSS。**3 个图表曲线**角色（SPECTRUM、TREND、RESISTANCE）驱动图表画笔、填充和 DraggableLabel 文本。**2 个图表显示**角色（GRID、AXIS）驱动网格线和坐标轴样式 —— 两者均可在颜色面板中由用户编辑。

六个派生颜色由 `_adjust(hex, amount)` 内联计算，该函数对 RGB 各分量加上一个有符号整数：

| 派生色 | 公式 | 控制范围 |
|---------|---------|----------|
| `text2` | `_adjust(TEXT, -30)` | QLabel、QPlainTextEdit、QStatusBar 文本 |
| `text3` | `_adjust(TEXT, -50)` | QPushButton:disabled 文本 |
| `dark2` | `_adjust(DARK, -6)` | QMainWindow、QLineEdit、QSpinBox、QComboBox 背景 |
| `light2` | `_adjust(LIGHT, +10)` | （已定义但当前 QSS 中未使用 —— 保留供将来使用） |
| `accent` | `_adjust(LIGHT, +30)` | GroupBox 标题、焦点边框、splitter/scrollbar 悬停 |
| `btn_hover` | `_adjust(BTN, +10)` | QPushButton:hover 背景 |

`ColorScheme` 上的三个可调常量：`LABEL_SIZE=14`（图表标签字体像素）、`LABEL_ALPHA="ff"`（标签背景不透明度 —— 十六进制字符串，运行时通过 `int(..., 16)` 解析得到 0–255）、`AXIS_LABEL_SIZE=13`（坐标轴刻度字体像素）。

## 颜色角色参考

| 角色 | 默认值 | 类别 | 控制范围 |
|------|---------|----------|----------|
| `TEXT` | `#c0caf5` | 基础 | 前景文本、状态栏、图表前景、标签、输入框 |
| `LIGHT` | `#1e1f2e` | 基础 | GroupBox 背景、QComboBox 下拉、ScrollBar、禁用按钮 |
| `DARK` | `#1a1b26` | 基础 | QWidget/QMainWindow 背景、pyqtgraph 图表背景 |
| `LINE` | `#3b3d56` | 基础 | GroupBox、QLineEdit、SpinBox、ComboBox、Splitter、ScrollBar 边框 |
| `BTN` | `#3b3d56` | 基础 | QPushButton 背景/边框（默认同 `LINE`；拆分以便独立控制 —— 更改 LINE 不会自动更新 BTN） |
| `SPECTRUM` | `#0db9d7` | 图表曲线 | Spectrum 线条（宽度 2.2）+ 填充（alpha 60）+ DraggableLabel 文本 |
| `TREND` | `#bb9af7` | 图表曲线 | Trend 线条（宽度 2）+ 符号画刷（大小 3）+ DraggableLabel 文本 |
| `RESISTANCE` | `#f7768e` | 图表曲线 | SourceMeter 线条（宽度 2.2，`connect="finite"`）+ DraggableLabel 文本 |
| `GRID` | `#2c2d3f` | 图表显示 | 图表网格线（alpha 0.4） |
| `AXIS` | `#565f89` | 图表显示 | 坐标轴线画笔 + 刻度标签画笔 |

## 功能特性

- **动态主题：** 所有控件通过应用于 `QApplication` 的单个 `get_stylesheet()` 字符串从当前 `ColorScheme` 值重新样式化。覆盖 QMainWindow、QWidget、QLabel、QGroupBox、QPushButton（包括 `:hover`、`:pressed`、`:disabled` 伪状态）、QLineEdit、QSpinBox、QDoubleSpinBox、QComboBox、QSplitter、QPlainTextEdit、QStatusBar、QScrollBar（垂直 + 水平，箭头按钮通过 `height:0; border:none` 隐藏）。任何颜色更改都会即时传播到所有控件和全部 3 个图表。
- **颜色面板：** 170px 右侧边栏。3 个带标签的区域 —— "Base Colors"（5 行）、"Chart Curves"（3 行）、"Chart Display"（2 行）。每行包含：10×10 色块（边框 `#555`，独立于主题）、28px 角色标签、64px 十六进制 QLineEdit（回车应用，无效时红色边框）、18px `QColorDialog` 选择器按钮。重置按钮从 `settings_manager.DEFAULTS["colors"]` 恢复全部 10 个默认值。**BTN** 默认值与 LINE 相同 —— 用户应同时更新两者以保持按钮边框一致；关于耦合的说明请参阅 REPRODUCE_zh.md。
- **可折叠面板：** 左侧（300px 参数）、右侧（170px 颜色）、底部（150px 日志）。面板之间放置 12×30px 的箭头切换按钮。可见性持久化为 `"panels": {"left": bool, "right": bool, "log": bool}` —— 由 `setdefault` 添加的运行时键，不在 DEFAULTS 中。**注意：** 切换按钮使用硬编码颜色（`#606060` / `#c0c0c0`），绕过动态主题。这是已知限制 —— 无论所选主题如何，它们始终保持视觉稳定。
- **参数设置：** 7 个硬件参数，分 3 个 GroupBox —— Spectrometer（integration_ms 1–60000、averages 2–100、monitor_wl 0–10000）、SourceMeter（source_type 下拉 Voltage/Current、source_value -100–100、nplc 0.01–10）、Acquisition（sample_rate 0.01–1000 Hz）。**注意：** `sample_rate` 是用户可见的参考/硬件配置参数 —— 它不会动态控制模拟器定时器间隔（固定为 500ms）。孤立的 Start/Stop/Save 按钮具有用于硬编码 QSS 样式（绿/红/蓝，绕过动态主题）的 `objectName` 选择器，但没有 `clicked` 连接 —— 是硬件控制的自然接入点。
- **三个图表：** 垂直 `QSplitter` 堆叠。`SpectrumChart` —— 自动范围、半透明填充（`hex_to_rgba(SPECTRUM, 60)`）、每 5 个 tick 节流（第一帧立即渲染；原理：1400 个数据点 vs. 滚动图表的 2 个点 —— 每 5 个 tick 节流以避免饱和 Qt 事件循环）。`TrendChart` —— 1000 点滚动缓冲区、符号标记、通过 `setXLink` 链接 X 轴到 SourceMeter、底部轴隐藏。`SourceMeterChart` —— 1000 点缓冲区、`connect="finite"`、驱动共享 X 轴，60 秒滚动窗口。Y 轴宽度在首次显示时通过延迟的 `QTimer.singleShot(0, ...)` 统一。**注意：** 持有三个图表的 QSplitter 是局部变量（未存储为 `self._splitter`），因此分割器手柄位置不会跨重启持久化 —— 用户每次会话需重新拖动手柄。
- **可拖动标签：** 每图表一个 `DraggableLabel`（QLabel 子类）。拖动任意位置移动；右下角 20×20 区域调整大小（最小 40×20）。每次调整大小时自动缩放字体 `max(8, height * 0.72)`。背景由 `ColorScheme.LIGHT` RGB + `LABEL_ALPHA` 不透明度组成，边框来自 `ColorScheme.LINE`，文本颜色来自曲线颜色。位置/大小在鼠标释放时持久化到 `chart_labels` 键。
- **数据模拟器：** `DataSimulator` 静态方法 —— 3 个高斯峰（450nm sigma=30 amp=800、550nm sigma=25 amp=500、680nm sigma=20 amp=300）带噪声 `gauss(0,15)`、阻尼正弦 `500+200*sin(t*0.5)*exp(-t*0.01)` 带噪声 `gauss(0,10)`、V/I 电阻 `V=5+0.1*sin(2t)`、`I=0.003+0.0002*cos(3t)` 且在 I=0 时为 NaN。`QTimer` 每 500ms，每次 2 个点。**替换为真实硬件信号**（参见 REPRODUCE_zh.md）。
- **设置持久化：** `settings.json` 位于源码旁（或在冻结为 `.exe` 时位于 `sys.executable` 旁，而非 `sys._MEIPASS` —— 参见 REPRODUCE_zh.md 关键陷阱 #7）。每次更改时完整快照：10 个颜色、7 个参数、3 个面板布尔值、3 个标签位置。加载时深度合并 —— 逐子字典浅合并，因此缺失的键获得默认值，未知键得以保留。**警告：** 在文件缺失/找不到时，`load_settings()` 返回模块级 `DEFAULTS` 字典**按引用**（而非副本）。对返回字典的任何后续修改都会破坏全局常量 —— 完整说明和缓解措施见 REPRODUCE_zh.md。
- **键盘：** `F10` 全屏，`Escape` 恢复正常。

## 关键设计决策

| 决策 | 理由 |
|----------|-----------|
| 颜色使用类属性（而非字典） | `ColorScheme.TEXT` 语法可直接在 QSS 的 f-string 中使用 |
| `get_stylesheet()` 为函数（而非文件） | 每次调用重新读取 `ColorScheme` 属性 —— 始终反映当前状态 |
| Pen/brush 在 `__init__` 创建，`refresh_color()` 中重建 | 主题更改很少发生；`update_data()` 是热路径 —— 那里不做分配 |
| 面板间放置带切换按钮的 `QHBoxLayout` | 切换位于面板和内容之间的接缝处，而非两者内部 |
| 冻结 exe 设置路径使用 `sys.executable` | `sys._MEIPASS` 是临时只读目录，退出时删除 |
| 信号连接在参数恢复之后 | 防止 `_apply_loaded_params()` 触发多余的 `_save()` |
| QSS 最后应用（在所有控件 + 参数 + 信号之后） | 控件构造可能设置内联样式，会覆盖主题 |
| 每图表数据使用 PyQt5 `pyqtSignal(dict)` | 信号驱动架构替代定时器轮询以适配真实硬件 —— 参见 REPRODUCE_zh.md |

## 窗口和 UI 默认值

| 设置 | 值 | 位置 |
|---------|-------|----------|
| 窗口标题 | "OptoSync — Synchronized Acquisition System" | `main_window.py` 第 25 行 |
| 默认大小 | 1440×920 | `main_window.py` 第 26 行 |
| 最小大小 | 1100×700 | `main_window.py` 第 27 行 |
| 日志面板缓冲区 | 最多 500 行（`setMaximumBlockCount`） | `main_window.py` 第 140 行 |
| 日志占位文本 | "Log output — demo mode" | `main_window.py` 第 141 行 |
| 状态栏消息 | "Ready — Demo Mode \| Simulated data" | `main_window.py` 第 285 行 |

## 故障排除

| 症状 | 原因 | 修复 |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'PyQt5'` | 缺少依赖 | `pip install pyqt5 pyqtgraph` |
| 启动时图表空白 | pyqtgraph 主题未应用，或图表背景不匹配 | 验证在 `refresh_colors()` 之前调用了 `_apply_pg_theme()` |
| 重启后设置丢失 | 冻结 exe 写入 `sys._MEIPASS`（临时/只读） | 验证 `_get_settings_dir()` 使用 `sys.executable` |
| 重启后设置丢失 | 目录写入权限 | 检查包含 `settings.json` 的目录是否可写 |
| 自定义设置未应用（应用使用默认值或启动崩溃） | 手动编辑的 `settings.json` 有 JSON 语法错误（如尾随逗号）或值类型不正确 | 当 JSON 无法解析时，应用安全地回退到默认值 —— 数据未丢失，只是未应用。首先验证并修复 JSON（使用 `python -m json.tool settings.json`）。如无法恢复，重命名为 `settings.json.bak`（不要删除 —— 颜色、参数和标签位置得以保留）。下次启动时重新生成默认值。手动将 `.bak` 文件中的值复制回新的 settings.json。 |
| `QWidget: Must construct a QApplication...` | QWidget 在 `QApplication()` 之前实例化 | 确保 `QApplication(sys.argv)` 在 `__main__` 中首先运行 |
| 选择器中初始颜色错误 | `_apply_loaded_colors()` 在 `ColorPanel` 构造之后调用 | 颜色必须在 `_setup_ui()` 创建面板之前恢复 |
| 重启后分割器手柄位置丢失 | QSplitter 是局部变量，未存储为实例属性（plot_widgets.py 第 299 行） | 已知限制 —— 重启后重新拖动手柄。结构原因见 REPRODUCE_zh.md。 |

## 许可证

MIT

---

关于逐步集成到新 PyQt5 项目的说明，请参阅 **REPRODUCE_zh.md**。
关于完整的设置 JSON 模式和保存/加载合并逻辑，请参阅 **REPRODUCE_zh.md**。
关于扩展点清单（添加颜色、替换模拟器、连接硬件），请参阅 **REPRODUCE_zh.md**。
