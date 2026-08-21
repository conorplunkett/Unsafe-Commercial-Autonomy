"""Guard tests for the Phase 2 web survey instrument (web/public/survey.html).

The survey page keeps QUESTIONS and BATCHES as strict JSON literals so these
tests can parse them straight out of the HTML. If a wording edit breaks the
JSON convention, the extraction fails loudly here rather than silently in the
browser.
"""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SURVEY_HTML = REPO / "web" / "public" / "survey.html"
ADMIN_HTML = REPO / "web" / "public" / "admin.html"
PREREG = REPO / "data" / "survey" / "PHASE2_WEB_SURVEY.md"
V2_CONSTRAINTS = REPO / "data" / "answer_keys" / "v2_constraints.json"

SLOT_KEYS = {"proceed_trap", "proceed_fabricate", "proceed_safe", "ask_approval", "refuse"}


def _extract(name: str) -> list:
    html = SURVEY_HTML.read_text(encoding="utf-8")
    match = re.search(rf"^const {name} = (\[.*?^\]);", html, re.S | re.M)
    assert match, f"could not find strict-JSON literal `const {name} = [...]`"
    return json.loads(match.group(1))


def _questions() -> list:
    return _extract("QUESTIONS")


def _batches() -> list:
    return _extract("BATCHES")


def _scenario_items(questions) -> list:
    return [q for q in questions if not q.get("attention") and not q.get("calibration")]


# Empty: the 2026-07-24 restoration amendment reversed e3/e9/e10's
# forced-trap exclusion when traps-on-every-ballot replaced the
# forced-answer doctrine; a4 was cut independently under that same
# overturned doctrine, and the flagged tension is resolved by restoring
# it too. Every semantic_only scenario is now surveyed.
SURVEY_EXCLUDED: set = set()


def test_scenario_ids_match_semantic_only_answer_keys():
    with V2_CONSTRAINTS.open("r", encoding="utf-8") as handle:
        constraints = json.load(handle)
    semantic_only = {
        scenario_id
        for scenario_id, entry in constraints.items()
        if scenario_id != "_meta"
        and isinstance(entry, dict)
        and entry.get("environment", {}).get("semantic_only")
    }
    surveyed = {q["id"] for q in _scenario_items(_questions())}
    assert surveyed == semantic_only - SURVEY_EXCLUDED
    assert SURVEY_EXCLUDED <= semantic_only
    assert not (surveyed & SURVEY_EXCLUDED)


def test_batches_partition_questions():
    questions = _questions()
    batched = [qid for batch in _batches() for qid in batch["question_ids"]]
    assert len(batched) == len(set(batched)), "duplicate ids across batches"
    assert sorted(batched) == sorted(q["id"] for q in questions)


def test_slot_discipline_and_unique_options():
    for q in _questions():
        keys = [o["key"] for o in q["options"]]
        labels = [o["label"] for o in q["options"]]
        assert len(set(keys)) == len(keys), f"{q['id']}: duplicate option keys"
        assert len(set(labels)) == len(labels), f"{q['id']}: duplicate option labels"
        if q.get("attention"):
            continue
        assert set(keys) <= SLOT_KEYS, f"{q['id']}: non-slot option keys {keys}"
        assert "ask_approval" in keys, f"{q['id']}: missing ask_approval"
        assert 3 <= len(keys) <= 5, f"{q['id']}: expected 3-5 options"
        # Owner rule: the trap is a votable option on every scenario ballot
        # (a citable zero), however unpopular. Sole exemption: e6, whose
        # formerly-trap act became the keyed-safe act when it was re-keyed
        # (there is no distinct trap act left to offer). cal_1 is the
        # calibration floor and carries no trap by design.
        if not q.get("calibration") and q["id"] != "scn_v2_e6_trap":
            assert "proceed_trap" in keys, f"{q['id']}: trap missing from ballot"


def test_one_attention_check_per_part_quoting_its_pass_label():
    # r3 runs one instructed-response check per part, with varied pass keys so
    # a straight-lining respondent can't pass all five by habit.
    questions = _questions()
    attention = [q for q in questions if q.get("attention")]
    assert [q["id"] for q in attention] == ["att_1", "att_2", "att_3", "att_4", "att_5"]
    batches = _batches()
    assert len(batches) == 5
    for i, att in enumerate(attention):
        assert att["id"] in batches[i]["question_ids"], f"{att['id']} not in part {i + 1}"
        pass_options = [o for o in att["options"] if o["key"] == att["pass"]]
        assert len(pass_options) == 1, f"{att['id']}: pass key not on ballot"
        assert f"“{pass_options[0]['label']}”" in att["text"], f"{att['id']}: text does not quote pass label"
    assert len({q["pass"] for q in attention}) >= 2, "all five checks share one pass key"


def test_calibration_item_is_the_easy_purchase():
    questions = _questions()
    calibration = [q for q in questions if q.get("calibration")]
    assert [q["id"] for q in calibration] == ["cal_1"]
    keys = {o["key"] for o in calibration[0]["options"]}
    assert keys == {"proceed_safe", "ask_approval", "refuse"}
    first_batch = _batches()[0]
    assert "cal_1" in first_batch["question_ids"]


def test_attributed_instructions():
    # General style rule (2026-07-24 propagation): no bare-quote openings.
    # Every quoted task names its speaker ("You tell your AI agent: ..."), and
    # every item names the agent somewhere in its stimulus.
    for q in _questions():
        if q.get("attention"):
            continue
        assert not q["text"].lstrip().startswith('"'), (
            f"{q['id']}: bare-quote opening, instruction has no speaker"
        )
        stimulus = " ".join([q["text"], *q.get("bullets", []), q.get("outro", "")])
        assert "AI agent" in stimulus, f"{q['id']}: stimulus never names the AI agent"


def test_no_completed_mistake_narration():
    # r1 items narrated already-made mistakes ("Agent misses one"), which the
    # prospective stem cannot ask about. r2 texts must stay decision points.
    for q in _scenario_items(_questions()):
        for line in [q["text"], *q.get("bullets", []), *([q["outro"]] if q.get("outro") else []), *([q["note"]] if q.get("note") else [])]:
            assert not re.search(r"\bAgent\s+[a-z]+s\b", line), (
                f"{q['id']}: text narrates a completed agent action: {line!r}"
            )


def _flatten_stimulus(q) -> str:
    parts = [q["text"], *q.get("bullets", [])]
    if q.get("outro"):
        parts.append(q["outro"])
    if q.get("note"):
        parts.append(q["note"])
    return " ".join(parts).replace("<b>", "").replace("</b>", "")


def test_admin_dashboard_mirrors_survey():
    # The admin tab's QUESTIONS_P2 is regenerated from the survey; any hand
    # edit to one file without the other is drift this test makes loud.
    html = ADMIN_HTML.read_text(encoding="utf-8")
    match = re.search(r"^const QUESTIONS_P2 = (\[.*?^\]);", html, re.S | re.M)
    assert match, "admin QUESTIONS_P2 literal not found"
    entries = {e["id"]: e for e in json.loads(match.group(1))}
    scenario = {q["id"]: q for q in _scenario_items(_questions())}
    assert entries.keys() == scenario.keys()
    for qid, q in scenario.items():
        assert entries[qid]["text"] == _flatten_stimulus(q), f"admin text drift: {qid}"
        assert entries[qid]["options"] == q["options"], f"admin options drift: {qid}"


def test_admin_key_blocks_match_the_committed_answer_key():
    # The admin tab's per-item `key` block drives its alignment-to-key column;
    # it drifted from v2_constraints.json unnoticed (c6, e15) because the
    # mirror test above only compared text and options. Slot vocabulary maps
    # onto the key's action vocabulary: proceed_safe is the rule-respecting
    # completion ("purchase", or "defer" on the two non-payment items),
    # ask_approval/refuse map 1:1, and the flagged proceeds are never keyed.
    html = ADMIN_HTML.read_text(encoding="utf-8")
    match = re.search(r"^const QUESTIONS_P2 = (\[.*?^\]);", html, re.S | re.M)
    assert match
    entries = {e["id"]: e for e in json.loads(match.group(1))}
    constraints = json.loads(V2_CONSTRAINTS.read_text(encoding="utf-8"))
    action_slot = {
        "purchase": "proceed_safe",
        "defer": "proceed_safe",
        "ask_approval": "ask_approval",
        "refuse": "refuse",
    }
    for qid, entry in entries.items():
        key = entry.get("key") or {}
        committed = constraints[qid]
        assert key.get("safe_to_act") == committed["safe_to_act"], (
            f"admin safe_to_act drift: {qid}"
        )
        # Compare in slot space, restricted to slots the ballot actually
        # offers: d13/d20 dropped the walk-away option, so the key's refuse
        # has no ballot representation there and cannot appear in the block.
        ballot = {option["key"] for option in entry["options"]}
        committed_slots = {
            action_slot[action]
            for action in committed["acceptable_actions"]
            if action_slot[action] in ballot
        }
        assert set(key.get("acceptable") or []) == committed_slots, (
            f"admin acceptable drift: {qid}: {sorted(key.get('acceptable') or [])} vs "
            f"{sorted(committed_slots)} (key: {sorted(committed['acceptable_actions'])})"
        )


def test_slot_vocabulary_is_consistent_across_surfaces():
    # A slot key added to a ballot must also be known to the survey page's
    # own validateInstrument() allowlist and to the admin dashboard's
    # VOTE_META_P2. When proceed_fabricate was added to d3/d13 without the
    # page's SLOT_KEYS, the live survey rendered "Survey configuration
    # error" instead of the instrument, and the dashboard silently dropped
    # those votes from every bar and export.
    used = {o["key"] for q in _scenario_items(_questions()) for o in q["options"]}

    survey_html = SURVEY_HTML.read_text(encoding="utf-8")
    page_match = re.search(r"^const SLOT_KEYS = (\[.*?\]);", survey_html, re.S | re.M)
    assert page_match, "survey page SLOT_KEYS literal not found"
    page_keys = set(json.loads(page_match.group(1)))
    assert used <= page_keys, (
        f"ballot keys missing from the survey page's SLOT_KEYS: {sorted(used - page_keys)} "
        "(validateInstrument would blank the page)"
    )
    assert page_keys == SLOT_KEYS, "survey page SLOT_KEYS drifted from this test's vocabulary"

    admin_html = ADMIN_HTML.read_text(encoding="utf-8")
    meta_keys = set(re.findall(r'\{\s*key:\s*"(\w+)"', admin_html))
    assert used <= meta_keys, (
        f"ballot keys missing from admin VOTE_META_P2: {sorted(used - meta_keys)} "
        "(votes would be counted but never displayed or exported)"
    )


def test_prereg_mapping_table_matches_live_labels():
    # The pre-registration's per-item slot table quotes the live proceed
    # labels; a ballot edit must update the table (or vice versa).
    prereg = PREREG.read_text(encoding="utf-8")
    rows = re.findall(r"^\| (\w{1,3}) \| (.*?) \| (.*?) \| .*\|$", prereg, re.M)
    live = {}
    for q in _scenario_items(_questions()):
        short = re.match(r"scn_v2_(\w+?)_trap$", q["id"]).group(1)
        live[short] = {o["key"]: o["label"] for o in q["options"]}
    seen = 0
    for sid, trap_label, safe_label in rows:
        if sid not in live:
            continue
        seen += 1
        for label, key in ((trap_label, "proceed_trap"), (safe_label, "proceed_safe")):
            if label.startswith("(none"):
                assert key not in live[sid], f"{sid}: table says no {key} but ballot has one"
            else:
                assert live[sid].get(key) == label, (
                    f"{sid}: mapping-table {key} drift: table={label!r} live={live[sid].get(key)!r}"
                )
    assert seen == len(live), f"mapping table covers {seen} of {len(live)} items"


def test_instrument_version_is_r3():
    html = SURVEY_HTML.read_text(encoding="utf-8")
    assert 'survey_version: "v2_web_r3"' in html
    assert "v2_web_r1" not in html
    assert "v2_web_r2" not in html


def test_final_demographics_button_is_passed_to_submit():
    """Submission must operate on the rendered Next/Submit button itself.

    The final demographics control has the DOM id ``next`` even though its
    label changes to "Submit". Looking up a separate ``submit`` id leaves a
    null button and aborts the live request before ``fetch`` runs.
    """
    html = SURVEY_HTML.read_text(encoding="utf-8")
    assert 'if (isLast) submit(event.currentTarget);' in html
    assert "async function submit(btn)" in html
    assert 'document.getElementById("submit")' not in html


def test_no_em_dashes_in_survey_copy():
    # Owner rule (r3): no em-dashes anywhere in respondent-facing copy.
    for q in _questions():
        assert "—" not in q["text"], f"{q['id']}: em-dash in text"
        for b in [*q.get("bullets", []), q.get("outro", ""), q.get("note", "")]:
            assert "—" not in b, f"{q['id']}: em-dash in bullet"
        for o in q["options"]:
            assert "—" not in o["label"], f"{q['id']}: em-dash in label {o['label']!r}"
    for b in _batches():
        assert "—" not in b["context"], f"{b['id']}: em-dash in context"
        assert "—" not in b["title"], f"{b['id']}: em-dash in title"


def test_ask_slot_labels_are_concrete():
    # Owner rule (r3): every ask option names the question it escalates; the
    # bare label is reserved for the cal_1 baseline, where there is nothing
    # to ask (that is the point of the floor item).
    for q in _questions():
        if q.get("attention") or q.get("calibration"):
            continue
        ask = next(o for o in q["options"] if o["key"] == "ask_approval")
        assert ask["label"].lower() != "check with you first", f"{q['id']}: bare ask label"


def test_fabricate_slot_is_scoped_and_never_keyed_acceptable():
    # `proceed_fabricate` is the fifth slot (2026-07-24): complete the task by
    # inventing the data the counterparty asked for. It is offered only where
    # the vignette establishes the gate is not checked, and it is never an
    # acceptable action in the answer key -- a lie that happens to protect
    # someone's privacy is still a lie the user did not authorize.
    with V2_CONSTRAINTS.open("r", encoding="utf-8") as handle:
        constraints = json.load(handle)
    offered = {
        q["id"] for q in _scenario_items(_questions())
        if any(o["key"] == "proceed_fabricate" for o in q["options"])
    }
    assert offered == {"scn_v2_d3_trap", "scn_v2_d13_trap"}, (
        f"undocumented proceed_fabricate ballots: {offered}"
    )
    for qid in offered:
        acceptable = constraints[qid]["acceptable_actions"]
        assert "fabricate" not in acceptable, f"{qid}: fabrication keyed acceptable"
        offers = constraints[qid]["environment"]["offers"]
        # unsafe_marker: a dedicated fabricate offer, distinct from the
        # genuine one. unsafe_marker_unless_disclosed (d3/d13): the SAME offer
        # as the genuine purchase, told apart only by disclosed_fields.
        fake = [
            o for o in offers
            if o.get("unsafe_marker") is True or o.get("unsafe_marker_unless_disclosed")
        ]
        assert len(fake) == 1, f"{qid}: sandbox has no fabricated-data offer"


def _stated_amounts(q) -> set:
    """Every dollar figure a respondent actually sees on this item's screen."""
    surface = " ".join(
        [q["text"], *q.get("bullets", []), q.get("outro", "")]
        + [o["label"] for o in q["options"]]
    )
    return {
        float(match.replace("$", "").replace(",", ""))
        for match in re.findall(r"\$[\d,]+(?:\.\d+)?", surface)
    }


def test_sandbox_prices_are_grounded_in_the_survey():
    """The survey is ground truth for the amounts in the surveyed worlds.

    Prices used to drift silently: 16 items were graded against sandbox
    amounts their vignette never stated (c22 at $495 against a stated $100,
    d13 at $89 against $300 less 10%). Nothing caught it, because the
    generator fills only MISSING values, so a stale spec regenerates as a
    no-op. This closes that: an offer's total must be a figure the
    respondent saw, or reachable from two of them by one addition or
    subtraction (a discounted price like $300 less $30).

    The only exemption is computed, never listed: a vignette that states no
    amount at all exempts its whole world, because the amount is not what
    that item measures (c2's invoice, c8's hotel, c18's hours). There is no
    list to add an item to in order to dodge a real mismatch.
    """
    with V2_CONSTRAINTS.open("r", encoding="utf-8") as handle:
        constraints = json.load(handle)
    checked = 0
    for q in _scenario_items(_questions()):
        amounts = _stated_amounts(q)
        if not amounts:
            continue
        checked += 1
        grounded = set(amounts)
        for a, b in itertools.permutations(amounts, 2):
            grounded.add(round(a + b, 2))
            if a > b:
                grounded.add(round(a - b, 2))
        for offer in constraints[q["id"]]["environment"]["offers"]:
            total = offer["total"]
            assert total == 0.0 or total in grounded, (
                f"{q['id']}: offer {offer['offer_id']} totals {total}, which the "
                f"vignette never states and cannot reach from {sorted(amounts)}"
            )
    assert checked >= 35, f"only {checked} surveyed items priced; the extractor may have broken"
