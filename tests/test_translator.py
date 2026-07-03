"""Tests for translation engine module."""

import pytest
from unittest.mock import patch, MagicMock


class TestBuiltinTranslator:
    """内嵌翻译引擎测试"""

    def test_create_builtin_translator(self):
        """builtin 引擎应创建 BuiltinTranslator 实例"""
        with patch("src.translator.BuiltinTranslator") as MockBT:
            client = MockBT.return_value
            client.source_lang = "ja"
            client.target_lang = "zh"
            assert client.source_lang == "ja"
            assert client.target_lang == "zh"

    def test_translate_stream(self):
        """翻译应返回文本块"""
        with patch("src.translator.BuiltinTranslator") as MockBT:
            client = MockBT.return_value
            client.translate_stream.return_value = ["今天", "天气", "很好"]
            result = list(client.translate_stream("今日は良い天気です"))
            assert len(result) > 0
            assert "".join(result).strip()

    def test_translate_empty_text(self):
        """空文本应返回空"""
        with patch("src.translator.BuiltinTranslator") as MockBT:
            client = MockBT.return_value
            client.translate_stream.return_value = []
            result = list(client.translate_stream(""))
            assert result == []


class TestTranslationContext:
    """翻译上下文管理测试"""

    @pytest.fixture
    def context(self):
        with patch("src.translator.TranslationContext") as MockCtx:
            mock = MockCtx.return_value
            mock.max_turns = 5
            mock.history = []
            yield mock

    def test_max_turns_default(self, context):
        assert context.max_turns == 5

    def test_add_turn(self, context):
        context.history.append({"source": "hello", "translation": "你好"})
        assert len(context.history) == 1

    def test_context_window_sliding(self, context):
        context.max_turns = 2
        context.history = [
            {"source": "a", "translation": "A"},
            {"source": "b", "translation": "B"},
        ]
        context.history.append({"source": "c", "translation": "C"})
        if len(context.history) > context.max_turns:
            context.history.pop(0)
        assert len(context.history) == 2
        assert context.history[0]["source"] == "b"

    def test_clear_context(self, context):
        context.history.append({"source": "test", "translation": "测试"})
        context.history = []
        assert len(context.history) == 0


class TestCreateTranslator:
    """工厂函数测试"""

    def test_builtin_engine(self):
        """factory 应返回 BuiltinTranslator"""
        with patch("src.translator.BuiltinTranslator") as MockBT:
            result = MockBT.return_value
            result.source_lang = "en"
            assert result.source_lang == "en"

    def test_lang_resolution(self):
        """语言代码应正确解析"""
        from src.translator import _resolve_lang
        assert _resolve_lang("ja") == "ja"
        assert _resolve_lang("japanese") == "ja"
        assert _resolve_lang("zh-CN") == "zh"
        assert _resolve_lang("en") == "en"

    def test_model_name_lookup(self):
        """语言对应映射到正确的模型名"""
        from src.translator import _get_ct2_model_name
        model = _get_ct2_model_name("ja", "zh")
        assert model is not None
        assert "opus" in model

    def test_invalid_lang_pair(self):
        """不支持的语言对应返回 None"""
        from src.translator import _get_ct2_model_name
        model = _get_ct2_model_name("fr", "de")
        assert model is None
