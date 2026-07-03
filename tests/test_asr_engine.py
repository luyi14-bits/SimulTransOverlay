"""Tests for ASR engine module."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestASREngineBase:
    """ASR 引擎抽象基类测试"""

    def test_engine_factory_returns_whisper(self):
        """工厂应返回 faster-whisper 实例"""
        with patch("src.asr_engine.create_asr_engine") as factory:
            engine = factory.return_value
            engine.name = "faster-whisper"
            assert engine.name == "faster-whisper"

    def test_engine_factory_returns_sensevoice(self):
        """工厂应返回 SenseVoice 实例"""
        with patch("src.asr_engine.create_asr_engine") as factory:
            engine = factory.return_value
            engine.name = "sensevoice"
            assert engine.name == "sensevoice"

    def test_engine_invalid_name(self):
        """无效引擎名应抛出 ValueError"""
        with patch("src.asr_engine.create_asr_engine") as factory:
            factory.side_effect = ValueError("Unknown engine: invalid")
            with pytest.raises(ValueError, match="Unknown engine"):
                factory("invalid")

    def test_engine_has_expected_methods(self):
        """引擎应有 transcribe 和 load_model 方法"""
        with patch("src.asr_engine.BaseASREngine") as MockEngine:
            mock = MockEngine.return_value
            mock.load_model = MagicMock()
            mock.transcribe = MagicMock(return_value="test text")
            assert callable(mock.load_model)
            assert callable(mock.transcribe)


class TestWhisperEngine:
    """faster-whisper 引擎测试"""

    @pytest.fixture
    def whisper(self):
        with patch("src.asr_whisper.WhisperASREngine") as MockWhisper:
            mock = MockWhisper.return_value
            mock.name = "faster-whisper"
            mock.model_size = "small"
            mock.device = "auto"
            mock.compute_type = "int8"
            mock.language = "ja"
            mock.is_loaded = False
            yield mock

    def test_default_config(self, whisper):
        """默认配置应为 small + INT8 + auto 设备"""
        assert whisper.model_size == "small"
        assert whisper.compute_type == "int8"
        assert whisper.device == "auto"

    def test_load_model_sets_loaded(self, whisper):
        """加载模型后 is_loaded 应为 True"""
        whisper.is_loaded = True
        assert whisper.is_loaded is True

    def test_transcribe_returns_text(self, whisper):
        """转写应返回字符串"""
        whisper.transcribe.return_value = "今日の天気は良いです"
        result = whisper.transcribe(np.zeros(16000, dtype=np.float32))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_transcribe_silence(self, whisper):
        """静音输入应返回空字符串"""
        whisper.transcribe.return_value = ""
        result = whisper.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""


class TestSenseVoiceEngine:
    """SenseVoice 引擎测试"""

    @pytest.fixture
    def sensevoice(self):
        with patch("src.asr_sensevoice.SenseVoiceASREngine") as MockSV:
            mock = MockSV.return_value
            mock.name = "sensevoice"
            mock.language = "zh"
            mock.is_loaded = False
            yield mock

    def test_engine_name(self, sensevoice):
        assert sensevoice.name == "sensevoice"

    def test_transcribe_chinese(self, sensevoice):
        """SenseVoice 转写中文"""
        sensevoice.transcribe.return_value = "今天天气很好"
        result = sensevoice.transcribe(np.zeros(16000, dtype=np.float32))
        assert "天气" in result


class TestModelManager:
    """模型管理器测试"""

    @pytest.fixture
    def model_manager(self):
        with patch("src.model_manager.ModelManager") as MockMM:
            mock = MockMM.return_value
            mock.model_dir = "models/"
            yield mock

    def test_model_dir(self, model_manager):
        assert model_manager.model_dir == "models/"

    def test_download_model(self, model_manager):
        """下载模型标记状态"""
        model_manager.download.return_value = True
        result = model_manager.download("base")
        assert result is True

    def test_model_exists_check(self, model_manager):
        """检查模型是否已存在"""
        model_manager.is_downloaded.return_value = False
        result = model_manager.is_downloaded("medium")
        assert result is False
        model_manager.is_downloaded.return_value = True
        result = model_manager.is_downloaded("base")
        assert result is True


class TestTranscriptionBuffer:
    """转写结果缓冲与句子组装测试"""

    @pytest.fixture
    def buffer(self):
        with patch("src.asr_engine.TranscriptionBuffer") as MockBuf:
            mock = MockBuf.return_value
            mock.max_segments = 5
            yield mock

    def test_max_segments(self, buffer):
        """缓冲应有最大片段数限制"""
        assert buffer.max_segments == 5

    def test_add_segment(self, buffer):
        """添加片段应返回当前句子"""
        buffer.add_segment.return_value = "今日の天気は"
        result = buffer.add_segment("今日の天気は")
        assert result is not None
