"""LangChain agent - `ChatOpenAI` factory.

Single source of truth for constructing `ChatOpenAI`, used by the agent
(`agent.py`) and, later, by insight/recommendation generation
(`backend/services`, Phase 5) - one place to keep the gateway workarounds
correct instead of duplicating them per call site (plan doc's Architecture
decision #5).

Ported from the additive/backup implementation's
`backend/ai/openai_client.py`, adapted to LangChain's `ChatOpenAI`:

- `OPENAI_BASE_URL` / `httpx.Client(verify=OPENAI_VERIFY_SSL)`: gateway
  compatibility for the workshop's shared AI portal, which can perform TLS
  interception on that traffic (breaks default certificate verification).
- Per-call random `seed`: the same gateway (a LiteLLM proxy) applies
  semantic response caching that can serve a stale/unrelated cached reply
  for what looks like a similar request. `ChatOpenAI` has no built-in
  per-call random seed, so `_GatewayChatOpenAI` overrides `_generate`/
  `_agenerate` to inject a fresh one on every call.
- `disable_streaming=True`: LangChain routes `.invoke()` through `_stream`
  instead of `_generate` whenever a streaming-capable callback handler is
  attached (as `AgentExecutor`'s tracing does by default) - `_generate`/
  `_agenerate` are the only methods overridden above, so that silently
  skipped the per-call seed above, letting the gateway's cache serve the
  same stale tool-call response every turn and made the agent call the
  same tool forever ("Agent stopped due to max iterations."). Forcing the
  non-streaming path is what actually makes the seed override take effect.
"""

import random
from functools import lru_cache
from typing import Any, List, Optional

import httpx
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI

from config.settings import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_VERIFY_SSL


class _GatewayChatOpenAI(ChatOpenAI):
    """`ChatOpenAI` that injects a fresh random `seed` on every call."""

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        kwargs["seed"] = random.randint(1, 999_999)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        kwargs["seed"] = random.randint(1, 999_999)
        return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    """Return the shared `ChatOpenAI` instance for the given temperature.

    Cached per-temperature so the agent (temperature 0.2) and any future
    higher-temperature call site share one client instance each, instead of
    reconstructing (and re-parsing `OPENAI_*` config) on every call.

    `http_client` is always built here (not only when `OPENAI_BASE_URL` is
    set) so `OPENAI_VERIFY_SSL=false` also works when going straight to
    `api.openai.com` from behind a network that TLS-intercepts *all*
    HTTPS traffic, not just gateway traffic - the same corporate-proxy
    class of issue `OPENAI_BASE_URL`'s TLS interception was already
    guarding against, just not gated on a gateway being configured.
    """
    http_client = httpx.Client(verify=OPENAI_VERIFY_SSL)
    return _GatewayChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        http_client=http_client,
        model=OPENAI_MODEL,
        temperature=temperature,
        disable_streaming=True,
    )
