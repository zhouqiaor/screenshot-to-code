# pyright: reportUnknownVariableType=false
import base64
import copy
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from agent.providers.base import (
    EventSink,
    ExecutedToolCall,
    ProviderSession,
    ProviderTurn,
    StreamEvent,
)
from costs.pricing import MODEL_PRICING
from costs.token_usage import TokenUsage
from agent.state import ensure_str
from agent.tools import CanonicalToolDefinition, ToolCall, parse_json_arguments
from agent.tools.seed_tool_call import parse_seed_tool_call_content
from fs_logging.agent_runs import AgentRunRecorder
from fs_logging.prompt_reports import PromptReportLogger
from llm import Llm, get_openai_api_name, get_openai_reasoning_effort

logger = logging.getLogger(__name__)


def _convert_message_to_responses_input(
    message: ChatCompletionMessageParam,
    image_detail: str = "high",
) -> Dict[str, Any]:
    role = message.get("role", "user")
    content = message.get("content", "")

    if isinstance(content, str):
        return {"role": role, "content": content}

    parts: List[Dict[str, Any]] = []
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text":
                parts.append({"type": "input_text", "text": part.get("text", "")})
            elif part.get("type") == "image_url":
                image_url = part.get("image_url", {})
                parts.append(
                    {
                        "type": "input_image",
                        "image_url": image_url.get("url", ""),
                        "detail": image_detail,
                    }
                )

    return {"role": role, "content": parts}


def _get_image_detail_for_model(model: Llm) -> str:
    if get_openai_api_name(model) in {
        "gpt-5.5",
        "gpt-5.6-sol",
        "gpt-5.6-terra",
    }:
        return "original"
    return "high"


def _get_event_attr(event: Any, key: str, default: Any = None) -> Any:
    if hasattr(event, key):
        return getattr(event, key)
    if isinstance(event, dict):
        return event.get(key, default)
    return default


def _copy_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(schema)


def _nullable_type(type_value: Any) -> Any:
    if isinstance(type_value, list):
        if "null" not in type_value:
            return [*type_value, "null"]
        return type_value
    if isinstance(type_value, str):
        return [type_value, "null"]
    return type_value


def _make_responses_schema_strict(schema: Dict[str, Any]) -> Dict[str, Any]:
    schema_copy: Dict[str, Any] = _copy_schema(schema)

    def transform(node: Dict[str, Any], in_object_property: bool = False) -> None:
        node_type = node.get("type")

        if node_type == "object":
            node["additionalProperties"] = False
            properties = node.get("properties") or {}
            if isinstance(properties, dict):
                node["required"] = list(properties.keys())
                for prop in properties.values():
                    if isinstance(prop, dict):
                        transform(prop, in_object_property=True)
            return

        if node_type == "array":
            if in_object_property:
                node["type"] = _nullable_type(node_type)
            items = node.get("items")
            if isinstance(items, dict):
                transform(items, in_object_property=False)
            return

        if in_object_property and node_type is not None:
            node["type"] = _nullable_type(node_type)

    transform(schema_copy, in_object_property=False)
    return schema_copy


def serialize_openai_tools(
    tools: List[CanonicalToolDefinition],
) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    for tool in tools:
        schema = _make_responses_schema_strict(tool.parameters)
        serialized.append(
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": schema,
                "strict": True,
            }
        )
    return serialized
@dataclass
class OpenAIResponsesParseState:
    assistant_text: str = ""
    tool_calls: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    item_to_call_id: Dict[str, str] = field(default_factory=dict)
    output_items_by_index: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    saw_reasoning_summary_text_delta: bool = False
    last_emitted_reasoning_summary_part: str = ""
    turn_usage: TokenUsage | None = None


def _extract_openai_usage(response: Any) -> TokenUsage:
    """Extract unified token usage from an OpenAI Responses ``response.completed`` event.

    OpenAI includes cached tokens inside ``input_tokens``, so they are subtracted
    to get the non-cached input count.
    """
    usage = _get_event_attr(response, "usage")
    if usage is None:
        return TokenUsage()
    input_tokens = _get_event_attr(usage, "input_tokens", 0) or 0
    output_tokens = _get_event_attr(usage, "output_tokens", 0) or 0
    total_tokens = _get_event_attr(usage, "total_tokens", 0) or 0

    details = _get_event_attr(usage, "input_tokens_details") or {}
    cached_tokens = _get_event_attr(details, "cached_tokens", 0) or 0

    return TokenUsage(
        input=input_tokens - cached_tokens,
        output=output_tokens,
        cache_read=cached_tokens,
        cache_write=0,
        total=total_tokens,
    )


async def parse_event(
    event: Any,
    state: OpenAIResponsesParseState,
    on_event: EventSink,
) -> None:
    event_type = _get_event_attr(event, "type")
    if event_type in (
        "response.created",
        "response.completed",
        "response.done",
        "response.output_item.done",
    ):
        if event_type == "response.completed":
            response = _get_event_attr(event, "response")
            if response:
                state.turn_usage = _extract_openai_usage(response)
        if event_type == "response.output_item.done":
            output_index = _get_event_attr(event, "output_index")
            item = _get_event_attr(event, "item")
            if isinstance(output_index, int) and item:
                state.output_items_by_index[output_index] = item
        return

    if event_type == "response.output_text.delta":
        delta = _get_event_attr(event, "delta", "")
        if delta:
            state.assistant_text += delta
            await on_event(StreamEvent(type="assistant_delta", text=delta))
        return

    if event_type in (
        "response.reasoning_text.delta",
        "response.reasoning_summary_text.delta",
    ):
        delta = _get_event_attr(event, "delta", "")
        if delta:
            if event_type == "response.reasoning_summary_text.delta":
                state.saw_reasoning_summary_text_delta = True
            await on_event(StreamEvent(type="thinking_delta", text=delta))
        return

    if event_type in (
        "response.reasoning_summary_part.added",
        "response.reasoning_summary_part.done",
    ):
        if state.saw_reasoning_summary_text_delta:
            return
        part = _get_event_attr(event, "part") or {}
        text = _get_event_attr(part, "text", "")
        if text and text != state.last_emitted_reasoning_summary_part:
            state.last_emitted_reasoning_summary_part = text
            await on_event(StreamEvent(type="thinking_delta", text=text))
        return

    if event_type == "response.output_item.added":
        item = _get_event_attr(event, "item")
        item_type = _get_event_attr(item, "type") if item else None
        output_index = _get_event_attr(event, "output_index")
        if isinstance(output_index, int) and item:
            state.output_items_by_index.setdefault(output_index, item)

        if item and item_type in ("function_call", "custom_tool_call"):
            item_id = _get_event_attr(item, "id")
            call_id = _get_event_attr(item, "call_id") or item_id
            if item_id and call_id:
                state.item_to_call_id[item_id] = call_id
            if call_id:
                if item_id and item_id in state.tool_calls and item_id != call_id:
                    existing = state.tool_calls.pop(item_id)
                    state.tool_calls[call_id] = {
                        **existing,
                        "id": call_id,
                    }
                args_value = _get_event_attr(item, "arguments")
                if args_value is None and item_type == "custom_tool_call":
                    args_value = _get_event_attr(item, "input")
                state.tool_calls.setdefault(
                    call_id,
                    {
                        "id": call_id,
                        "name": _get_event_attr(item, "name"),
                        "arguments": args_value or "",
                    },
                )
                if args_value:
                    await on_event(
                        StreamEvent(
                            type="tool_call_delta",
                            tool_call_id=call_id,
                            tool_name=_get_event_attr(item, "name"),
                            tool_arguments=args_value,
                        )
                    )
        return

    if event_type in (
        "response.function_call_arguments.delta",
        "response.mcp_call_arguments.delta",
        "response.custom_tool_call_input.delta",
    ):
        item_id = _get_event_attr(event, "item_id")
        call_id = _get_event_attr(event, "call_id")
        if call_id and item_id:
            state.item_to_call_id[item_id] = call_id
        if not call_id:
            call_id = state.item_to_call_id.get(item_id) if item_id else None
        if not call_id and item_id:
            call_id = item_id
        if not call_id:
            return

        entry = state.tool_calls.setdefault(
            call_id,
            {
                "id": call_id,
                "name": _get_event_attr(event, "name"),
                "arguments": "",
            },
        )
        delta_value = _get_event_attr(event, "delta")
        if delta_value is None:
            delta_value = _get_event_attr(event, "input")
        entry["arguments"] += ensure_str(delta_value)

        await on_event(
            StreamEvent(
                type="tool_call_delta",
                tool_call_id=call_id,
                tool_name=entry.get("name"),
                tool_arguments=entry.get("arguments"),
            )
        )
        return

    if event_type not in (
        "response.function_call_arguments.done",
        "response.mcp_call_arguments.done",
        "response.custom_tool_call_input.done",
    ):
        return

    item_id = _get_event_attr(event, "item_id")
    call_id = _get_event_attr(event, "call_id")
    if call_id and item_id:
        state.item_to_call_id[item_id] = call_id
    if not call_id:
        call_id = state.item_to_call_id.get(item_id) if item_id else None
    if not call_id and item_id:
        call_id = item_id
    if not call_id:
        return

    entry = state.tool_calls.setdefault(
        call_id,
        {
            "id": call_id,
            "name": _get_event_attr(event, "name"),
            "arguments": "",
        },
    )
    final_value = _get_event_attr(event, "arguments")
    if final_value is None:
        final_value = _get_event_attr(event, "input")
    if final_value is None:
        final_value = entry["arguments"]
    entry["arguments"] = final_value
    if _get_event_attr(event, "name"):
        entry["name"] = _get_event_attr(event, "name")

    await on_event(
        StreamEvent(
            type="tool_call_delta",
            tool_call_id=call_id,
            tool_name=entry.get("name"),
            tool_arguments=entry.get("arguments"),
        )
    )

    output_index = _get_event_attr(event, "output_index")
    if (
        item_id
        and isinstance(output_index, int)
        and isinstance(state.output_items_by_index.get(output_index), dict)
    ):
        state.output_items_by_index[output_index] = {
            **state.output_items_by_index[output_index],
            "arguments": entry["arguments"],
            "call_id": call_id,
            "name": entry.get("name"),
        }


def _build_provider_turn(state: OpenAIResponsesParseState) -> ProviderTurn:
    output_items = [
        state.output_items_by_index[idx]
        for idx in sorted(state.output_items_by_index.keys())
        if state.output_items_by_index.get(idx)
    ]

    tool_items = [
        item
        for item in output_items
        if isinstance(item, dict)
        and item.get("type") in ("function_call", "custom_tool_call")
    ]

    tool_calls: List[ToolCall] = []
    if tool_items:
        for item in tool_items:
            raw_args = item.get("arguments")
            if raw_args is None and item.get("type") == "custom_tool_call":
                raw_args = item.get("input")
            args, error = parse_json_arguments(raw_args)
            if error:
                args = {"INVALID_JSON": ensure_str(raw_args)}
            call_id = item.get("call_id") or item.get("id")
            tool_calls.append(
                ToolCall(
                    id=call_id or f"call-{uuid.uuid4().hex[:6]}",
                    name=item.get("name") or "unknown_tool",
                    arguments=args,
                )
            )
    else:
        for entry in state.tool_calls.values():
            args, error = parse_json_arguments(entry.get("arguments"))
            if error:
                args = {"INVALID_JSON": ensure_str(entry.get("arguments"))}
            call_id = entry.get("id") or entry.get("call_id")
            tool_calls.append(
                ToolCall(
                    id=call_id or f"call-{uuid.uuid4().hex[:6]}",
                    name=entry.get("name") or "unknown_tool",
                    arguments=args,
                )
            )

    assistant_turn: List[Dict[str, Any]] = output_items if tool_calls else []

    return ProviderTurn(
        assistant_text=state.assistant_text,
        tool_calls=tool_calls,
        assistant_turn=assistant_turn,
    )


# ---------------------------------------------------------------------------
# Raw httpx fallback for Volcano Ark / doubao-seed-evolving.
#
# The OpenAI Python SDK (AsyncOpenAI) silently crashes when the request body
# is large (>10KB text + 165KB image data URL). The process is killed with no
# exception, no traceback, and no output from faulthandler. The workaround is
# to bypass the SDK entirely and POST directly via httpx.
# ---------------------------------------------------------------------------

# Models known to trigger the SDK silent crash — use raw httpx for these.
_VOLCANO_ARK_MODELS = {
    "doubao-seed-evolving",
    "doubao-seed-1.6-flash",
    "doubao-seed-1.8",
    "doubao-seed-1.6-vision",
    "doubao-seed-2-1-turbo-260628",
}


def _is_volcano_ark_model(model: Llm) -> bool:
    """Check if the model is served via Volcano Ark and may need raw httpx."""
    return get_openai_api_name(model) in _VOLCANO_ARK_MODELS


def _convert_responses_input_to_chat_messages(
    input_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert Responses-API input items back to chat/completions messages.

    The Responses API uses a flat list of items with ``role`` and ``content``
    fields. The chat/completions API uses the same structure but with
    ``image_url`` parts instead of ``input_image`` and ``text`` parts instead
    of ``input_text``.
    """
    messages: List[Dict[str, Any]] = []
    for item in input_items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type", "")
        # Skip non-message items (function_call_output, etc. are handled
        # separately by being converted to tool result messages)
        if item_type in ("function_call", "custom_tool_call"):
            # Previous assistant tool call — represent as assistant message
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": item.get("call_id") or item.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": item.get("name", ""),
                        "arguments": item.get("arguments", ""),
                    },
                }],
            })
            continue
        if item_type == "function_call_output":
            messages.append({
                "role": "tool",
                "tool_call_id": item.get("call_id", ""),
                "content": _stringify_output(item.get("output", "")),
            })
            continue

        role = item.get("role", "user")
        content = item.get("content")
        item_tool_calls = item.get("tool_calls")

        # Handle synthetic assistant message with tool_calls (from raw httpx
        # fallback path in append_tool_results)
        if role == "assistant" and item_tool_calls:
            chat_tool_calls: List[Dict[str, Any]] = []
            for tc in item_tool_calls:
                if not isinstance(tc, dict):
                    continue
                tc_id = tc.get("call_id") or tc.get("id", "")
                tc_name = tc.get("name", "")
                tc_args = tc.get("arguments", "")
                if isinstance(tc_args, dict):
                    tc_args = json.dumps(tc_args, ensure_ascii=False)
                chat_tool_calls.append({
                    "id": tc_id,
                    "type": "function",
                    "function": {
                        "name": tc_name,
                        "arguments": tc_args,
                    },
                })
            messages.append({
                "role": "assistant",
                "content": content if isinstance(content, str) and content else None,
                "tool_calls": chat_tool_calls,
            })
            continue

        if isinstance(content, str):
            messages.append({"role": role, "content": content})
        elif isinstance(content, list):
            parts: List[Dict[str, Any]] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type", "")
                if ptype == "input_text":
                    parts.append({"type": "text", "text": part.get("text", "")})
                elif ptype == "input_image":
                    image_url = part.get("image_url", "")
                    parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": part.get("detail", "high"),
                        },
                    })
            if parts:
                messages.append({"role": role, "content": parts})
    return messages


def _stringify_output(output: Any) -> str:
    """Convert a function_call_output ``output`` field to a string for the
    chat/completions ``tool`` message ``content`` field."""
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        # Extract text parts from the list
        texts: List[str] = []
        for part in output:
            if isinstance(part, dict):
                if part.get("type") == "input_text":
                    texts.append(part.get("text", ""))
        return "\n".join(texts) if texts else json.dumps(output)
    return json.dumps(output)


def _build_turn_from_raw_chat_response(
    response_data: Dict[str, Any],
) -> ProviderTurn:
    """Build a ProviderTurn from a raw chat/completions response.

    Handles both standard ``tool_calls`` field and ``<seed:tool_call>`` XML
    embedded in the message content.
    """
    choices = response_data.get("choices", [])
    assistant_text = ""
    tool_calls: List[ToolCall] = []

    if choices:
        message = choices[0].get("message", {})
        assistant_text = message.get("content") or ""

        # Try standard tool_calls field first
        std_tool_calls = message.get("tool_calls", [])
        if std_tool_calls:
            for tc in std_tool_calls:
                func = tc.get("function", {})
                args_raw = func.get("arguments", "{}")
                args, error = parse_json_arguments(args_raw)
                if error:
                    args = {"INVALID_JSON": ensure_str(args_raw)}
                tool_calls.append(ToolCall(
                    id=tc.get("id", f"call-{uuid.uuid4().hex[:6]}"),
                    name=func.get("name", "unknown_tool"),
                    arguments=args,
                ))
        elif assistant_text:
            # Try <seed:tool_call> XML extraction
            seed_calls = parse_seed_tool_call_content(assistant_text)
            for sc in seed_calls:
                tool_calls.append(ToolCall(
                    id=sc["id"],
                    name=sc["name"],
                    arguments=sc["arguments"],
                ))

    return ProviderTurn(
        assistant_text=assistant_text,
        tool_calls=tool_calls,
        assistant_turn=[],  # raw chat mode doesn't use Responses output items
    )


class OpenAIProviderSession(ProviderSession):
    def __init__(
        self,
        client: AsyncOpenAI,
        model: Llm,
        prompt_messages: List[ChatCompletionMessageParam],
        tools: List[Dict[str, Any]],
        recorder: Optional[AgentRunRecorder] = None,
        # Raw httpx fallback credentials (extracted from the AsyncOpenAI client
        # by the factory when the model is known to trigger SDK silent crashes,
        # e.g. doubao-seed-evolving on Volcano Ark).
        fallback_api_key: Optional[str] = None,
        fallback_base_url: Optional[str] = None,
    ):
        self._client = client
        self._model = model
        self._tools = tools
        self._total_usage = TokenUsage()
        self._recorder = recorder
        self._fallback_api_key = fallback_api_key
        self._fallback_base_url = fallback_base_url
        self._prompt_report_logger = PromptReportLogger(
            provider="openai",
            model=model,
            api_model_name=get_openai_api_name(model),
        )
        image_detail = _get_image_detail_for_model(model)
        self._input_items: List[Dict[str, Any]] = [
            _convert_message_to_responses_input(message, image_detail=image_detail)
            for message in prompt_messages
        ]

    async def _stream_turn_raw_httpx(self, on_event: EventSink) -> ProviderTurn:
        """Fallback: bypass the OpenAI SDK and POST directly via httpx.

        This is needed because ``AsyncOpenAI.responses.create()`` silently
        crashes (process killed, no exception) when the request body is large
        (>10KB text + 165KB image data URL) on Volcano Ark.

        Uses the ``chat/completions`` endpoint instead of the Responses API.
        The model returns ``<seed:tool_call>`` XML in the message content
        instead of standard ``tool_calls`` — this is handled by
        :func:`parse_seed_tool_call_content`.
        """
        api_key = self._fallback_api_key
        base_url = self._fallback_base_url
        if not api_key or not base_url:
            raise RuntimeError(
                "Raw httpx fallback requires api_key and base_url, but they "
                "were not provided. Pass fallback_api_key and fallback_base_url "
                "to OpenAIProviderSession."
            )

        model_name = get_openai_api_name(self._model)
        chat_messages = _convert_responses_input_to_chat_messages(self._input_items)

        # Build tools in chat/completions format (not Responses format)
        chat_tools: List[Dict[str, Any]] = []
        for tool in self._tools:
            chat_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            })

        body: Dict[str, Any] = {
            "model": model_name,
            "messages": chat_messages,
            "max_tokens": 50000,
        }
        if chat_tools:
            body["tools"] = chat_tools
            body["tool_choice"] = "auto"

        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body_json = json.dumps(body)
        logger.info(
            "[raw-httpx fallback] POST %s | model=%s | body=%d bytes",
            url,
            model_name,
            len(body_json),
        )
        if self._recorder is not None:
            self._recorder.record_llm_request("openai-raw-httpx", model_name, body)

        self._prompt_report_logger.record_request(body)

        timeout = httpx.Timeout(900.0, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            resp = await http_client.post(
                url,
                content=body_json.encode("utf-8"),
                headers=headers,
            )

            if resp.status_code != 200:
                error_text = resp.text[:1000]
                logger.error(
                    "[raw-httpx fallback] HTTP %d: %s",
                    resp.status_code,
                    error_text,
                )
                raise RuntimeError(
                    f"Raw httpx fallback failed: HTTP {resp.status_code}: {error_text}"
                )

            data = resp.json()
            # Extract usage
            usage_data = data.get("usage", {})
            input_tokens = usage_data.get("prompt_tokens", 0) or 0
            output_tokens = usage_data.get("completion_tokens", 0) or 0
            total_tokens = usage_data.get("total_tokens", 0) or 0
            # Volcano Ark puts reasoning tokens in completion_tokens_details
            details = usage_data.get("completion_tokens_details", {})
            reasoning_tokens = details.get("reasoning_tokens", 0) or 0

            turn_usage = TokenUsage(
                input=input_tokens,
                output=output_tokens,
                cache_read=0,
                cache_write=0,
                total=total_tokens,
            )
            self._prompt_report_logger.record_usage(turn_usage)
            self._total_usage.accumulate(turn_usage)

            # Build the turn
            turn = _build_turn_from_raw_chat_response(data)

            # Emit streaming events for the assistant text
            if turn.assistant_text:
                await on_event(StreamEvent(
                    type="assistant_delta",
                    text=turn.assistant_text,
                ))
            # Emit tool call deltas
            for tc in turn.tool_calls:
                await on_event(StreamEvent(
                    type="tool_call_delta",
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    tool_arguments=json.dumps(tc.arguments, ensure_ascii=False),
                ))

            logger.info(
                "[raw-httpx fallback] OK | input=%d output=%d "
                "reasoning=%d tool_calls=%d",
                input_tokens,
                output_tokens,
                reasoning_tokens,
                len(turn.tool_calls),
            )

            if self._recorder is not None:
                self._recorder.record_llm_response(
                    turn.assistant_text,
                    turn.tool_calls,
                    turn_usage,
                )

            return turn

    async def stream_turn(self, on_event: EventSink) -> ProviderTurn:
        model_name = get_openai_api_name(self._model)
        params: Dict[str, Any] = {
            "model": model_name,
            "input": self._input_items,
            "tools": self._tools,
            "tool_choice": "auto",
            "stream": True,
            "max_output_tokens": 50000,
        }
        if model_name == "gpt-5.4-2026-03-05":
            params["prompt_cache_retention"] = "24h"
        reasoning_effort = get_openai_reasoning_effort(self._model)
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort, "summary": "auto"}

        self._prompt_report_logger.record_request(params)
        if self._recorder is not None:
            self._recorder.record_llm_request("openai", model_name, params)

        # Volcano Ark / doubao models are known to silently crash the SDK
        # when the request body is large. Skip the SDK entirely for these.
        use_raw_httpx = _is_volcano_ark_model(self._model)

        if not use_raw_httpx:
            state = OpenAIResponsesParseState()
            try:
                stream = await self._client.responses.create(**params)  # type: ignore
                event_count = 0
                async for event in stream:  # type: ignore
                    event_count += 1
                    await parse_event(event, state, on_event)

                # Detect silent crash: if we got zero events and this is a
                # model known to silently crash on large request bodies,
                # attempt raw httpx fallback. For standard OpenAI models,
                # an empty stream is unusual but not necessarily a crash
                # (e.g. in tests with fake clients).
                if event_count == 0 and _is_volcano_ark_model(self._model):
                    logger.warning(
                        "[sdk] responses.create() returned 0 events for "
                        "model=%s — attempting raw httpx fallback",
                        model_name,
                    )
                    if self._fallback_api_key and self._fallback_base_url:
                        return await self._stream_turn_raw_httpx(on_event)
                    raise RuntimeError(
                        f"OpenAI SDK returned 0 events for model={model_name} "
                        "and no raw httpx fallback is configured."
                    )

                if state.turn_usage is not None:
                    self._prompt_report_logger.record_usage(state.turn_usage)
                    self._total_usage.accumulate(state.turn_usage)

                turn = _build_provider_turn(state)
                if self._recorder is not None:
                    self._recorder.record_llm_response(
                        turn.assistant_text, turn.tool_calls, state.turn_usage
                    )
                return turn

            except Exception as exc:
                # If the SDK raised an exception and we have fallback creds,
                # try the raw httpx path before propagating the error.
                if self._fallback_api_key and self._fallback_base_url:
                    logger.warning(
                        "[sdk] responses.create() raised %s: %s — "
                        "attempting raw httpx fallback",
                        type(exc).__name__,
                        exc,
                    )
                    return await self._stream_turn_raw_httpx(on_event)
                raise
        else:
            # Volcano Ark / doubao models: skip the SDK entirely to avoid
            # the silent crash on large request bodies.
            return await self._stream_turn_raw_httpx(on_event)

    def total_cost_usd(self) -> float | None:
        pricing = MODEL_PRICING.get(get_openai_api_name(self._model))
        if pricing is None:
            return None
        return self._total_usage.cost(pricing)

    @staticmethod
    def _image_ref(part: Any) -> str | None:
        """A public URL is sent as-is; local bytes become a base64 data URL."""
        if part.image_url:
            return part.image_url
        if part.data is not None:
            encoded = base64.b64encode(part.data).decode("ascii")
            return f"data:{part.mime_type};base64,{encoded}"
        return None

    async def append_tool_results(
        self,
        turn: ProviderTurn,
        executed_tool_calls: list[ExecutedToolCall],
    ) -> None:
        assistant_output_items = turn.assistant_turn or []
        if assistant_output_items:
            self._input_items.extend(assistant_output_items)
        elif turn.assistant_text or turn.tool_calls:
            # Raw httpx fallback mode: assistant_turn is empty, but we have
            # text and/or tool_calls. Add a synthetic assistant message item
            # so the conversation history stays consistent when converting
            # to chat/completions format.
            self._input_items.append({
                "role": "assistant",
                "content": turn.assistant_text or "",
                "tool_calls": [
                    {
                        "type": "function_call",
                        "call_id": tc.id,
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    }
                    for tc in turn.tool_calls
                ],
            })

        image_detail = _get_image_detail_for_model(self._model)
        tool_output_items: List[Dict[str, Any]] = []
        for executed in executed_tool_calls:
            result_json = json.dumps(executed.result.result)
            parts = executed.result.multimodal_parts or []
            output: Any = result_json
            if parts and executed.result.ok:
                # Responses lets function_call_output carry image content; keep
                # the text result first so the model still gets the structured
                # data (URLs, status) alongside the rendered images.
                output = [{"type": "input_text", "text": result_json}]
                for part in parts:
                    image_url = self._image_ref(part)
                    if image_url is None:
                        continue
                    output.append(
                        {
                            "type": "input_image",
                            "detail": image_detail,
                            "image_url": image_url,
                        }
                    )
            tool_output_items.append(
                {
                    "type": "function_call_output",
                    "call_id": executed.tool_call.id,
                    "output": output,
                }
            )
        self._input_items.extend(tool_output_items)

    async def close(self) -> None:
        u = self._total_usage
        model_name = get_openai_api_name(self._model)
        pricing = MODEL_PRICING.get(model_name)
        cost_str = f" cost=${u.cost(pricing):.4f}" if pricing else ""
        cache_hit_rate_str = f" cache_hit_rate={u.cache_hit_rate_percent():.2f}%"
        print(
            f"[TOKEN USAGE] provider=openai model={model_name} | "
            f"input={u.input} output={u.output} "
            f"cache_read={u.cache_read} cache_write={u.cache_write} "
            f"total={u.total}{cache_hit_rate_str}{cost_str}"
        )
        await self._client.close()
