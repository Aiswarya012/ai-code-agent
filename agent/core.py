import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from groq import BadRequestError, Groq
from groq.types.chat import ChatCompletion

from agent.parser import ToolExecutor
from agent.prompt import build_system_prompt, get_tool_definitions
from config import settings
from memory.chat_memory import ChatMemory
from memory.vector_store import VectorStore

logger = logging.getLogger("ai_agent.core")

FAILED_GENERATION_PATTERN = re.compile(r"<function=(\w+)\s*(\{.*?\})\s*</function>", re.DOTALL)
MAX_RETRIES = 2

EventCallback = Callable[[str, dict[str, Any]], None]


class AgentCore:
    def __init__(
        self,
        workspace: Path,
        on_event: EventCallback | None = None,
    ) -> None:
        self._workspace = workspace.resolve()
        self._data_dir = settings.resolve_data_dir(self._workspace)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._client = Groq(api_key=settings.groq_api_key)
        self._vector_store = VectorStore(data_dir=self._data_dir)
        self._executor = ToolExecutor(self._workspace, self._vector_store)
        self._memory = ChatMemory(self._data_dir / "memory.json")
        self._system_prompt = build_system_prompt(self._workspace)
        self._tool_definitions = get_tool_definitions()
        self.on_event = on_event

    @property
    def memory(self) -> ChatMemory:
        return self._memory

    @property
    def vector_store(self) -> VectorStore:
        return self._vector_store

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self.on_event:
            self.on_event(event_type, data)

    def run(self, query: str) -> str:
        logger.info("User query: %s", query)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
        ]
        messages.extend(self._memory.get_messages())
        messages.append({"role": "user", "content": query})

        response = self._call_llm(messages)

        for iteration in range(settings.max_agent_iterations):
            message = response.choices[0].message
            tool_calls = message.tool_calls

            if not tool_calls:
                break

            self._emit(
                "iteration",
                {"number": iteration + 1, "tool_count": len(tool_calls)},
            )
            logger.info(
                "Iteration %d: %d tool call(s)",
                iteration + 1,
                len(tool_calls),
            )

            messages.append(self._serialize_assistant_message(message))

            for tc in tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                logger.info("Tool call: %s(%s)", fn_name, fn_args)

                self._emit("tool_call_start", {"name": fn_name, "args": fn_args})
                result = self._executor.execute(fn_name, fn_args)
                self._emit(
                    "tool_call_end",
                    {"name": fn_name, "result_preview": result[:500]},
                )
                logger.debug("Tool result preview: %s", result[:200])

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

            response = self._call_llm(messages)

        final_text = response.choices[0].message.content or ""

        if not final_text:
            final_text = "I was unable to produce a response. Please try rephrasing your query."

        self._memory.add_user(query)
        self._memory.add_assistant(final_text)

        logger.info("Response length: %d chars", len(final_text))
        return final_text

    def _call_llm(self, messages: list[dict[str, Any]]) -> ChatCompletion:
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self._client.chat.completions.create(  # type: ignore[call-overload,no-any-return]
                    model=settings.model,
                    max_tokens=settings.max_tokens,
                    tools=self._tool_definitions,
                    tool_choice="auto",
                    messages=messages,
                )
            except BadRequestError as exc:
                if "tool_use_failed" not in str(exc) or attempt == MAX_RETRIES:
                    raise

                logger.warning("Groq tool_use_failed (attempt %d), recovering...", attempt + 1)
                recovered = self._recover_from_failed_tool_call(exc, messages)
                if recovered:
                    return recovered

                logger.warning("Recovery failed, retrying LLM call...")
                continue

        raise RuntimeError("Exhausted retries for LLM call")

    def _recover_from_failed_tool_call(
        self,
        exc: BadRequestError,
        messages: list[dict[str, Any]],
    ) -> ChatCompletion | None:
        error_body = exc.body if hasattr(exc, "body") else {}
        if not isinstance(error_body, dict):
            return None

        failed_gen = error_body.get("error", {}).get("failed_generation", "")
        if not failed_gen:
            return None

        match = FAILED_GENERATION_PATTERN.search(failed_gen)
        if not match:
            return None

        fn_name = match.group(1)
        try:
            fn_args = json.loads(match.group(2))
        except json.JSONDecodeError:
            return None

        logger.info("Recovered tool call from failed generation: %s(%s)", fn_name, fn_args)
        result = self._executor.execute(fn_name, fn_args)

        fake_tool_call_id = f"recovered_{fn_name}_{id(exc)}"
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": fake_tool_call_id,
                        "type": "function",
                        "function": {
                            "name": fn_name,
                            "arguments": json.dumps(fn_args),
                        },
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": fake_tool_call_id,
                "content": result,
            }
        )

        return self._client.chat.completions.create(  # type: ignore[call-overload,no-any-return]
            model=settings.model,
            max_tokens=settings.max_tokens,
            tools=self._tool_definitions,
            tool_choice="auto",
            messages=messages,
        )

    @staticmethod
    def _serialize_assistant_message(message: Any) -> dict[str, Any]:
        serialized: dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
        }
        if message.tool_calls:
            serialized["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        return serialized
