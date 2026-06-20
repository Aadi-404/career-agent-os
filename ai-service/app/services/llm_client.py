import httpx
from fastapi import HTTPException

from app.core.config import Settings


def call_llm(prompt: str, settings: Settings, provider: str, model: str) -> str:
    api_key = _resolve_api_key(settings, provider)
    if not api_key:
        raise HTTPException(status_code=500, detail=f"API key is required for provider: {provider}")

    if provider == "groq":
        return _call_openai_compatible(
            base_url="https://api.groq.com/openai/v1/chat/completions",
            prompt=prompt,
            settings=settings,
            api_key=api_key,
            model=model,
        )

    if provider == "openai":
        return _call_openai_compatible(
            base_url="https://api.openai.com/v1/chat/completions",
            prompt=prompt,
            settings=settings,
            api_key=api_key,
            model=model,
        )

    if provider == "gemini":
        return _call_gemini(prompt=prompt, settings=settings, api_key=api_key, model=model)

    raise HTTPException(status_code=500, detail=f"Unsupported LLM provider: {provider}")


def _resolve_api_key(settings: Settings, provider: str) -> str:
    if provider == "groq":
        return settings.groq_api_key or settings.llm_api_key
    if provider == "openai":
        return settings.openai_api_key or settings.llm_api_key
    if provider == "gemini":
        return settings.gemini_api_key or settings.google_api_key or settings.llm_api_key
    return settings.llm_api_key


def _call_openai_compatible(base_url: str, prompt: str, settings: Settings, api_key: str, model: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Return only valid JSON. Do not include markdown fences.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="LLM request timed out") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Gemini model not found: {model}. Select a current Gemini API model "
                    "such as gemini-3.5-flash, gemini-2.5-flash, or gemini-2.5-flash-lite."
                ),
            ) from exc
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    data = response.json()
    return data["choices"][0]["message"]["content"]


def _call_gemini(prompt: str, settings: Settings, api_key: str, model: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="LLM request timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
