"""Researcher docs must track the live sandbox tool names.

The 2026-08-26 `pay` -> `complete_checkout` rename updated every model-visible
surface but none of the five researcher docs, which kept describing (and, in
EPISODE_WALKTHROUGH's runnable snippet, calling) a tool that no longer exists.
This guard would have caught that drift the day it happened. Historical
CHANGELOG entries are deliberately out of scope.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    "README.md",
    "RUNBOOK.md",
    "EPISODE_WALKTHROUGH.md",
    "SANDBOX_OVERVIEW.md",
    "COLAB_GUIDE.md",
)


@pytest.mark.parametrize("doc", DOCS)
def test_docs_name_the_live_checkout_tool(doc):
    text = (ROOT / doc).read_text(encoding="utf-8")
    assert "`pay`" not in text, (
        f"{doc} still references the pre-2026-08-26 tool name `pay` — the live "
        "tool is complete_checkout"
    )
    assert "complete_checkout" in text, (
        f"{doc} never names the checkout tool; it should describe the live "
        "surface (complete_checkout)"
    )
