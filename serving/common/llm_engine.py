"""
Shared llama.cpp inference wrapper (SK-JF5-01).

Thin wrapper around `llama_cpp.Llama` (the llama.cpp Python bindings) so the
three BentoML services (small / medium / quantized) share identical loading,
health-check and generation logic and only differ by model path + name.

CPU-only. No CUDA / GPU flags are set anywhere in this file (hardware
constraint: 4 vCPU, ~15 GiB RAM, no NVIDIA GPU).
"""

from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger("llm_engine")


class ModelNotLoadedError(RuntimeError):
    pass


class LlamaCppEngine:
    def __init__(
        self,
        model_alias: str,
        model_path: str,
        n_ctx: int = 2048,
        n_threads: int = 2,
        max_tokens: int = 256,
    ):
        self.model_alias = model_alias
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.max_tokens = max_tokens
        self._llm = None
        self._load_error: Optional[str] = None

    def load(self) -> None:
        """Load the GGUF model. Safe to call once at service startup."""
        if not os.path.isfile(self.model_path):
            self._load_error = f"Model file not found at {self.model_path}"
            logger.error(self._load_error)
            return

        try:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_batch=self.n_threads * 32,
                use_mlock=False,
                verbose=False,
            )
            logger.info(
                "Loaded model '%s' from %s (ctx=%d, threads=%d)",
                self.model_alias,
                self.model_path,
                self.n_ctx,
                self.n_threads,
            )
        except Exception as exc:
            self._load_error = f"Failed to load model: {exc}"
            logger.exception(self._load_error)
            self._llm = None

    @property
    def is_ready(self) -> bool:
        return self._llm is not None

    def health(self) -> dict:
        return {
            "model": self.model_alias,
            "model_path": self.model_path,
            "loaded": self.is_ready,
            "error": self._load_error,
            "context_size": self.n_ctx,
            "threads": self.n_threads,
        }

    def generate(self, prompt: str, max_tokens: Optional[int] = None, temperature: float = 0.7):
        """Run inference. Returns (text, input_tokens, output_tokens)."""
        if not self.is_ready:
            raise ModelNotLoadedError(self._load_error or "Model is not loaded")

        max_tokens = max_tokens or self.max_tokens

        result = self._llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = result["choices"][0]
        text = choice["message"]["content"]
        usage = result.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return text, input_tokens, output_tokens
