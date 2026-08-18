from __future__ import annotations

from openai import OpenAI

from .config import settings


client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)


def complete(messages: list[dict[str, str]]) -> str:
    response = client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=1.0,
        top_p=0.95,
    )
    message = response.choices[0].message
    return message.content or ""
