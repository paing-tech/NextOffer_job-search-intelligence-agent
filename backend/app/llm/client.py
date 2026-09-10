"""LLM access — GPT-5.6 Terra via Microsoft Foundry (Azure AI Foundry).

Everything provider-specific lives here. The rest of the codebase calls
``complete()`` and gets back a normalized :class:`LLMResult`, so swapping the
model or provider is a one-file change.

Foundry exposes an OpenAI-compatible surface. Two shapes are supported:
  * Azure-OpenAI style  — set ``FOUNDRY_API_VERSION`` (uses ``AsyncAzureOpenAI``)
  * Unified / OpenAI style — leave it unset (uses ``AsyncOpenAI`` + ``base_url``)

NOTE: confirm the exact endpoint/params for the ``gpt-5.6-terra`` deployment
against current Azure AI Foundry docs; only this module should need changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.config import get_settings

_settings = get_settings()


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResult:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    parsed: dict | None = None
    usage: dict = field(default_factory=dict)
    finish_reason: str | None = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMNotConfigured(RuntimeError):
    pass


@lru_cache
def _client():
    if not _settings.foundry_endpoint or not _settings.foundry_api_key:
        raise LLMNotConfigured(
            "FOUNDRY_ENDPOINT and FOUNDRY_API_KEY must be set to call the model."
        )
    endpoint = _settings.foundry_endpoint.rstrip("/")

    # Foundry unified endpoint (…/openai/v1) speaks the plain OpenAI protocol.
    # Only the classic resource endpoint (…openai.azure.com, no /v1) needs the
    # Azure client with an api-version.
    use_azure = _settings.foundry_api_version and not endpoint.endswith("/openai/v1")

    if use_azure:
        from openai import AsyncAzureOpenAI

        return AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=_settings.foundry_api_key,
            api_version=_settings.foundry_api_version,
        )
    from openai import AsyncOpenAI

    return AsyncOpenAI(base_url=endpoint, api_key=_settings.foundry_api_key)


def _response_format(schema: dict | None) -> dict | None:
    if schema is None:
        return None
    return {
        "type": "json_schema",
        "json_schema": {"name": schema.get("title", "output"), "schema": schema, "strict": True},
    }


async def complete(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    response_schema: dict | None = None,
    temperature: float | None = None,
    max_tokens: int = 2048,
) -> LLMResult:
    """One model call. Returns text and/or tool calls and/or a parsed object.

    GPT-5.x / reasoning-style deployments use ``max_completion_tokens`` (not
    ``max_tokens``) and reject any ``temperature`` other than the default, so we
    only send ``temperature`` when a caller explicitly asks for one.
    """
    kwargs: dict[str, Any] = {
        "model": _settings.foundry_deployment,
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice
    fmt = _response_format(response_schema)
    if fmt:
        kwargs["response_format"] = fmt

    resp = await _client().chat.completions.create(**kwargs)
    choice = resp.choices[0]
    msg = choice.message

    tool_calls: list[ToolCall] = []
    for tc in msg.tool_calls or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {"_raw": tc.function.arguments}
        tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

    parsed = None
    if fmt and msg.content:
        try:
            parsed = json.loads(msg.content)
        except json.JSONDecodeError:
            parsed = None

    usage = {}
    if resp.usage:
        usage = {
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "total_tokens": resp.usage.total_tokens,
        }

    return LLMResult(
        text=msg.content,
        tool_calls=tool_calls,
        parsed=parsed,
        usage=usage,
        finish_reason=choice.finish_reason,
    )
