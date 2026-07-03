"""Legacy translation engine module (Ollama/DeepSeek fallback).

Kept as fallback for users who prefer cloud-based translation.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from .translator import TranslationContext

logger = logging.getLogger(__name__)

TRANSLATION_SYSTEM_PROMPT = """You are a professional real-time translator. 
Translate the given text accurately and naturally. 
Only output the translation, no explanations, no notes."""


class OllamaClient:
    """Ollama API client for streaming translation (fallback)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        context: Optional[TranslationContext] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.context = context or TranslationContext()

    def translate_stream(self, text: str, target: str = "zh-CN"):
        if not text.strip():
            return
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{
                            "role": "user",
                            "content": f"Translate to {target}: {text}"
                        }],
                        "stream": True,
                    },
                )
                response.raise_for_status()
                full_text = ""
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_text += content
                            yield content
                    except json.JSONDecodeError:
                        continue
                self.context.add_turn(text, full_text)
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            yield "[Ollama 连接失败]"
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            yield f"[翻译错误: {e}]"


class DeepSeekClient:
    """DeepSeek API client (fallback)."""

    def __init__(
        self,
        api_base: str = "https://api.deepseek.com/v1",
        api_key: str = "",
        model: str = "deepseek-chat",
        context: Optional[TranslationContext] = None,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.context = context or TranslationContext()

    def translate_stream(self, text: str, target: str = "zh-CN"):
        if not text.strip():
            return
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.api_base}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": f"Translate to {target}: {text}"}],
                        "stream": True,
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"DeepSeek failed: {e}")
            yield "[翻译错误]"
