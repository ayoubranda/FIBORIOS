"""
Claude intelligence layer.

Receives only the final outputs of Fibrios engines — no raw candles,
no large JSON. Target: < 500 input tokens, < 300 output tokens per call.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict

import anthropic

# In-process response cache (5-minute TTL)
_CACHE: Dict[str, Dict[str, Any]] = {}
_TTL = 300


class ClaudeAnalyzer:
    """Bridge between Fibrios engine outputs and the Anthropic Claude API."""

    # Cheapest capable model — keeps cost < $0.001 per analysis
    MODEL = "claude-haiku-4-5-20251001"
    MAX_TOKENS = 300

    _SYSTEM = (
        "You are an institutional trading analyst assistant.\n"
        "You receive compact Fibrios engine outputs (signal, confidence, bias labels).\n"
        "Return exactly 4 labelled lines:\n"
        "Summary: <1-2 sentences>\n"
        "Reasoning: <1-2 sentences>\n"
        "Risks: <1-2 sentences>\n"
        "Narrative: <1 sentence>\n"
        "No preamble. No markdown. Be concise."
    )

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY environment variable is not set."
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(self, signal_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send minimal engine output to Claude and return structured narrative.

        signal_context must contain only:
            symbol, timeframe, signal, confidence,
            elliott_bias, market_structure, liquidity, price_action
        """
        key = self._cache_key(signal_context)
        cached = _CACHE.get(key)
        if cached and (time.time() - cached["ts"]) < _TTL:
            return cached["data"]

        prompt = self._build_prompt(signal_context)
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=self._SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        result = self._parse(text)
        _CACHE[key] = {"ts": time.time(), "data": result}
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, ctx: Dict[str, Any]) -> str:
        # Minimal — well under 200 tokens
        return (
            f"Symbol: {ctx.get('symbol')} | TF: {ctx.get('timeframe')}\n"
            f"Signal: {ctx.get('signal')} | Confidence: {ctx.get('confidence')}/10\n"
            f"Elliott: {ctx.get('elliott_bias')} | Structure: {ctx.get('market_structure')}\n"
            f"Liquidity: {ctx.get('liquidity')} | PA: {ctx.get('price_action')}"
        )

    def _parse(self, text: str) -> Dict[str, Any]:
        """Extract the four labelled fields from Claude's response."""
        result: Dict[str, Any] = {
            "market_summary": "",
            "trade_reasoning": "",
            "risks": "",
            "institutional_narrative": "",
        }
        field_map = {
            "summary":   "market_summary",
            "reasoning": "trade_reasoning",
            "risks":     "risks",
            "narrative": "institutional_narrative",
        }
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            for label, key in field_map.items():
                if lower.startswith(label + ":"):
                    result[key] = line[len(label) + 1:].strip()
                    break
        # Fallback: if parsing fails, put full text in summary
        if not any(result.values()):
            result["market_summary"] = text
        return result

    @staticmethod
    def _cache_key(ctx: Dict[str, Any]) -> str:
        return hashlib.md5(json.dumps(ctx, sort_keys=True).encode()).hexdigest()
