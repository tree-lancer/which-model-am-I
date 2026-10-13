import itertools
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import compile_questionnaire as compiler


ROOT = Path(__file__).resolve().parents[3]
VERSION = sys.argv[1] if len(sys.argv) > 1 else json.loads((ROOT / "data" / "questionnaires" / "current.json").read_text(encoding="utf-8"))["version"]
FOLDER = ROOT / "data" / "questionnaires" / VERSION


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def comparable_question(question):
    return {**question, "options": sorted(question["options"], key=lambda option: option["id"])}


bank = read_json(FOLDER / "question_bank.json")
quiz = read_json(FOLDER / "questionnaire.json")
current = read_json(ROOT / "data" / "questionnaires" / "current.json")
require(quiz == current, "Current questionnaire differs from requested version")
require(quiz["schemaVersion"] == 2, "Expected version 2 schema")
require(quiz["version"] == bank["version"] == VERSION, "Version mismatch")
require(quiz["asOf"] == bank["asOf"], "Compilation date mismatch")
require(date.fromisoformat(quiz["asOf"]) <= date.today(), "Compilation date is in the future")
require([item["date"] for item in bank["checkpoints"]] == sorted(item["date"] for item in bank["checkpoints"]), "Checkpoint dates are unsorted")
bank, as_of = compiler.load_bank(VERSION)
rows = compiler.load_catalog(as_of)
checkpoints = bank["checkpoints"]
require(quiz["catalogSize"] == len(rows), "Catalog size mismatch")
require(quiz["questionCount"] == 3 * len(checkpoints), "Question count mismatch")
require(len(checkpoints) >= 3, "Too few time checkpoints")
for previous, following in zip(checkpoints, checkpoints[1:]):
    require((date.fromisoformat(following["date"]) - date.fromisoformat(previous["date"])).days >= 30, f"Checkpoints too close: {previous['id']}, {following['id']}")

bank_by_id = {item["id"]: item for item in checkpoints}
seen_events = set()
seen_sources = set()
date_report = []
for checkpoint in checkpoints:
    boundary = date.fromisoformat(checkpoint["date"])
    certain_before = 0
    possibly_after = 0
    for row in rows:
        lower, upper = compiler.parse_cutoff(row["cutoff"])
        certain_before += upper is not None and upper < boundary
        possibly_after += upper is None or upper >= boundary
    require(certain_before > 0 and possibly_after > 0, f"Checkpoint cannot divide catalog: {checkpoint['id']}")
    event_dates = [date.fromisoformat(question["eventDate"]) for question in checkpoint["questions"]]
    span = (max(event_dates) - min(event_dates)).days
    require(span <= 90, f"Events span more than 90 days: {checkpoint['id']}")
    domains = set()
    for question, event_date in zip(checkpoint["questions"], event_dates):
        question_id = question["id"]
        require(question_id not in seen_events, f"Repeated event: {question_id}")
        seen_events.add(question_id)
        source = question["sourceUrl"]
        require(source not in seen_sources, f"Repeated source: {source}")
        seen_sources.add(source)
        domains.add(urlparse(source).netloc.lower())
        published = date.fromisoformat(question["sourcePublishedDate"])
        require(event_date <= published <= min(as_of, event_date + timedelta(days=7)), f"Source too late or predates event: {question_id}")
        require(question["options"][-1]["id"] == "unknown", f"Unknown option is not last: {question_id}")
    require(len(domains) >= 2, f"Checkpoint relies on one source domain: {checkpoint['id']}")
    date_report.append((checkpoint["id"], checkpoint["date"], span, certain_before, possibly_after))

nodes = quiz["nodes"]
visited = set()
leaves = []
checkpoint_ids = []


def walk(node_id, lower, upper):
    require(node_id in nodes, f"Missing node: {node_id}")
    require(node_id not in visited, f"Repeated node: {node_id}")
    visited.add(node_id)
    node = nodes[node_id]
    require(node["id"] == node_id, f"Node ID mismatch: {node_id}")
    if node["type"] == "result":
        expected = compiler.make_result(node_id, lower, upper, rows, as_of)
        require(node == expected, f"Result range or candidate ranking mismatch: {node_id}")
        leaves.append((node_id, lower, upper, node["candidateCount"]))
        return
    require(node["type"] == "checkpoint", f"Unknown node type: {node_id}")
    checkpoint_id = node_id.removeprefix("checkpoint_")
    require(checkpoint_id in bank_by_id, f"Unknown checkpoint: {node_id}")
    checkpoint = bank_by_id[checkpoint_id]
    checkpoint_ids.append(checkpoint_id)
    require(node["date"] == checkpoint["date"], f"Checkpoint date mismatch: {node_id}")
    require(node["threshold"] == 2, f"Checkpoint threshold mismatch: {node_id}")
    require(len(node["questions"]) == 3, f"Checkpoint question count mismatch: {node_id}")
    require([question["id"] for question in node["questions"]] == [question["id"] for question in checkpoint["questions"]], f"Question order mismatch: {node_id}")
    for actual, source in zip(node["questions"], checkpoint["questions"]):
        require(comparable_question(actual) == comparable_question(source), f"Compiled question differs from source: {actual['id']}")
    positions = [next(index for index, option in enumerate(question["options"]) if option["id"] == question["correctOptionId"]) for question in node["questions"]]
    require(sorted(positions) == [0, 1, 2], f"Correct answer positions are unbalanced: {node_id}")
    require(all(question["options"][-1]["id"] == "unknown" for question in node["questions"]), f"Unknown option position mismatch: {node_id}")
    require(sum(question["category"] == "society" for question in node["questions"]) >= 2, f"Too few social questions: {node_id}")
    for selected in itertools.product(*(tuple(option["id"] for option in question["options"]) for question in node["questions"])):
        correct_count = sum(choice == question["correctOptionId"] for choice, question in zip(selected, node["questions"]))
        branch = "correct" if correct_count >= 2 else "incorrect"
        require(node["next"][branch] in nodes, f"Missing {branch} transition: {node_id}")
    for wrong_index in range(3):
        selected = [question["correctOptionId"] if index != wrong_index else "unknown" for index, question in enumerate(node["questions"])]
        require(sum(choice == question["correctOptionId"] for choice, question in zip(selected, node["questions"])) >= 2, f"One unknown answer reverses checkpoint: {node_id}")
    require(set(node["next"]) == {"correct", "incorrect"}, f"Invalid transitions: {node_id}")
    boundary = date.fromisoformat(node["date"])
    require((lower is None or lower <= boundary) and (upper is None or boundary <= upper), f"Checkpoint outside path range: {node_id}")
    walk(node["next"]["incorrect"], lower, boundary - timedelta(days=1))
    walk(node["next"]["correct"], boundary, upper)


walk(quiz["root"], None, None)
require(len(visited) == len(nodes), "Unreachable nodes")
require(set(checkpoint_ids) == set(bank_by_id) and len(checkpoint_ids) == len(checkpoints), "Missing or repeated checkpoints")
require(len(leaves) == len(checkpoints) + 1, "Wrong number of result intervals")
ordered_leaves = sorted(leaves, key=lambda leaf: leaf[1] or date.min)
require(ordered_leaves[0][1] is None and ordered_leaves[-1][2] is None, "Result intervals do not cover all dates")
for previous, following in zip(ordered_leaves, ordered_leaves[1:]):
    require(previous[2] is not None and following[1] == previous[2] + timedelta(days=1), "Result intervals overlap or leave a gap")

print(f"PASS: {len(checkpoints)} checkpoints, {quiz['questionCount']} questions, {len(leaves)} continuous result intervals, {len(rows)} catalog models")
print("PASS: source timing, 90-day event windows, independent domains, source-to-build fidelity, rankings, answer positions, one-error tolerance")
for checkpoint_id, checkpoint_date, span, before, after in date_report:
    print(f"  {checkpoint_id}: boundary {checkpoint_date}, event span {span} days, catalog {before} certainly before / {after} possibly after")
print("Manual review remains required for salience, ambiguity, distractor plausibility, and source truthfulness")
