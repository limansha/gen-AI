import logging
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.settings import settings

logger = logging.getLogger(__name__)


class LLMUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(TypedDict):
    content: str
    usage: LLMUsage


def _normalize_usage(metadata: dict[str, Any] | None) -> LLMUsage:
    if not metadata:
        return LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
    usage = metadata.get("token_usage") or metadata.get("usage_metadata") or {}
    prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("prompt_token_count", 0)
    completion = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("candidates_token_count", 0)
    total = usage.get("total_tokens") or (prompt + completion)
    return LLMUsage(
        prompt_tokens=int(prompt),
        completion_tokens=int(completion),
        total_tokens=int(total),
    )


def _build_client(
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    temp = temperature if temperature is not None else settings.llm_temperature
    max_tok = max_tokens or settings.llm_max_tokens
    if not settings.llm_api_key or not settings.llm_api_key.strip():
        raise ValueError(
            "LLM_API_KEY is not set. Set it in .env or use GOOGLE_API_KEY for Gemini."
        )
    if settings.llm_provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            temperature=temp,
            max_output_tokens=max_tok,
            api_key=settings.llm_api_key,
        )
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=temp,
        max_tokens=max_tok,
        api_key=settings.llm_api_key,
    )


class LLMClient:
    """Abstraction for LLM provider operations (OpenAI, Anthropic, Gemini)."""

    _client: BaseChatModel | None = None

    @classmethod
    def _get_client(cls) -> BaseChatModel:
        if cls._client is None:
            cls._client = _build_client()
        return cls._client

    @staticmethod
    async def generate_completion(
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        try:
            if temperature is not None or max_tokens is not None:
                client = _build_client(temperature=temperature, max_tokens=max_tokens)
            else:
                client = LLMClient._get_client()

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            response = await client.ainvoke(messages)
            metadata = getattr(response, "response_metadata", None) or {}
            usage = _normalize_usage(metadata)

            return LLMResponse(
                content=response.content,
                usage=usage,
            )
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate LLM response: {str(e)}")

    @staticmethod
    async def generate_structured(
        prompt: str,
        system_prompt: str | None = None,
        output_parser: StrOutputParser | None = None,
    ) -> str:
        response = await LLMClient.generate_completion(prompt, system_prompt)
        if output_parser:
            return output_parser.parse(response["content"])
        return response["content"]
