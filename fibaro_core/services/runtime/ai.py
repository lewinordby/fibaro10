"""Ai services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from fibaro_core.export_definitions import AI_DATASETS
from fibaro_core.models import AiQueryLog
from fibaro_core.models import ControlConfig
from fibaro_core.models import ControlConfigHistory
from sqlalchemy import select
from sqlalchemy import text as sql_text
from sun2_helpers import repair_mojibake
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Optional
from value_parsing import int_value
import asyncio
import json
import os
import re
import urllib.request


@dataclass
class Dependencies:
    AI_CONFIG_KEY: Any
    OPENAI_MODEL: Any
    async_session: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def ai_jsonable(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: ai_jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [ai_jsonable(item) for item in value]
        return value

    def ai_dataset_overview() -> list[Dict[str, Any]]:
        return [
            {
                "key": key,
                "table": dataset["table"],
                "title": repair_mojibake(dataset["title"]),
                "description": repair_mojibake(dataset["description"]),
                "time_column": dataset.get("time_column"),
                "columns_count": len(dataset["columns"]),
            }
            for key, dataset in AI_DATASETS.items()
        ]

    def ai_dataset_schema(dataset_key: str) -> Dict[str, Any]:
        dataset = AI_DATASETS.get((dataset_key or "").strip())
        if not dataset:
            return {"ok": False, "error": "Ukjent datasett", "datasets": list(AI_DATASETS)}
        return {
            "ok": True,
            "key": dataset_key,
            "table": dataset["table"],
            "title": repair_mojibake(dataset["title"]),
            "description": repair_mojibake(dataset["description"]),
            "time_column": dataset.get("time_column"),
            "columns": dataset["columns"],
        }

    def validate_ai_sql(sql: str) -> tuple[bool, str]:
        sql_clean = (sql or "").strip()
        if not re.match(r"(?is)^select\b", sql_clean):
            return False, "Kun SELECT-spørringer er tillatt."
        if ";" in sql_clean or "--" in sql_clean or "/*" in sql_clean or "*/" in sql_clean:
            return False, "Kommentarer og flere SQL-setninger er ikke tillatt."
        forbidden = r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|execute|call|merge|vacuum|analyze)\b"
        if re.search(forbidden, sql_clean, flags=re.IGNORECASE):
            return False, "Spørringen inneholder ikke-tillatte SQL-kommandoer."
        from_match = re.search(r"(?is)\bfrom\b(.*?)(\bwhere\b|\bgroup\b|\border\b|\blimit\b|$)", sql_clean)
        if from_match and "," in from_match.group(1):
            return False, "Bruk eksplisitt JOIN i stedet for kommaseparerte tabeller."
        allowed_tables = {dataset["table"].lower() for dataset in AI_DATASETS.values()}
        used_tables = {
            match.group(1).split(".")[-1].strip('"').lower()
            for match in re.finditer(r"(?is)\b(?:from|join)\s+([a-zA-Z_][\w.]*)", sql_clean)
        }
        if not used_tables:
            return False, "Fant ingen tabell i spørringen."
        unknown = sorted(table for table in used_tables if table not in allowed_tables)
        if unknown:
            return False, f"Tabellen er ikke godkjent for AI-søk: {', '.join(unknown)}"
        return True, ""

    async def run_safe_ai_sql(sql: str, limit: int = 200) -> Dict[str, Any]:
        async_session = dependencies.async_session
        ok, error = validate_ai_sql(sql)
        if not ok:
            return {"ok": False, "error": error, "rows": []}
        safe_limit = max(1, min(int_value(limit) or 200, 500))
        wrapped_sql = f"SELECT * FROM ({sql.strip()}) AS ai_query LIMIT {safe_limit}"
        async with async_session() as session:
            result = await session.execute(sql_text(wrapped_sql))
            rows = [dict(row._mapping) for row in result.fetchall()]
        return {
            "ok": True,
            "limit": safe_limit,
            "count": len(rows),
            "rows": ai_jsonable(rows),
        }

    def ai_tools_definition() -> list[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "list_datasets",
                "description": "Lister alle datasett og tabeller som kan brukes til analyse.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "type": "function",
                "name": "get_dataset_schema",
                "description": "Henter tabellnavn, kolonner og beskrivelse for ett datasett.",
                "parameters": {
                    "type": "object",
                    "properties": {"dataset": {"type": "string"}},
                    "required": ["dataset"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "run_safe_sql",
                "description": "Kjører en trygg SELECT-spørring mot godkjente tabeller. Bruk alltid LIMIT eller argumentet limit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                    },
                    "required": ["sql"],
                    "additionalProperties": False,
                },
            },
        ]

    async def run_ai_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "list_datasets":
            return {"ok": True, "datasets": ai_dataset_overview()}
        if name == "get_dataset_schema":
            return ai_dataset_schema(str(arguments.get("dataset") or ""))
        if name == "run_safe_sql":
            return await run_safe_ai_sql(str(arguments.get("sql") or ""), int_value(arguments.get("limit")) or 200)
        return {"ok": False, "error": f"Ukjent verktøy: {name}"}

    def openai_env_api_key() -> str:
        return (os.getenv("OPENAI_API_KEY") or "").strip()

    def mask_secret(value: Optional[str]) -> str:
        if not value:
            return ""
        value = str(value)
        if len(value) <= 10:
            return "********"
        return f"{value[:7]}...{value[-4:]}"

    async def get_ai_config() -> ControlConfig:
        AI_CONFIG_KEY = dependencies.AI_CONFIG_KEY
        OPENAI_MODEL = dependencies.OPENAI_MODEL
        async_session = dependencies.async_session
        async with async_session() as session:
            row = (await session.execute(select(ControlConfig).where(ControlConfig.key == AI_CONFIG_KEY))).scalars().first()
            if row:
                return row
            row = ControlConfig(
                key=AI_CONFIG_KEY,
                version=1,
                values={"openai_api_key": "", "openai_model": OPENAI_MODEL},
                updated_by="system",
            )
            session.add(row)
            session.add(
                ControlConfigHistory(
                    config_key=AI_CONFIG_KEY,
                    version=1,
                    values={"openai_api_key": "", "openai_model": OPENAI_MODEL},
                    changed_by="system",
                    reason="AI-innstillinger opprettet",
                )
            )
            await session.commit()
            await session.refresh(row)
            return row

    async def effective_openai_settings() -> Dict[str, Any]:
        OPENAI_MODEL = dependencies.OPENAI_MODEL
        env_key = openai_env_api_key()
        row = await get_ai_config()
        values = row.values or {}
        stored_key = str(values.get("openai_api_key") or "").strip()
        stored_model = str(values.get("openai_model") or "").strip()
        return {
            "api_key": env_key or stored_key,
            "source": "Servermiljøvariabel" if env_key else ("App-innstilling" if stored_key else "Mangler"),
            "has_env_key": bool(env_key),
            "has_stored_key": bool(stored_key),
            "stored_key_masked": mask_secret(stored_key),
            "model": stored_model or OPENAI_MODEL,
            "config": row,
        }

    def openai_responses_request(payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        if not api_key:
            raise RuntimeError("OpenAI API key mangler.")
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=75) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI svarte {exc.code}: {body[:800]}") from exc

    def response_output_text(response: Dict[str, Any]) -> str:
        if response.get("output_text"):
            return str(response["output_text"]).strip()
        parts = []
        for item in response.get("output", []) or []:
            if item.get("type") != "message":
                continue
            for content in item.get("content", []) or []:
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    parts.append(str(content["text"]))
        return "\n".join(parts).strip()

    def response_function_calls(response: Dict[str, Any]) -> list[Dict[str, Any]]:
        return [item for item in response.get("output", []) or [] if item.get("type") == "function_call"]

    async def ask_ai(question: str, username: str) -> Dict[str, Any]:
        question = (question or "").strip()
        if not question:
            return {"ok": False, "answer": "", "error": "Skriv inn et spørsmål først.", "tool_calls": []}
        openai_settings = await effective_openai_settings()
        api_key = openai_settings["api_key"]
        model = openai_settings["model"]
        if not api_key:
            return {
                "ok": False,
                "answer": "",
                "error": "OpenAI API key mangler. Legg den inn under AI > Innstillinger eller som OPENAI_API_KEY på serveren.",
                "tool_calls": [],
            }

        system_prompt = (
            "Du er analyseassistent for SUN2 Lillehammer sin Fibaro10-applikasjon. "
            "Svar på norsk, kort og konkret, men forklar metode når tallene kan misforstås. "
            "Du har bare lov til å bruke verktøyene for å se datasett, skjema og lese data. "
            "Ikke finn opp tall. Hvis data mangler, si det tydelig. "
            "Når du trenger data, bruk først list_datasets eller get_dataset_schema, og kjør deretter run_safe_sql. "
            "SQL skal være enkel SELECT mot godkjente tabeller."
        )
        tools = ai_tools_definition()
        conversation_items = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": question}],
            }
        ]
        payload = {
            "model": model,
            "instructions": system_prompt,
            "tools": tools,
            "input": conversation_items,
        }
        response = await asyncio.to_thread(openai_responses_request, payload, api_key)
        tool_log: list[Dict[str, Any]] = []

        for _ in range(6):
            calls = response_function_calls(response)
            if not calls:
                answer = response_output_text(response)
                return {"ok": bool(answer), "answer": answer, "error": "" if answer else "Fikk ikke svar fra modellen.", "tool_calls": tool_log}

            outputs = []
            for call in calls:
                try:
                    args = json.loads(call.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await run_ai_tool(call.get("name") or "", args)
                tool_log.append(
                    {
                        "name": call.get("name"),
                        "arguments": args,
                        "ok": result.get("ok", True),
                        "count": result.get("count"),
                        "error": result.get("error"),
                    }
                )
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.get("call_id"),
                        "output": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
            conversation_items.extend(response.get("output", []) or [])
            conversation_items.extend(outputs)
            response = await asyncio.to_thread(
                openai_responses_request,
                {
                    "model": model,
                    "instructions": system_prompt,
                    "tools": tools,
                    "input": conversation_items,
                },
                api_key,
            )

        return {"ok": False, "answer": response_output_text(response), "error": "AI-søket stoppet etter for mange verktøykall.", "tool_calls": tool_log}

    async def recent_ai_logs(limit: int = 10) -> list[AiQueryLog]:
        async_session = dependencies.async_session
        async with async_session() as session:
            result = await session.execute(select(AiQueryLog).order_by(AiQueryLog.timestamp.desc()).limit(limit))
            return result.scalars().all()

    return {
        "ai_dataset_overview": ai_dataset_overview,
        "ai_dataset_schema": ai_dataset_schema,
        "ai_jsonable": ai_jsonable,
        "ai_tools_definition": ai_tools_definition,
        "ask_ai": ask_ai,
        "effective_openai_settings": effective_openai_settings,
        "get_ai_config": get_ai_config,
        "mask_secret": mask_secret,
        "openai_env_api_key": openai_env_api_key,
        "openai_responses_request": openai_responses_request,
        "recent_ai_logs": recent_ai_logs,
        "response_function_calls": response_function_calls,
        "response_output_text": response_output_text,
        "run_ai_tool": run_ai_tool,
        "run_safe_ai_sql": run_safe_ai_sql,
        "validate_ai_sql": validate_ai_sql,
    }
