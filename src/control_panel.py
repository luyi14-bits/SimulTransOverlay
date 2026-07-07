"""Control panel dialog with 5 configuration tabs.

Provides a GUI for modifying settings that would otherwise
require manual editing of config.yaml.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QDialog, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSlider, QSpinBox, QCheckBox, QPushButton,
    QWidget, QGroupBox, QFormLayout, QTextEdit, QFileDialog,
    QMessageBox,
)

logger = logging.getLogger(__name__)


def _get_config_path() -> Path:
    """Get config.yaml path, PyInstaller-compatible."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "config" / "config.yaml"


class ControlPanel(QDialog):
    """Settings dialog with 5 configuration tabs."""

    config_saved = pyqtSignal()

    def __init__(self, config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self._config = config or {}
        self.setWindowTitle("SimulTransOverlay — 设置")
        self.setMinimumSize(520, 400)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._add_audio_tab()
        self._add_asr_tab()
        self._add_translation_tab()
        self._add_overlay_tab()
        self._add_about_tab()

        # Close button at bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    # ───────── Tab 1: Audio ─────────
    def _add_audio_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        device_box = QGroupBox("音频设备")
        d_layout = QFormLayout(device_box)
        self.device_combo = QComboBox()

        # Populate devices
        try:
            from src.audio_capture import list_loopback_devices
            for dev in list_loopback_devices():
                self.device_combo.addItem(f"[{dev['index']}] {dev['name']}", dev["index"])
        except Exception:
            self.device_combo.addItem("(无法枚举设备)")
        d_layout.addRow("输出设备:", self.device_combo)

        self.mic_check = QCheckBox("混入麦克风输入")
        mic_val = self._config.get("audio", {}).get("mic_enabled", False)
        self.mic_check.setChecked(mic_val)
        d_layout.addRow(self.mic_check)

        form.addRow(device_box)
        self.tabs.addTab(tab, "音频")

    # ───────── Tab 2: ASR ─────────
    def _add_asr_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        asr_cfg = self._config.get("asr", {})

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["faster-whisper", "sensevoice"])
        self.engine_combo.setCurrentText(asr_cfg.get("engine", "faster-whisper"))
        form.addRow("引擎:", self.engine_combo)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText(asr_cfg.get("model", "base"))
        form.addRow("模型大小:", self.model_combo)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["auto (自动检测)", "ja (日本語)", "en (English)", "zh (中文)"])
        lang = asr_cfg.get("language", "auto")
        lang_map = {"auto": 0, "ja": 1, "en": 2, "zh": 3}
        self.lang_combo.setCurrentIndex(lang_map.get(lang, 0))
        form.addRow("语言:", self.lang_combo)

        self.tabs.addTab(tab, "ASR")

    # ───────── Tab 3: Translation ─────────
    def _add_translation_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        tr_cfg = self._config.get("translation", {})

        self.tr_engine_combo = QComboBox()
        self.tr_engine_combo.addItems(["builtin (离线翻译)", "ollama (需安装)", "deepseek (需API)"])
        eng = tr_cfg.get("engine", "builtin")
        eng_map = {"builtin": 0, "ollama": 1, "deepseek": 2}
        self.tr_engine_combo.setCurrentIndex(eng_map.get(eng, 0))
        form.addRow("翻译引擎:", self.tr_engine_combo)

        self.src_lang_combo = QComboBox()
        self.src_lang_combo.addItems(["auto", "ja", "en", "zh"])
        form.addRow("源语言:", self.src_lang_combo)

        self.tgt_lang_combo = QComboBox()
        self.tgt_lang_combo.addItems(["zh-CN", "en", "ja"])
        form.addRow("目标语言:", self.tgt_lang_combo)

        self.tabs.addTab(tab, "翻译")

    # ───────── Tab 4: Overlay ─────────
    def _add_overlay_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        ov_cfg = self._config.get("overlay", {})

        self.theme_combo = QComboBox()
        from src.subtitle_overlay import THEMES
        for name in THEMES:
            self.theme_combo.addItem(name)
        self.theme_combo.setCurrentText(ov_cfg.get("theme", "dark"))
        form.addRow("主题:", self.theme_combo)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(12, 72)
        self.font_spin.setValue(ov_cfg.get("font_size", 24))
        form.addRow("字体大小:", self.font_spin)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        opacity = int(ov_cfg.get("background_opacity", 0.5) * 100)
        self.opacity_slider.setValue(opacity)
        form.addRow("透明度:", self.opacity_slider)

        self.history_spin = QSpinBox()
        self.history_spin.setRange(0, 5)
        self.history_spin.setValue(ov_cfg.get("history_lines", 2))
        form.addRow("历史行数:", self.history_spin)

        self.tabs.addTab(tab, "叠加层")

    # ───────── Tab 5: About ─────────
    def _add_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QTextEdit()
        info.setReadOnly(True)
        info.setHtml("""
        <h2>SimulTransOverlay</h2>
        <p><b>版本：</b>v1.0.0</p>
        <p><b>许可证：</b>AGPL v3</p>
        <p><b>技术栈：</b>Python 3.12 + PyQt6 + faster-whisper + ctranslate2</p>
        <p><b>存储：</b>模型文件在首次运行时自动下载到 models/ 目录</p>
        <hr>
        <p>零外部依赖屏幕同传翻译工具。</p>
        <p>GitHub: <a href='https://github.com/luyi14-bits/SimulTransOverlay'>
        github.com/luyi14-bits/SimulTransOverlay</a></p>
        """)
        layout.addWidget(info)

        diag_btn = QPushButton("导出诊断信息")
        diag_btn.clicked.connect(self._export_diagnostics)
        layout.addWidget(diag_btn)

        self.tabs.addTab(tab, "关于")

    def _export_diagnostics(self):
        """Export logs + config as diagnostics.zip."""
        path, _ = QFileDialog.getSaveFileName(
            self, "保存诊断文件", "diagnostics.zip", "ZIP (*.zip)"
        )
        if path:
            import zipfile
            try:
                with zipfile.ZipFile(path, "w") as zf:
                    # Add config
                    config_path = _get_config_path()
                    if config_path.exists():
                        zf.write(config_path, "config.yaml")

                    # Add log files
                    log_dir = Path.home() / ".simultrans-overlay" / "logs"
                    if log_dir.exists():
                        for log_file in log_dir.glob("*.log"):
                            zf.write(log_file, f"logs/{log_file.name}")

                QMessageBox.information(self, "完成", f"诊断文件已保存到:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {e}")

    def get_settings(self) -> Dict[str, Any]:
        """Read current widget values into a config dict."""
        lang_map = {0: "auto", 1: "ja", 2: "en", 3: "zh"}
        return {
            "audio": {
                "device_name": self.device_combo.currentText(),
                "mic_enabled": self.mic_check.isChecked(),
            },
            "asr": {
                "engine": self.engine_combo.currentText(),
                "model": self.model_combo.currentText(),
                "language": lang_map.get(self.lang_combo.currentIndex(), "auto"),
            },
            "translation": {
                "engine": self.tr_engine_combo.currentText().split()[0],
                "source_language": self.src_lang_combo.currentText(),
                "target_language": self.tgt_lang_combo.currentText(),
            },
            "overlay": {
                "theme": self.theme_combo.currentText(),
                "font_size": self.font_spin.value(),
                "background_opacity": self.opacity_slider.value() / 100,
                "history_lines": self.history_spin.value(),
            },
        }
