"""
Pluggable LLM client.

Supports Anthropic Claude and Groq (free tier, no credit card required,
OpenAI-compatible API) as interchangeable providers for the extraction and
AI-commentary pipelines. The provider is chosen automatically based on
which API key is present in the environment — no other code needs to
change to switch between them:

    GROQ_API_KEY set        -> Groq, model below (free)
    ANTHROPIC_API_KEY set   -> Anthropic Claude (paid)
    neither set              -> raises a clear error; callers should
                                 surface this or fall back to templated
                                 content rather than crash

If both are set, ANTHROPIC_API_KEY takes precedence (treated as an
intentional upgrade from the free tier).

Get a free Groq key at https://console.groq.com/keys — no billing required.
Get an Anthropic key at https://console.anthropic.com — paid, usage-based.
"""

import os

GROQ_MODEL = "llama-3.3-70b-versatile"
ANTHROPIC_MODEL = "claude-sonnet-4-6"


def get_provider() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    return "none"


def current_model_label() -> str:
    provider = get_provider()
    if provider == "anthropic":
        return ANTHROPIC_MODEL
    if provider == "groq":
        return f"groq/{GROQ_MODEL}"
    return "none"


def chat_json(system: str, user: str, max_tokens: int = 4000) -> str:
    """Sends a system + user prompt to whichever provider is configured and
    returns the raw text response. Callers are responsible for parsing/
    validating JSON out of the returned text (providers occasionally wrap
    it in markdown fences despite instructions not to)."""
    provider = get_provider()

    if provider == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    if provider == "groq":
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content

    raise RuntimeError(
        "No LLM provider configured. Set one of the following before starting "
        "the server:\n"
        "  GROQ_API_KEY       — free, no credit card: https://console.groq.com/keys\n"
        "  ANTHROPIC_API_KEY  — paid, usage-based: https://console.anthropic.com"
    )