"""Multi-agent IRIS class compatibility assistant.

Architecture (OpenAI Agents SDK):
    Classifier ──▶ {Catalog | VersionHistory} ──▶ Synthesizer

The Classifier routes the question. Catalog tells you whether a class
exists in the running IRIS instance (live REST, curated fallback).
VersionHistory answers "when was X introduced" from a hand-curated JSON.
Synthesizer composes the final answer with citations.

Usage:
    python main.py "Is %SQL.Statement available in iris20253?"
    python main.py "When was the first time %Library.DynamicArray came into existence?"
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY missing from .env", file=sys.stderr)
    sys.exit(1)

from agents import Agent, Runner, function_tool  # noqa: E402

import iris_catalog  # noqa: E402


# ---------- Tools ----------

@function_tool
def tool_class_exists(class_name: str) -> dict:
    """Check if an IRIS class exists in the currently running instance.

    Args:
        class_name: Fully qualified class name, e.g. "%SQL.Statement".
    """
    return iris_catalog.class_exists_in_iris(class_name)


@function_tool
def tool_iris_version() -> dict:
    """Return the version of the running IRIS instance (or note if unreachable)."""
    return iris_catalog.get_iris_version()


@function_tool
def tool_version_history(class_name: str) -> dict:
    """Look up curated history for a class: when introduced, which releases include it, purpose."""
    return iris_catalog.lookup_version_history(class_name)


@function_tool
def tool_normalize_release(release_label: str) -> dict:
    """Normalize informal release labels like 'iris20253' or 'IRIS 2025.3' to canonical '2025.3'."""
    return {"normalized": iris_catalog.normalize_iris_release(release_label)}


# ---------- Agents ----------

catalog_agent = Agent(
    name="CatalogAgent",
    instructions=(
        "You gather facts about whether an IRIS class exists in the running instance.\n"
        "STEP 1: Call tool_class_exists with the class name as the user wrote it (preserve %).\n"
        "STEP 2: If the user mentioned a release like 'iris20253', also call tool_normalize_release.\n"
        "STEP 3: Once you have the tool results, you MUST hand off to SynthesizerAgent. "
        "Pass along the raw tool results (including the 'source' field — 'iris_live' or 'curated_fallback') "
        "so the synthesizer can cite correctly.\n"
        "Do NOT compose the final user answer yourself."
    ),
    tools=[tool_class_exists, tool_iris_version, tool_normalize_release],
    model="gpt-4.1-mini",
)

version_history_agent = Agent(
    name="VersionHistoryAgent",
    instructions=(
        "You gather facts about when an IRIS class was first introduced.\n"
        "STEP 1: Call tool_version_history with the exact class name (preserve %).\n"
        "STEP 2: Once you have the tool result, you MUST hand off to SynthesizerAgent. "
        "Pass along the raw tool result so the synthesizer can compose the answer with a citation.\n"
        "Do NOT compose the final user answer yourself."
    ),
    tools=[tool_version_history],
    model="gpt-4.1-mini",
)

synthesizer_agent = Agent(
    name="SynthesizerAgent",
    instructions=(
        "You compose the final answer for the user. You MUST output exactly two parts, in this order:\n"
        "1) A 1-3 sentence answer paragraph.\n"
        "2) A new line beginning with the literal text 'Source: ' followed by the citation.\n\n"
        "The 'Source:' line is REQUIRED. If you do not include it, your output is wrong.\n\n"
        "Citation rules:\n"
        "- If a previous tool output contained 'source': 'iris_live', cite: 'live IRIS REST API (/api/atelier)'.\n"
        "- If a previous tool output contained 'source': 'curated_fallback', cite: 'curated knowledge base (version_history.json) — IRIS was unreachable'.\n"
        "- If the answer used tool_version_history, cite: 'curated knowledge base (version_history.json)'.\n"
        "- Never claim live IRIS unless you saw 'source': 'iris_live' verbatim.\n\n"
        "Example output:\n"
        "  Yes, %SQL.Statement is available in IRIS 2025.3.\n"
        "  Source: live IRIS REST API (/api/atelier)"
    ),
    model="gpt-4.1-mini",
)

classifier_agent = Agent(
    name="ClassifierAgent",
    instructions=(
        "You are the router for an IRIS class compatibility assistant. "
        "Read the user's question and decide which specialist to hand off to:\n"
        "  - 'catalog' for questions about whether a class is available / exists in a specific IRIS version\n"
        "  - 'history' for questions about when a class was introduced / first appeared\n"
        "Hand off to the matching specialist via the handoffs list. After the specialist replies, "
        "hand off to SynthesizerAgent for final formatting."
    ),
    handoffs=[catalog_agent, version_history_agent, synthesizer_agent],
    model="gpt-4.1-mini",
)

# Let specialists hand off to the synthesizer when done.
catalog_agent.handoffs = [synthesizer_agent]
version_history_agent.handoffs = [synthesizer_agent]


# ---------- Entry point ----------

async def answer(question: str) -> str:
    result = await Runner.run(classifier_agent, question, max_turns=12)
    return result.final_output


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python main.py "<question>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    print(f"\n[?] {question}\n")
    answer_text = asyncio.run(answer(question))
    print(answer_text)


if __name__ == "__main__":
    main()
