from __future__ import annotations

from openai import OpenAI

from .config import settings


client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)


def complete(messages: list[dict[str, str]]) -> tuple[str, int, int]:
    response = client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=1.0,
        top_p=0.95,
    )
    message = response.choices[0].message
    usage = response.usage
    if usage:
        return message.content or "", usage.prompt_tokens, usage.completion_tokens
    return message.content or "", 0, 0
