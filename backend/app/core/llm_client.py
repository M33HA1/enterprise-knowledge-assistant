"""
LLM client abstraction layer.

Supports OpenAI (gpt-4o-mini) and Anthropic Claude.
Default: OpenAI gpt-4o-mini (cheapest capable model).
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import settings, LLMProvider

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are an Enterprise Knowledge Assistant.
Answer employee questions using ONLY the provided context from company documents.

RULES:
1. Answer ONLY from the provided context. Do NOT use general knowledge.
2. ALWAYS cite sources: [Source: document_name, Section/Page: X]
3. If context is insufficient, say so explicitly.
4. If unsure, flag: ⚠️ LOW CONFIDENCE - This may need human review.
5. Use bullet points for multi-part answers.
6. Quote policy sections directly when relevant.
7. Never fabricate information.
"""


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    confidence: float


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, query: str, context: str, system_prompt: str = None) -> LLMResponse:
        ...

    @abstractmethod
    async def agenerate(self, query: str, context: str, system_prompt: str = None) -> LLMResponse:
        ...

    def _estimate_confidence(self, text: str) -> float:
        markers = [
            "i don't have enough information", "not enough context",
            "cannot determine", "unclear from the provided",
            "may need human review", "i'm not sure",
            "not mentioned in", "low confidence",
        ]
        count = sum(1 for m in markers if m in text.lower())
        if count >= 2: return 0.2
        if count == 1: return 0.5
        if "⚠️" in text: return 0.3
        return 0.85


class OpenAIClient(BaseLLMClient):
    def __init__(self):
        from openai import OpenAI, AsyncOpenAI
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required")
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL
        logger.info(f"OpenAI client: {self._model}")

    def _build_messages(self, query, context, system_prompt):
        return [
            {"role": "system", "content": system_prompt or RAG_SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n---\n{context}\n---\n\nQUESTION: {query}\n\nAnswer from context only. Cite documents."},
        ]

    def generate(self, query, context, system_prompt=None):
        from openai import AuthenticationError, RateLimitError, APIError
        msgs = self._build_messages(query, context, system_prompt)
        try:
            r = self._client.chat.completions.create(model=self._model, messages=msgs, temperature=0.2, max_tokens=1500)
        except AuthenticationError:
            raise ValueError(
                "OpenAI API key is invalid. Check OPENAI_API_KEY in backend/.env. "
                "Get your key at https://platform.openai.com/api-keys"
            )
        except RateLimitError as e:
            raise ValueError(f"OpenAI rate limit exceeded. Wait and retry. Details: {e}")
        except APIError as e:
            raise ValueError(f"OpenAI API error: {e}")
        c = r.choices[0].message.content
        return LLMResponse(content=c, model=self._model, tokens_used=r.usage.total_tokens, confidence=self._estimate_confidence(c))

    async def agenerate(self, query, context, system_prompt=None):
        from openai import AuthenticationError, RateLimitError, APIError
        msgs = self._build_messages(query, context, system_prompt)
        try:
            r = await self._async_client.chat.completions.create(model=self._model, messages=msgs, temperature=0.2, max_tokens=1500)
        except AuthenticationError:
            raise ValueError(
                "OpenAI API key is invalid. Check OPENAI_API_KEY in backend/.env. "
                "Get your key at https://platform.openai.com/api-keys"
            )
        except RateLimitError as e:
            raise ValueError(f"OpenAI rate limit exceeded. Wait and retry. Details: {e}")
        except APIError as e:
            raise ValueError(f"OpenAI API error: {e}")
        c = r.choices[0].message.content
        return LLMResponse(content=c, model=self._model, tokens_used=r.usage.total_tokens, confidence=self._estimate_confidence(c))


class ClaudeClient(BaseLLMClient):
    def __init__(self):
        from anthropic import Anthropic, AsyncAnthropic
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY required")
        self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.CLAUDE_MODEL
        logger.info(f"Claude client: {self._model}")

    def generate(self, query, context, system_prompt=None):
        r = self._client.messages.create(
            model=self._model, max_tokens=1500, temperature=0.2,
            system=system_prompt or RAG_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"CONTEXT:\n---\n{context}\n---\n\nQUESTION: {query}\n\nAnswer from context only. Cite documents."}],
        )
        c = r.content[0].text
        return LLMResponse(content=c, model=self._model, tokens_used=r.usage.input_tokens + r.usage.output_tokens, confidence=self._estimate_confidence(c))

    async def agenerate(self, query, context, system_prompt=None):
        r = await self._async_client.messages.create(
            model=self._model, max_tokens=1500, temperature=0.2,
            system=system_prompt or RAG_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"CONTEXT:\n---\n{context}\n---\n\nQUESTION: {query}\n\nAnswer from context only. Cite documents."}],
        )
        c = r.content[0].text
        return LLMResponse(content=c, model=self._model, tokens_used=r.usage.input_tokens + r.usage.output_tokens, confidence=self._estimate_confidence(c))


class GeminiClient(BaseLLMClient):
    """
    Google Gemini LLM client.

    Uses gemini-2.0-flash by default — free tier allows 15 RPM / 1M TPM.
    Best free option for development and testing.
    """

    def __init__(self):
        from google import genai
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY required. Get one free at https://aistudio.google.com/apikey")
        self._genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL
        logger.info(f"Gemini client: {self._model}")

    def _build_prompt(self, query, context, system_prompt):
        sys = system_prompt or RAG_SYSTEM_PROMPT
        return f"{sys}\n\nCONTEXT:\n---\n{context}\n---\n\nQUESTION: {query}\n\nAnswer from context only. Cite documents."

    def generate(self, query, context, system_prompt=None):
        from google import genai
        from google.genai import types
        prompt = self._build_prompt(query, context, system_prompt)
        try:
            r = self._genai_client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=1500),
            )
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                raise ValueError(
                    "Gemini free tier quota exceeded for today. "
                    "Switch to another model using the UI model selector, "
                    "or wait until tomorrow for the quota to reset."
                )
            raise ValueError(f"Gemini API error: {e}")
        c = r.text
        tokens = getattr(r, 'usage_metadata', None)
        total_tokens = 0
        if tokens:
            total_tokens = getattr(tokens, 'total_token_count', 0)
        return LLMResponse(content=c, model=self._model, tokens_used=total_tokens, confidence=self._estimate_confidence(c))

    async def agenerate(self, query, context, system_prompt=None):
        from google import genai
        from google.genai import types
        prompt = self._build_prompt(query, context, system_prompt)
        try:
            r = await self._genai_client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=1500),
            )
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                raise ValueError(
                    "Gemini free tier quota exceeded for today. "
                    "Switch to another model using the UI model selector, "
                    "or wait until tomorrow for the quota to reset."
                )
            raise ValueError(f"Gemini API error: {e}")
        c = r.text
        tokens = getattr(r, 'usage_metadata', None)
        total_tokens = 0
        if tokens:
            total_tokens = getattr(tokens, 'total_token_count', 0)
        return LLMResponse(content=c, model=self._model, tokens_used=total_tokens, confidence=self._estimate_confidence(c))


class GrokClient(BaseLLMClient):
    """
    xAI Grok client using the OpenAI compatible endpoint.
    """
    def __init__(self):
        from openai import OpenAI, AsyncOpenAI
        if not settings.GROK_API_KEY:
            raise ValueError("GROK_API_KEY required")
        self._client = OpenAI(api_key=settings.GROK_API_KEY, base_url="https://api.x.ai/v1")
        self._async_client = AsyncOpenAI(api_key=settings.GROK_API_KEY, base_url="https://api.x.ai/v1")
        self._model = settings.GROK_MODEL
        logger.info(f"Grok client: {self._model}")

    def _build_messages(self, query, context, system_prompt):
        return [
            {"role": "system", "content": system_prompt or RAG_SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n---\n{context}\n---\n\nQUESTION: {query}\n\nAnswer from context only. Cite documents."},
        ]

    def generate(self, query, context, system_prompt=None):
        from openai import AuthenticationError, RateLimitError, APIError
        msgs = self._build_messages(query, context, system_prompt)
        try:
            r = self._client.chat.completions.create(model=self._model, messages=msgs, temperature=0.2, max_tokens=1500)
        except AuthenticationError:
            raise ValueError("Grok API key is invalid. Check GROK_API_KEY in .env.")
        except RateLimitError as e:
            raise ValueError(f"Grok rate limit exceeded. Details: {e}")
        except APIError as e:
            raise ValueError(f"Grok API error: {e}")
        c = r.choices[0].message.content
        return LLMResponse(content=c, model=self._model, tokens_used=r.usage.total_tokens, confidence=self._estimate_confidence(c))

    async def agenerate(self, query, context, system_prompt=None):
        from openai import AuthenticationError, RateLimitError, APIError
        msgs = self._build_messages(query, context, system_prompt)
        try:
            r = await self._async_client.chat.completions.create(model=self._model, messages=msgs, temperature=0.2, max_tokens=1500)
        except AuthenticationError:
            raise ValueError("Grok API key is invalid. Check GROK_API_KEY in .env.")
        except RateLimitError as e:
            raise ValueError(f"Grok rate limit exceeded. Details: {e}")
        except APIError as e:
            raise ValueError(f"Grok API error: {e}")
        c = r.choices[0].message.content
        return LLMResponse(content=c, model=self._model, tokens_used=r.usage.total_tokens, confidence=self._estimate_confidence(c))


def get_llm_client_by_provider(provider: str) -> BaseLLMClient:
    """Factory: returns LLM client for specific provider."""
    provider = provider.lower() if provider else ""
    if provider == LLMProvider.CLAUDE.value:
        return ClaudeClient()
    elif provider == LLMProvider.GEMINI.value:
        return GeminiClient()
    elif provider == LLMProvider.GROK.value:
        return GrokClient()
    elif provider == LLMProvider.OPENAI.value:
        return OpenAIClient()
    return get_llm_client()  # fallback to default

def get_llm_client() -> BaseLLMClient:
    """Factory: returns configured default LLM client."""
    if settings.LLM_PROVIDER == LLMProvider.CLAUDE:
        return ClaudeClient()
    elif settings.LLM_PROVIDER == LLMProvider.GEMINI:
        return GeminiClient()
    elif settings.LLM_PROVIDER == LLMProvider.GROK:
        return GrokClient()
    return OpenAIClient()
