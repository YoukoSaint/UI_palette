# -*- coding: utf-8 -*-
"""实时光谱与趋势图表（pyqtgraph + 模拟数据）"""
import math
import random
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer
from color_scheme import ColorScheme, hex_to_rgba


def _apply_pg_theme():
    pg.setConfigOption("background", ColorScheme.DARK)
    pg.setConfigOption("foreground", ColorScheme.TEXT)
    pg.setConfigOption("antialias", False)
    pg.setConfigOptions(useOpenGL=False, leftButtonPan=False)


class SpectrumChart(pg.PlotWidget):
    """图 1 — 光谱曲线 + 同色半透明填充"""

    def __init__(self):
        super().__init__()
        self.setLabel("bottom", "Wavelength (nm)")
        self.setLabel("left", "Intensity")
        self.setTitle("Spectrum")
        self.showGrid(x=True, y=True, alpha=0.4)
        self._curve = self.plot([], [], pen=pg.mkPen(ColorScheme.SPECTRUM, width=2.2))
        self.enableAutoRange()

    def _apply_fill(self):
        c = ColorScheme.SPECTRUM
        r, g, b, a = hex_to_rgba(c, 60)
        self._curve.setFillBrush(pg.mkBrush(r, g, b, a))
        self._curve.setFillLevel(0)

    def refresh_color(self):
        self._curve.setPen(pg.mkPen(ColorScheme.SPECTRUM, width=2.2))
        self._apply_fill()

    def update_spectrum(self, wl, spec):
        self._curve.setData(wl, spec)
        self._apply_fill()
        self.autoRange()


class TrendChart(pg.PlotWidget):
    """图 2 — 波段强度趋势"""

    MAX_POINTS = 1000

    def __init__(self):
        super().__init__()
        self.setLabel("bottom", "Time (s)")
        self.setLabel("left", "Intensity")
        self.setTitle("Band Intensity Trend")
        self.showGrid(x=True, y=True, alpha=0.4)
        self._curve = self.plot(
            [], [], pen=pg.mkPen(ColorScheme.TREND, width=2),
            symbol="o", symbolSize=3,
            symbolBrush=ColorScheme.TREND, symbolPen=pg.mkPen(None),
        )
        self.enableAutoRange()

    def refresh_color(self):
        c = ColorScheme.TREND
        self._curve.setPen(pg.mkPen(c, width=2))
        self._curve.setSymbolBrush(c)

    def update_data(self, times, values):
        self._curve.setData(times, values)


class SourceMeterChart(pg.PlotWidget):
    """图 3 — 电阻"""

    MAX_POINTS = 1000

    def __init__(self):
        super().__init__()
        self.setLabel("bottom", "Time (s)")
        self.setLabel("left", "Resistance (Ω)")
        self.setTitle("SourceMeter Readings")
        self.showGrid(x=True, y=True, alpha=0.4)
        self._r = self.plot(
            [], [], pen=pg.mkPen(ColorScheme.RESISTANCE, width=2.2),
            name="Resistance (Ω)", connect="finite",
        )
        self.enableAutoRange()

    def refresh_color(self):
        self._r.setPen(pg.mkPen(ColorScheme.RESISTANCE, width=2.2))

    def update_data(self, times, r):
        self._r.setData(times, r)


class DataSimulator:
    @staticmethod
    def spectrum(wavelengths=None):
        if wavelengths is None:
            wavelengths = [300 + i * 0.5 for i in range(1400)]
        spec = []
        for wl in wavelengths:
            val = (800 * math.exp(-0.5 * ((wl - 450) / 30) ** 2) +
                   500 * math.exp(-0.5 * ((wl - 550) / 25) ** 2) +
                   300 * math.exp(-0.5 * ((wl - 680) / 20) ** 2) +
                   random.gauss(0, 15))
            spec.append(max(0, val))
        return wavelengths, spec

    @staticmethod
    def trend(n_points):
        times = [i * 0.1 for i in range(n_points)]
        values = []
        for t in times:
            v = 500 + 200 * math.sin(t * 0.5) * math.exp(-t * 0.01)
            values.append(v + random.gauss(0, 10))
        return times, values

    @staticmethod
    def sourcemeter(n_points):
        times = [i * 0.05 for i in range(n_points)]
        r = []
        for t in times:
            vt = 5.0 + 0.1 * math.sin(t * 2)
            ct = 0.003 + 0.0002 * math.cos(t * 3)
            r.append(vt / ct if ct != 0 else float("nan"))
        return times, r


class ChartPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = pg.QtWidgets.QSplitter(pg.QtCore.Qt.Vertical)
        self.spectrum = SpectrumChart()
        self.trend = TrendChart()
        self.sourcemeter = SourceMeterChart()
        splitter.addWidget(self.spectrum)
        splitter.addWidget(self.trend)
        splitter.addWidget(self.sourcemeter)
        layout.addWidget(splitter)

        self._data_counter = 0
        self._wl_cache = None
        self._times, self._trend_vals = [], []
        self._t2, self._r = [], []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

    def _tick(self):
        self._data_counter += 1
        start_t = self._data_counter * 0.5

        # 光谱 — 首帧立即显示，之后每 5 帧 (~2.5s) 更新
        if self._data_counter <= 1 or self._data_counter % 5 == 0:
            wl, spec = DataSimulator.spectrum(self._wl_cache)
            if self._wl_cache is None:
                self._wl_cache = wl
            self.spectrum.update_spectrum(self._wl_cache, spec)

        # 趋势 — 加 2 点
        t, v = DataSimulator.trend(2)
        for i in range(2):
            self._times.append(start_t + t[i])
            self._trend_vals.append(v[i])
        if len(self._times) > self.trend.MAX_POINTS:
            cut = len(self._times) - self.trend.MAX_POINTS
            self._times = self._times[cut:]
            self._trend_vals = self._trend_vals[cut:]
        self.trend.update_data(self._times, self._trend_vals)
        if self._times:
            self.trend.setXRange(max(0, self._times[-1] - 60), self._times[-1] + 5)

        # 源表 — 加 2 点
        t2, rt = DataSimulator.sourcemeter(2)
        for i in range(2):
            self._t2.append(start_t + t2[i])
            self._r.append(rt[i])
        if len(self._t2) > self.sourcemeter.MAX_POINTS:
            cut = len(self._t2) - self.sourcemeter.MAX_POINTS
            self._t2 = self._t2[cut:]
            self._r = self._r[cut:]
        self.sourcemeter.update_data(self._t2, self._r)
        if self._t2:
            self.sourcemeter.setXRange(max(0, self._t2[-1] - 60), self._t2[-1] + 5)

    def refresh_colors(self):
        _apply_pg_theme()
        for ch in [self.spectrum, self.trend, self.sourcemeter]:
            ch.setBackground(ColorScheme.DARK)
        self.spectrum.refresh_color()
        self.trend.refresh_color()
        self.sourcemeter.refresh_color()
