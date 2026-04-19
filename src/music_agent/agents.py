from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .ollama_client import ResilientOllamaClient
from .semantic_memory import SemanticMemory
from .tools import MusicHistoryTools


DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
PEAK_ENTITY_RE = re.compile(
    r"(?:когда|в какой день|в какие дни).*(?:чаще всего|больше всего).*(?:слушал|слушала|слушали)\s+(.+?)\??$",
    re.IGNORECASE,
)


def _ru_weeks_word(value: int) -> str:
    last_two = value % 100
    last_one = value % 10
    if 11 <= last_two <= 14:
        return "недель"
    if last_one == 1:
        return "неделю"
    if 2 <= last_one <= 4:
        return "недели"
    return "недель"


@dataclass
class AgentTask:
    tool_name: str
    params: Dict[str, Any]
    rationale: str


@dataclass
class AgentState:
    user_query: str
    planner_summary: str = ""
    tasks: List[AgentTask] = field(default_factory=list)
    memory_hits: List[Dict[str, Any]] = field(default_factory=list)
    factual_results: List[Dict[str, Any]] = field(default_factory=list)
    analysis: Dict[str, Any] | None = None
    verified: Dict[str, Any] | None = None
    final_answer: str = ""


class PlannerAgent:
    def __init__(self, llm: ResilientOllamaClient, tools: MusicHistoryTools) -> None:
        self.llm = llm
        self.tools = tools

    def plan(self, user_query: str) -> tuple[str, List[AgentTask]]:
        heuristic = self._heuristic_plan(user_query)
        if heuristic is not None:
            return heuristic

        prompt = (
            "Ты Planner Agent мультиагентной системы анализа музыкальной истории.\n"
            "У тебя есть набор доступных tools. Нужно составить минимальный план анализа.\n"
            "Нельзя придумывать несуществующие tools.\n"
            "Верни только JSON с полями summary и tasks.\n"
            "tasks должен быть массивом объектов с полями tool_name, params, rationale.\n"
            "Используй только tools из списка.\n\n"
            f"User query:\n{user_query}\n\n"
            f"Available tools:\n{json.dumps(self.tools.list_tool_specs(), ensure_ascii=False, indent=2)}"
        )
        llm_result = self.llm.generate(prompt, options={"temperature": 0.1, "num_predict": 350})
        parsed = _extract_json_payload(llm_result["response"])
        tasks = self._normalize_tasks(parsed.get("tasks", []))
        if tasks:
            return parsed.get("summary", "Planned with LLM."), tasks

        return self._fallback_plan(user_query)

    def _heuristic_plan(self, user_query: str) -> tuple[str, List[AgentTask]] | None:
        query = user_query.lower().strip()
        date_match = DATE_RE.search(user_query)
        peak_match = PEAK_ENTITY_RE.search(user_query)

        if peak_match:
            entity_name = peak_match.group(1).strip(" \"'«»")
            entity_type = "track" if any(token in query for token in ["трек", "песня"]) else "artist"
            return (
                "Find peak dates for the requested entity.",
                [AgentTask("entity_peak_dates", {"entity_type": entity_type, "entity_name": entity_name, "limit": 5}, "Need the dates with the highest frequency for the named entity.")],
            )
        if date_match:
            return (
                "Get the exact daily snapshot for the requested date.",
                [AgentTask("daily_snapshot", {"history_date": date_match.group(1)}, "The user asked about one specific date.")],
            )
        if "недел" in query:
            return (
                "Analyze weekly leaders and recurring patterns.",
                [AgentTask("weekly_trend_summary", {}, "Weekly pattern question.")],
            )
        if any(token in query for token in ["устойчив", "всплеск", "закреп", "мимолет", "мимолёт", "шум"]):
            dimension = "genre" if "жанр" in query else "artist"
            return (
                "Distinguish stable patterns from short-lived spikes.",
                [AgentTask("stability_vs_spikes", {"dimension": dimension}, "Need deterministic stable-vs-spike summary.")],
            )
        if "сравн" in query or "измен" in query or "динамик" in query or "как поменял" in query:
            return (
                "Compare two broad periods to describe changes over time.",
                [AgentTask("period_compare_summary", {"date_from": "2026-02-10", "split_date": "2026-03-15", "date_to": "2026-04-18"}, "Need a broad early-vs-late comparison.")],
            )
        if "жанр" in query:
            return (
                "Return top genres.",
                [AgentTask("top_entities", {"entity_type": "genres", "limit": 7}, "Genre-focused ranking question.")],
            )
        if "контекст" in query:
            return (
                "Return top contexts.",
                [AgentTask("top_entities", {"entity_type": "contexts", "limit": 6}, "Context-focused ranking question.")],
            )
        if "артист" in query or "исполнитель" in query:
            return (
                "Return top artists.",
                [AgentTask("top_entities", {"entity_type": "artists", "limit": 7}, "Artist ranking question.")],
            )
        if "трек" in query or "песня" in query:
            return (
                "Return top tracks.",
                [AgentTask("top_entities", {"entity_type": "tracks", "limit": 7}, "Track ranking question.")],
            )
        if any(token in query for token in ["что можно сказать", "проанализируй", "что видно", "что интересного", "мой вкус", "история прослушиваний"]):
            return (
                "Gather broad facts about the dataset and weekly patterns before analysis.",
                [
                    AgentTask("dataset_overview", {}, "Need the broad scope and date range first."),
                    AgentTask("weekly_trend_summary", {}, "Need recurring weekly patterns for open-ended analysis."),
                    AgentTask("stability_vs_spikes", {}, "Need stable-vs-spike signals for open-ended analysis."),
                    AgentTask("top_entities", {"entity_type": "artists", "limit": 7}, "Need stable artist leaders."),
                    AgentTask("top_entities", {"entity_type": "genres", "limit": 7}, "Need stable genre leaders."),
                ],
            )
        return None

    def _fallback_plan(self, user_query: str) -> tuple[str, List[AgentTask]]:
        return (
            "Fallback plan: broad overview plus top artists and genres.",
            [
                AgentTask("dataset_overview", {}, "Default fallback overview."),
                AgentTask("top_entities", {"entity_type": "artists", "limit": 5}, "Default artist ranking."),
                AgentTask("top_entities", {"entity_type": "genres", "limit": 5}, "Default genre ranking."),
            ],
        )

    def _normalize_tasks(self, raw_tasks: List[Any]) -> List[AgentTask]:
        specs = {spec["name"] for spec in self.tools.list_tool_specs()}
        tasks: List[AgentTask] = []
        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            tool_name = item.get("tool_name")
            if tool_name not in specs:
                continue
            params = item.get("params", {})
            rationale = item.get("rationale", "")
            tasks.append(AgentTask(tool_name, params if isinstance(params, dict) else {}, str(rationale)))
        return tasks


class MemoryAgent:
    def __init__(self, memory: SemanticMemory) -> None:
        self.memory = memory

    def run(self, user_query: str) -> List[Dict[str, Any]]:
        return self.memory.search(user_query, limit=4).get("data", [])


class DataAgent:
    def __init__(self, tools: MusicHistoryTools) -> None:
        self.tools = tools

    def run(self, tasks: List[AgentTask]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for task in tasks:
            result = self.tools.run_tool(task.tool_name, **task.params)
            results.append(
                {
                    "tool_name": task.tool_name,
                    "params": task.params,
                    "rationale": task.rationale,
                    "result": result,
                }
            )
        return results


class AnalysisAgent:
    def __init__(self, llm: ResilientOllamaClient) -> None:
        self.llm = llm

    def run(self, state: AgentState) -> Dict[str, Any]:
        if self._has_single_tool(state, "weekly_trend_summary"):
            return {
                "status": "ok",
                "model": "deterministic",
                "summary": "Built deterministic weekly trend claims.",
                "claims": self._weekly_claims(state.factual_results[0]["result"].get("data", {})),
                "caveats": [
                    "Weekly trends are based on top-ranked artists and genres per week, not on a full listening log."
                ],
            }
        if self._has_single_tool(state, "stability_vs_spikes"):
            return {
                "status": "ok",
                "model": "deterministic",
                "summary": "Built deterministic stable-vs-spike claims.",
                "claims": self._stability_claims(state.factual_results[0]["result"].get("data", {})),
                "caveats": ["Stable/spike signals are based on weekly top appearances, not on a full listening log."],
            }
        if self._has_single_tool(state, "period_compare_summary"):
            return {
                "status": "ok",
                "model": "deterministic",
                "summary": "Built deterministic period comparison claims.",
                "claims": self._period_compare_claims(state.factual_results[0]["result"].get("data", {})),
                "caveats": ["Comparison is based on top entities in two broad periods."],
            }

        prompt = (
            "Ты Analysis Agent мультиагентной системы анализа музыкальной истории.\n"
            "Твоя задача: на основе factual tool results и semantic memory сделать осторожный аналитический draft.\n"
            "Нельзя выдумывать факты. Нельзя строить психологические выводы.\n"
            "Верни только JSON с полями summary, claims, caveats.\n"
            "claims должен быть массивом коротких factual/analytical утверждений.\n"
            "caveats должен быть массивом ограничений.\n\n"
            f"User query:\n{state.user_query}\n\n"
            f"Planner summary:\n{state.planner_summary}\n\n"
            f"Memory hits:\n{json.dumps(state.memory_hits, ensure_ascii=False, indent=2)}\n\n"
            f"Factual tool results:\n{json.dumps(state.factual_results, ensure_ascii=False, indent=2)}"
        )
        llm_result = self.llm.generate(prompt, options={"temperature": 0.2, "num_predict": 450})
        parsed = _extract_json_payload(llm_result["response"])
        return {
            "status": "ok",
            "model": llm_result["model"],
            "summary": parsed.get("summary", ""),
            "claims": parsed.get("claims", []) if isinstance(parsed.get("claims", []), list) else [],
            "caveats": parsed.get("caveats", []) if isinstance(parsed.get("caveats", []), list) else [],
            "raw": llm_result["response"],
        }

    def _has_single_tool(self, state: AgentState, tool_name: str) -> bool:
        return len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == tool_name

    def _weekly_claims(self, data: Dict[str, Any]) -> List[str]:
        week_count = data.get("week_count", 0)
        genre_leaders = data.get("genre_leaders", [])
        artist_leaders = data.get("artist_leaders", [])
        recurring_artists = data.get("recurring_artists", [])
        leadership_changes = data.get("leadership_changes", [])
        claims: List[str] = []

        if genre_leaders:
            top_genre = genre_leaders[0]
            claims.append(
                f"Жанр {top_genre['genre']} был недельным лидером в {top_genre['weeks']} из {week_count} {_ru_weeks_word(week_count)}."
            )
        if artist_leaders:
            top_artist = artist_leaders[0]
            claims.append(
                f"Самым частым недельным лидером среди артистов был {top_artist['artist_name']}: "
                f"{top_artist['weeks']} {_ru_weeks_word(top_artist['weeks'])} из {week_count}."
            )
        if recurring_artists:
            recurring = recurring_artists[:3]
            recurring_line = ", ".join(
                f"{row['artist_name']} ({row['weeks']} {_ru_weeks_word(row['weeks'])} в топ-3)" for row in recurring
            )
            claims.append(f"Наиболее устойчиво в недельный топ-3 входили: {recurring_line}.")
        if leadership_changes:
            first_change = leadership_changes[0]
            claims.append(
                f"Смена недельного лидера по артистам впервые произошла в {first_change['week_id']}: "
                f"{first_change['from']} -> {first_change['to']}."
            )

        return claims

    def _stability_claims(self, data: Dict[str, Any]) -> List[str]:
        claims: List[str] = []
        dimension = data.get("dimension", "artist")
        stable_artists = data.get("stable_artists", [])
        spike_artists = data.get("spike_artists", [])
        stable_genres = data.get("stable_genres", [])
        spike_genres = data.get("spike_genres", [])
        change_count = data.get("leadership_change_count", 0)
        if dimension == "genre":
            if stable_genres:
                stable_line = ", ".join(f"{row['genre']} ({row['weeks']} недель)" for row in stable_genres[:3])
                claims.append(f"Наиболее устойчивыми по недельным топам жанров были: {stable_line}.")
            if spike_genres:
                spike_line = ", ".join(f"{row['genre']}" for row in spike_genres[:3])
                claims.append(f"Краткосрочными жанровыми всплесками выглядели: {spike_line}.")
            else:
                claims.append("Среди жанровых недельных лидеров почти не было краткосрочных всплесков.")
        else:
            if stable_artists:
                stable_line = ", ".join(f"{row['artist_name']} ({row['weeks']} недель)" for row in stable_artists[:3])
                claims.append(f"Наиболее устойчивыми по недельным топам были: {stable_line}.")
            if spike_artists:
                spike_line = ", ".join(f"{row['artist_name']}" for row in spike_artists[:3])
                claims.append(f"Краткосрочными недельными лидерами выглядели: {spike_line}.")
            claims.append(f"Смена недельного лидера по артистам происходила {change_count} раз.")
        return claims

    def _period_compare_claims(self, data: Dict[str, Any]) -> List[str]:
        claims: List[str] = []
        persisted_artists = data.get("artist_persistence", [])
        new_artists = data.get("artist_new_in_right", [])
        missing_artists = data.get("artist_missing_in_right", [])
        persisted_genres = data.get("genre_persistence", [])
        if persisted_artists:
            claims.append(f"В обоих периодах среди лидеров по артистам удержались: {', '.join(persisted_artists[:4])}.")
        if new_artists:
            claims.append(f"Во втором периоде среди лидеров появились новые артисты: {', '.join(new_artists[:4])}.")
        if missing_artists:
            claims.append(f"Часть лидеров первого периода исчезла из топа во втором: {', '.join(missing_artists[:4])}.")
        if persisted_genres:
            claims.append(f"По жанрам устойчивыми между периодами остались: {', '.join(persisted_genres[:4])}.")
        return claims


class VerifierAgent:
    def verify(self, state: AgentState) -> Dict[str, Any]:
        limitations = self._collect_limitations(state.factual_results)
        approved_claims: List[str] = []
        rejected_claims: List[Dict[str, str]] = []
        caveats = list((state.analysis or {}).get("caveats", []))

        for claim in (state.analysis or {}).get("claims", []):
            reason = self._claim_rejection_reason(claim)
            if reason is None:
                approved_claims.append(claim)
            else:
                rejected_claims.append({"claim": claim, "reason": reason})

        return {
            "status": "approved",
            "planner_summary": state.planner_summary,
            "factual_results": state.factual_results,
            "approved_claims": approved_claims,
            "rejected_claims": rejected_claims,
            "caveats": caveats,
            "limitations": limitations,
        }

    def _collect_limitations(self, factual_results: List[Dict[str, Any]]) -> List[str]:
        collected: List[str] = []
        for item in factual_results:
            for limitation in item.get("result", {}).get("limitations", []):
                if limitation not in collected:
                    collected.append(limitation)
        return collected

    def _claim_rejection_reason(self, claim: str) -> str | None:
        lowered = claim.lower()
        banned_patterns = [
            ("психолог", "psychological_inference"),
            ("эмоцион", "psychological_inference"),
            ("причин", "causal_claim"),
            ("доказывает", "overclaim"),
            ("указывает на", "overclaim"),
            ("маркетинг", "external_factor"),
            ("fanbase", "unsupported_external_term"),
            ("region", "unsupported_external_term"),
        ]
        for pattern, tag in banned_patterns:
            if pattern in lowered:
                return tag
        return None


class ReportAgent:
    def __init__(self, llm: ResilientOllamaClient) -> None:
        self.llm = llm

    def run(self, state: AgentState) -> str:
        if len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == "dataset_overview":
            return self._render_dataset_overview(state.verified or {})
        if len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == "top_entities":
            return self._render_top_entities(state.verified or {})
        if len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == "daily_snapshot":
            return self._render_daily_snapshot(state.verified or {})
        if len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == "entity_peak_dates":
            return self._render_entity_peak_dates(state.verified or {})
        if len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == "weekly_trend_summary":
            return self._render_weekly_trend_summary(state.verified or {})
        if len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == "stability_vs_spikes":
            return self._render_claims_only(state.verified or {})
        if len(state.factual_results) == 1 and state.factual_results[0]["tool_name"] == "period_compare_summary":
            return self._render_claims_only(state.verified or {})

        prompt = (
            "Ты Report Agent мультиагентной системы анализа музыкальной истории.\n"
            "Собери краткий grounded answer по-русски.\n"
            "Используй только approved_claims и factual_results ниже.\n"
            "Если данных недостаточно, явно скажи об этом.\n"
            "Не используй rejected_claims.\n\n"
            f"User query:\n{state.user_query}\n\n"
            f"Verified payload:\n{json.dumps(state.verified or {}, ensure_ascii=False, indent=2)}"
        )
        return self.llm.generate(prompt, options={"temperature": 0.2, "num_predict": 320})["response"]

    def _render_dataset_overview(self, verified: Dict[str, Any]) -> str:
        factual_results = verified.get("factual_results", [])
        factual = factual_results[0]["result"]["data"] if factual_results else {}
        contexts = factual.get("contexts", [])
        context_line = ", ".join(
            f"{row['context_type']} ({row['count']})" for row in contexts[:3] if row.get("context_type")
        )
        answer = (
            f"В данных {factual.get('snapshots', 0)} snapshot-ов, {factual.get('canonical_days', 0)} уникальных дней "
            f"и {factual.get('canonical_track_occurrences', 0)} уникальных вхождений треков за период "
            f"{factual.get('date_min')} - {factual.get('date_max')}."
        )
        if context_line:
            answer += f" Самые частые контексты: {context_line}."
        return answer

    def _render_top_entities(self, verified: Dict[str, Any]) -> str:
        factual_results = verified.get("factual_results", [])
        tool_payload = factual_results[0] if factual_results else {}
        params = tool_payload.get("params", {})
        factual = tool_payload.get("result", {})
        rows = factual.get("data", [])
        entity_type = params.get("entity_type", "entities")

        if not rows:
            return f"По запросу для {entity_type} ничего не найдено."

        labels = {
            "artists": "артисты",
            "tracks": "треки",
            "genres": "жанры",
            "contexts": "контексты",
        }
        label = labels.get(entity_type, entity_type)
        ranking = ", ".join(f"{row['entity']} ({row['count']})" for row in rows[:5])
        return f"Чаще всего встречаются такие {label}: {ranking}."

    def _render_daily_snapshot(self, verified: Dict[str, Any]) -> str:
        factual_results = verified.get("factual_results", [])
        factual = factual_results[0]["result"]["data"] if factual_results else {}
        history_date = factual.get("history_date")
        top_artists = factual.get("top_artists", [])
        top_genres = factual.get("top_genres", [])
        top_tracks = factual.get("top_tracks", [])

        if not top_artists and not top_genres and not top_tracks:
            return f"Для даты {history_date} в текущих данных не нашёл содержательных совпадений."

        parts = [f"По дате {history_date} видно такой срез."]
        if top_artists:
            artists_line = ", ".join(f"{row['artist_name']} ({row['count']})" for row in top_artists[:3])
            parts.append(f"Топ-артисты: {artists_line}.")
        if top_genres:
            genres_line = ", ".join(f"{row['genre']} ({row['count']})" for row in top_genres[:3])
            parts.append(f"Топ-жанры: {genres_line}.")
        if top_tracks:
            tracks_line = ", ".join(f"{row['title']} ({row['count']})" for row in top_tracks[:3])
            parts.append(f"Топ-треки: {tracks_line}.")
        return " ".join(parts)

    def _render_entity_peak_dates(self, verified: Dict[str, Any]) -> str:
        factual_results = verified.get("factual_results", [])
        factual = factual_results[0]["result"]["data"] if factual_results else {}
        entity_type = factual.get("entity_type")
        entity_name = factual.get("entity_name", "entity")
        peak_dates = factual.get("peak_dates", [])

        if not peak_dates:
            noun = "артист" if entity_type == "artist" else "трек"
            return f"Не нашёл совпадений для {noun} {entity_name} в текущих данных."

        top_row = peak_dates[0]
        answer = (
            f"Чаще всего {entity_name} встречался {top_row['history_date']} "
            f"({top_row['count']} вхождений)."
        )
        if len(peak_dates) > 1:
            next_dates = ", ".join(f"{row['history_date']} ({row['count']})" for row in peak_dates[1:4])
            answer += f" Ещё заметные даты: {next_dates}."
        return answer

    def _render_weekly_trend_summary(self, verified: Dict[str, Any]) -> str:
        factual_results = verified.get("factual_results", [])
        factual = factual_results[0]["result"]["data"] if factual_results else {}
        approved_claims = verified.get("approved_claims", [])
        week_count = factual.get("week_count")
        weeks = factual.get("weeks", [])

        parts: List[str] = []
        if week_count and weeks:
            parts.append(f"По {week_count} неделям в диапазоне {weeks[0]} - {weeks[-1]} видно несколько устойчивых паттернов.")
        else:
            parts.append("По недельной сводке видно несколько устойчивых паттернов.")
        parts.extend(approved_claims[:4])

        if verified.get("caveats") or verified.get("limitations"):
            parts.append("Это summary по недельным лидерам, а не полный лог прослушивания.")

        return " ".join(parts)

    def _render_claims_only(self, verified: Dict[str, Any]) -> str:
        claims = verified.get("approved_claims", [])
        caveats = verified.get("caveats", [])
        parts = claims[:4]
        if caveats:
            parts.append(caveats[0])
        return " ".join(parts)


def _extract_json_payload(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {"summary": "", "claims": [], "caveats": [], "raw": raw}
