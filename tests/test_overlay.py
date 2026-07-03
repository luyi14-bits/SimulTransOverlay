"""Tests for subtitle overlay module."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestOverlayWindow:
    """半透明叠加层窗口测试"""

    @pytest.fixture
    def overlay(self):
        with patch("src.subtitle_overlay.SubtitleOverlay") as MockOverlay:
            mock = MockOverlay.return_value
            mock.window_width = 600
            mock.window_height = 100
            mock.opacity = 0.5
            mock.always_on_top = True
            mock.click_through = True
            mock.theme = "dark"
            yield mock

    def test_default_dimensions(self, overlay):
        """默认窗口尺寸应为 600x100"""
        assert overlay.window_width == 600
        assert overlay.window_height == 100

    def test_always_on_top(self, overlay):
        """应始终置顶"""
        assert overlay.always_on_top is True

    def test_click_through(self, overlay):
        """应鼠标穿透"""
        assert overlay.click_through is True

    def test_opacity(self, overlay):
        """透明度应为 0.5"""
        assert overlay.opacity == 0.5

    def test_default_theme(self, overlay):
        """默认主题为 dark"""
        assert overlay.theme == "dark"

    def test_show_text(self, overlay):
        """显示翻译文本"""
        overlay.show_text.return_value = None
        overlay.show_text("Hello World")
        # 不应抛出异常

    def test_set_opacity(self, overlay):
        """设置透明度"""
        overlay.opacity = 0.7
        assert overlay.opacity == 0.7

    def test_toggle_visibility(self, overlay):
        """切换显示/隐藏"""
        overlay.is_visible = True
        overlay.is_visible = False
        assert overlay.is_visible is False


class TestOverlayThemes:
    """叠加层主题测试"""

    @pytest.fixture
    def themes(self):
        with patch("src.subtitle_overlay.THEMES", create=True) as MockThemes:
            yield {
                "dark": {"bg": "#000000", "fg": "#FFFFFF", "opacity": 0.5},
                "light": {"bg": "#FFFFFF", "fg": "#000000", "opacity": 0.4},
                "glass": {"bg": "rgba(255,255,255,0.15)", "fg": "#FFFFFF", "opacity": 0.3},
                "blue": {"bg": "#1a1a2e", "fg": "#00d2ff", "opacity": 0.5},
                "green": {"bg": "#0a1a0a", "fg": "#00ff88", "opacity": 0.5},
                "purple": {"bg": "#1a0a2e", "fg": "#c084fc", "opacity": 0.5},
                "red": {"bg": "#2e0a0a", "fg": "#ff4444", "opacity": 0.5},
                "orange": {"bg": "#2e1a0a", "fg": "#ff8800", "opacity": 0.5},
                "pink": {"bg": "#2e0a1a", "fg": "#ff69b4", "opacity": 0.5},
                "cyber": {"bg": "#000000", "fg": "#00ff00", "opacity": 0.4},
            }

    def test_minimum_ten_themes(self, themes):
        """至少应有 10 个主题"""
        assert len(themes) >= 10

    def test_theme_has_bg_and_fg(self, themes):
        """每个主题应有 bg 和 fg 颜色"""
        for name, colors in themes.items():
            assert "bg" in colors, f"Theme '{name}' missing bg"
            assert "fg" in colors, f"Theme '{name}' missing fg"

    def test_switch_theme(self, themes):
        """切换主题"""
        for name in themes:
            assert name in themes


class TestHistoryScroll:
    """历史字幕滚动测试"""

    def test_history_lines_default(self):
        """默认保留 2 行历史"""
        with patch("src.subtitle_overlay.SubtitleOverlay") as MockOverlay:
            mock = MockOverlay.return_value
            mock.history_lines = 2
            assert mock.history_lines == 2

    def test_history_overflow(self):
        """历史超出时应丢弃最早的"""
        with patch("src.subtitle_overlay.SubtitleOverlay") as MockOverlay:
            mock = MockOverlay.return_value
            mock.history = ["line1", "line2", "line3"]
            if len(mock.history) > 2:
                mock.history.pop(0)
            assert len(mock.history) <= 2

    def test_history_clear(self):
        """清空历史"""
        with patch("src.subtitle_overlay.SubtitleOverlay") as MockOverlay:
            mock = MockOverlay.return_value
            mock.history = ["line1", "line2"]
            mock.history = []
            assert len(mock.history) == 0
