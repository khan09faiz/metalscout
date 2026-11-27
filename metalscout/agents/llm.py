"""Model router over free, OpenAI-compatible LLM endpoints.

Every provider here speaks the same `POST {base}/chat/completions` API, so one client covers all of them.
Model names on free tiers change often, so nothing is hard-coded: at the start of a run the router asks each
configured provider for its model list (`GET {base}/models`) and picks the first id matching the tier's
patterns. On a rate limit, quota error or bad output it falls through to the next provider for that tier.

Tiers:
  small  - cheap, fast: classification, short extraction
  large  - strongest free model: analysis, writing
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field

import httpx

log = logging.getLogger("metalscout.agents")

# Defaults; override any field under `agents.providers.<name>` in metalscout.yaml.
PROVIDERS: dict[str, dict] = {
    "groq": {"base": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY", "rpm": 25,
             "small": ["llama-3.1-8b", "gpt-oss-20b", "llama"], "large": ["llama-3.3-70b", "gpt-oss-120b", "qwen", "llama"]},
    "gemini": {"base": "https://generativelanguage.googleapis.com/v1beta/openai", "key_env": "GEMINI_API_KEY", "rpm": 8,
               "small": ["gemini-flash-lite-latest", "flash-lite", "flash"],
               "large": ["gemini-flash-latest", "flash-latest", "gemini-pro-latest", "flash", "gemma"]},
    "cerebras": {"base": "https://api.cerebras.ai/v1", "key_env": "CEREBRAS_API_KEY", "rpm": 25,
                 "small": ["llama3.1-8b", "llama"], "large": ["llama-3.3-70b", "gpt-oss-120b", "qwen", "llama"]},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY", "rpm": 15,
                   "small": ["openrouter/free"], "large": ["openrouter/free"], "fixed_models": ["openrouter/free"]},
    "ollama": {"base": "http://localhost:11434/v1", "base_env": "OLLAMA_BASE_URL", "key_env": "", "rpm": 600, "local": True,
               "small": ["qwen2.5:7b", "qwen", "llama3", "gemma", "mistral"], "large": ["qwen2.5:14b", "qwen", "mistral", "llama3", "gemma"]},
}
# never use <=3B models for the "large" tier (they paraphrase instead of quoting, so most facts get rejected)
TINY_MODEL = re.compile(r"(?<![\d.])(0\.5|1|1\.5|2|3)b|[-:](mini|tiny|nano)", re.I)
SKIP_MODEL = re.compile(r"embed|whisper|tts|guard|vision|image|audio|transcri|search|preview-tts|veo|imagen", re.I)


@dataclass
class Result:
    text: str
    data: dict | None
    provider: str
    model: str
    tokens: int
    latency_ms: int


@dataclass
class Provider:
    name: str
    base: str
    key: str
    rpm: int
    patterns: dict
    models: list[str] = field(default_factory=list)
    last_call: float = 0.0
    cooldown_until: float = 0.0
    bad: set = field(default_factory=set)

    def pick(self, tier: str) -> str | None:
        for pat in self.patterns.get(tier, []):
            for m in self.models:
                if m in self.bad:
                    continue
                if pat.lower() in m.lower() and not (tier == "large" and TINY_MODEL.search(m)):
                    return m
        return None


class BudgetExceeded(RuntimeError):
    pass


class Router:
    def __init__(self, cfg: dict):
        ac = cfg.get("agents", {})
        self.order: list[str] = ac.get("order", ["groq", "cerebras", "gemini", "openrouter", "ollama"])
        self.max_calls: int = ac.get("max_calls_per_run", 150)
        self.timeout: float = ac.get("timeout_s", 60)
        self.max_wait_s: float = ac.get("max_wait_s", 90)  # per call, when every provider is cooling down
        self.calls = 0
        self.providers: list[Provider] = []
        overrides = ac.get("providers", {}) or {}
        for name in self.order:
            spec = {**PROVIDERS.get(name, {}), **(overrides.get(name) or {})}
            if not spec:
                continue
            key = os.getenv(spec.get("key_env", ""), "") if spec.get("key_env") else ""
            base = os.getenv(spec.get("base_env", ""), "") or spec["base"]
            if spec.get("key_env") and not key:
                continue  # not configured
            p = Provider(name, base.rstrip("/"), key, int(spec.get("rpm", 10)),
                         {"small": spec.get("small", []), "large": spec.get("large", [])})
            p.models = list(spec.get("fixed_models", [])) or self._list_models(p)
            if p.models:
                self.providers.append(p)
            else:
                log.info("agents: provider %s has no usable models (offline or bad key)", name)

    # ---- discovery
    def _headers(self, p: Provider) -> dict:
        h = {"Content-Type": "application/json"}
        if p.key:
            h["Authorization"] = f"Bearer {p.key}"
        return h

    def _list_models(self, p: Provider) -> list[str]:
        try:
            r = httpx.get(f"{p.base}/models", headers=self._headers(p), timeout=10)
            r.raise_for_status()
            ids = [m.get("id", "") for m in r.json().get("data", [])]
            return [i.removeprefix("models/") for i in ids if i and not SKIP_MODEL.search(i)]
        except Exception as e:
            log.info("agents: listing models for %s failed: %s", p.name, str(e)[:120])
            return []

    @property
    def available(self) -> bool:
        return bool(self.providers)

    def roster(self) -> list[dict]:
        return [{"provider": p.name, "small": p.pick("small"), "large": p.pick("large")} for p in self.providers]

    # ---- calls
    def _throttle(self, p: Provider) -> None:
        gap = 60.0 / max(p.rpm, 1)
        wait = p.last_call + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        p.last_call = time.time()

    def complete(self, tier: str, system: str, user: str, want_json: bool = True, max_tokens: int = 1200) -> Result:
        """Try providers in order; within a provider try the tier's model, then the other tier's.
        A model that answers 400/404/422 is marked bad for the rest of the run (retired or not on this
        key's free tier). 402/403/429/5xx put the whole provider on cooldown."""
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"agent call budget ({self.max_calls}) used up")
        errors: list[str] = []
        other = "large" if tier == "small" else "small"
        waited = 0.0
        for _round in range(4):
            for p in self.providers:
                if time.time() < p.cooldown_until:
                    continue
                tried: set[str] = set()
                while True:
                    model = p.pick(tier) or p.pick(other)
                    if not model or model in tried:
                        break
                    tried.add(model)
                    res, provider_down = self._try(p, model, system, user, want_json, max_tokens, errors)
                    if res:
                        return res
                    if provider_down:
                        break
            # everyone is cooling down (rate limit / temporary outage): wait for the soonest one, briefly
            soonest = min((p.cooldown_until for p in self.providers if p.pick(tier) or p.pick(other)), default=0)
            gap = soonest - time.time()
            if gap <= 0 or waited + gap > self.max_wait_s:
                break
            log.info("agents: all providers cooling down, waiting %.0fs", gap)
            time.sleep(gap)
            waited += gap
        raise RuntimeError("all providers failed: " + ", ".join(errors[-6:]) if errors else "no provider available")

    def _try(self, p: Provider, model: str, system: str, user: str, want_json: bool, max_tokens: int,
             errors: list[str]) -> tuple[Result | None, bool]:
        body = {"model": model, "temperature": 0.1, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if want_json:
            body["response_format"] = {"type": "json_object"}
        for _ in range(3):
            if self.calls >= self.max_calls:
                raise BudgetExceeded(f"agent call budget ({self.max_calls}) used up")
            self._throttle(p)
            self.calls += 1
            t0 = time.time()
            try:
                r = httpx.post(f"{p.base}/chat/completions", headers=self._headers(p), json=body, timeout=self.timeout)
            except httpx.HTTPError as e:
                errors.append(f"{p.name}/{model}:{type(e).__name__}")
                return None, False
            if r.status_code == 400 and want_json and "response_format" in body:
                body.pop("response_format")  # some free models reject JSON mode; rely on the prompt
                continue
            if r.status_code in (402, 403, 429) or r.status_code >= 500:
                # 5xx = temporary overload: short pause; 429 = rate limit; 402/403 = quota/auth: give up for the run
                pause = 30 if r.status_code >= 500 else 60 if r.status_code == 429 else 3600
                p.cooldown_until = time.time() + pause
                errors.append(f"{p.name}:{r.status_code}")
                return None, True
            if r.status_code >= 400:
                p.bad.add(model)
                log.info("agents: %s/%s returned %s, skipping this model: %s", p.name, model, r.status_code, r.text[:160])
                errors.append(f"{p.name}/{model}:{r.status_code}")
                return None, False
            try:
                j = r.json()
                text = (j["choices"][0]["message"].get("content") or "").strip()
            except (KeyError, IndexError, ValueError, TypeError):
                errors.append(f"{p.name}/{model}:bad-response")
                continue
            data = parse_json(text) if want_json else None
            if want_json and data is None:
                errors.append(f"{p.name}/{model}:bad-json")
                continue
            tokens = (j.get("usage") or {}).get("total_tokens", 0) or 0
            return Result(text, data, p.name, model, int(tokens), int((time.time() - t0) * 1000)), False
        return None, False


def parse_json(text: str) -> dict | None:
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        v = json.loads(t)
        return v if isinstance(v, dict) else None
    except ValueError:
        m = re.search(r"\{.*\}", t, re.S)
        if m:
            try:
                v = json.loads(m.group(0))
                return v if isinstance(v, dict) else None
            except ValueError:
                return None
    return None
