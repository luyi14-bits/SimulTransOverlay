"""Translation engine module.

Provides embedded offline translation using ctranslate2 + OPUS-MT models.
No external service dependencies. Models are auto-downloaded on first use.

Language pairs supported:
  - ja→zh (Japanese → Chinese)
  - ja→en (Japanese → English)
  - en→zh (English → Chinese)
  - zh→en (Chinese → English)
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Language code normalization
LANG_ALIAS = {
    "ja": "ja", "japanese": "ja",
    "en": "en", "english": "en",
    "zh": "zh", "zh-cn": "zh", "zh-tw": "zh", "chinese": "zh",
}

# OPUS-MT models on HuggingFace (ctranslate2 compatible)
OPUS_MODELS = {
    ("ja", "zh"): "Helsinki-NLP/opus-mt-ja-zh",
    ("ja", "en"): "Helsinki-NLP/opus-mt-ja-en",
    ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
    ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
}


def _get_model_dir() -> Path:
    """Get model storage directory (PyInstaller-compatible)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "models" / "translation"
    return Path(__file__).resolve().parent.parent / "models" / "translation"


def _resolve_lang(lang: str) -> str:
    return LANG_ALIAS.get(lang.lower(), lang)


def _get_ct2_model_name(src: str, tgt: str) -> Optional[str]:
    src, tgt = _resolve_lang(src), _resolve_lang(tgt)
    return OPUS_MODELS.get((src, tgt))


class TranslationContext:
    """Conversation context for translation."""

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []

    def add_turn(self, source: str, translation: str) -> None:
        self.history.append({"source": source, "translation": translation})
        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def clear(self) -> None:
        self.history = []


class BuiltinTranslator:
    """Offline translator using ctranslate2 + OPUS-MT.

    No external service dependencies. Model auto-downloads on first use.
    """

    def __init__(
        self,
        source_lang: str = "ja",
        target_lang: str = "zh",
        model_name: Optional[str] = None,
        context: Optional[TranslationContext] = None,
    ):
        self.source_lang = _resolve_lang(source_lang)
        self.target_lang = _resolve_lang(target_lang)
        self.model_name = model_name or _get_ct2_model_name(self.source_lang, self.target_lang)
        self.context = context or TranslationContext()
        self._translator = None
        self._tokenizer = None

    def _load_model(self):
        """Load translation model (lazy, on first use)."""
        if self._translator is not None:
            return

        if self.model_name is None:
            raise RuntimeError(
                f"No translation model for {self.source_lang}→{self.target_lang}. "
                f"Supported: {list(OPUS_MODELS.keys())}"
            )

        logger.info(f"Loading translation model: {self.model_name}")
        try:
            # Try loading from local cache first
            cache_dir = _get_model_dir() / self.model_name.replace("/", "_")
            model_path = str(cache_dir) if cache_dir.exists() else self.model_name

            import ctranslate2
            import sentencepiece as spm

            self._translator = ctranslate2.Translator(
                model_path,
                device="cpu",
                compute_type="int8",
            )

            # Load tokenizer (SentencePiece model)
            if cache_dir.exists():
                sp_path = cache_dir / "source.spm"
                if not sp_path.exists():
                    sp_path = cache_dir / "spm.source.nopretok.model"
                if not sp_path.exists():
                    # Find any .spm file
                    sp_files = list(cache_dir.glob("*.spm"))
                    sp_path = sp_files[0] if sp_files else None
            else:
                sp_path = None

            if sp_path and sp_path.exists():
                self._tokenizer = spm.SentencePieceProcessor(str(sp_path))
            else:
                logger.warning("No SentencePiece model found, using fallback tokenizer")

            logger.info("Translation model loaded successfully")

        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load translation model: {e}")
            raise

    def translate_stream(self, text: str, target: Optional[str] = None):
        """Translate text with streaming output.

        Args:
            text: Source text to translate
            target: Override target language

        Yields:
            Text chunks for streaming display
        """
        if not text.strip():
            return

        self._load_model()
        if self._translator is None:
            yield "[翻译模型未加载]"
            return

        try:
            # Tokenize
            if self._tokenizer:
                tokens = self._tokenizer.encode(text, out_type=str)
            else:
                tokens = list(text)

            # Translate
            results = self._translator.translate_batch(
                [tokens],
                beam_size=4,
                max_batch_size=1,
            )

            # Detokenize
            if self._tokenizer:
                translation = self._tokenizer.decode(results[0].tokens)
            else:
                translation = " ".join(results[0].tokens)

            self.context.add_turn(text, translation)

            # Stream output in chunks for real-time effect
            if any('\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' for c in translation):
                chunk_size = max(1, len(translation) // 8)
                for i in range(0, len(translation), chunk_size):
                    yield translation[i:i + chunk_size]
            else:
                words = translation.split(" ")
                for word in words:
                    yield word + " "

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            yield f"[翻译错误]"

    def translate(self, text: str) -> str:
        chunks = list(self.translate_stream(text))
        return "".join(chunks).strip()


def create_translator(
    engine: str = "builtin",
    source_lang: str = "ja",
    target_lang: str = "zh",
    context: Optional[TranslationContext] = None,
):
    """Factory to create a translator engine.

    Args:
        engine: "builtin" (default, offline) | "ollama" | "deepseek"
        source_lang: Source language code
        target_lang: Target language code
        context: Optional translation context

    Returns:
        Translator instance
    """
    if engine == "builtin":
        return BuiltinTranslator(
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
        )
    elif engine == "ollama":
        from .translator_legacy import OllamaClient
        return OllamaClient(context=context)
    elif engine == "deepseek":
        from .translator_legacy import DeepSeekClient
        return DeepSeekClient(context=context)
    else:
        raise ValueError(f"Unknown translation engine: {engine}")
