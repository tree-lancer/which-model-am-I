import csv
import json
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "data" / "model_cutoffs.csv"
QUESTIONNAIRES = ROOT / "data" / "questionnaires"
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_cutoff(expression):
    dates = [date.fromisoformat(value) for value in DATE_PATTERN.findall(expression)]
    if expression.startswith("=") and len(dates) == 1:
        return dates[0], dates[0]
    if expression.startswith(">") and "&<" in expression and len(dates) == 2:
        return dates[0] + timedelta(days=1), dates[1] - timedelta(days=1)
    if expression.startswith(">") and len(dates) == 1:
        return dates[0] + timedelta(days=1), None
    if expression.startswith("<") and len(dates) == 1:
        return None, dates[0] - timedelta(days=1)
    raise ValueError(f"Invalid cutoff: {expression}")


def validate_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"Invalid evidence URL: {value}")


def load_catalog(as_of):
    with CATALOG.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    seen = set()
    for row in rows:
        key = (row["provider"], row["model_id"])
        if key in seen:
            raise ValueError(f"Duplicate catalog entry: {key}")
        seen.add(key)
        lower, upper = parse_cutoff(row["cutoff"])
        if lower and upper and lower > upper:
            raise ValueError(f"Empty cutoff interval: {key}")
        if lower and lower > as_of:
            raise ValueError(f"Future cutoff: {key}")
        validate_url(row["evidence_url"])
    return rows


def load_bank(version):
    folder = QUESTIONNAIRES / version
    bank = json.loads((folder / "question_bank.json").read_text(encoding="utf-8"))
    if bank["version"] != version:
        raise ValueError("Question bank version and directory disagree")
    as_of = date.fromisoformat(bank["asOf"])
    if "checkpoints" in bank:
        validate_checkpoints(bank["checkpoints"], as_of)
        return bank, as_of
    questions = bank["questions"]
    seen_ids = set()
    seen_dates = set()
    for question in questions:
        event = date.fromisoformat(question["eventDate"])
        if event > as_of:
            raise ValueError(f"Future event: {question['id']}")
        if question["id"] in seen_ids or event in seen_dates:
            raise ValueError(f"Duplicate question or event date: {question['id']}")
        seen_ids.add(question["id"])
        seen_dates.add(event)
        if not question["prompt"].strip() or len(question["options"]) != 4:
            raise ValueError(f"Incomplete question: {question['id']}")
        option_ids = [option["id"] for option in question["options"]]
        option_labels = [option["label"] for option in question["options"]]
        if len(option_ids) != len(set(option_ids)) or len(option_labels) != len(set(option_labels)) or any(not label.strip() for label in option_labels):
            raise ValueError(f"Invalid options: {question['id']}")
        if question["correctOptionId"] not in option_ids or question["unknownOptionId"] not in option_ids:
            raise ValueError(f"Missing correct or unknown option: {question['id']}")
        if question["correctOptionId"] == question["unknownOptionId"]:
            raise ValueError(f"Unknown option is correct: {question['id']}")
        if question["unknownOptionId"] != "unknown":
            raise ValueError(f"Unknown option must have id unknown: {question['id']}")
        if next(option["label"] for option in question["options"] if option["id"] == "unknown") != "不知道／不确定":
            raise ValueError(f"Invalid unknown option label: {question['id']}")
        validate_url(question["sourceUrl"])
    if not questions:
        raise ValueError("The question bank is empty")
    questions.sort(key=lambda item: item["eventDate"])
    return bank, as_of


def validate_checkpoints(checkpoints, as_of):
    if not checkpoints:
        raise ValueError("The checkpoint bank is empty")
    checkpoint_ids = set()
    question_ids = set()
    checkpoint_dates = set()
    for checkpoint in checkpoints:
        checkpoint_date = date.fromisoformat(checkpoint["date"])
        if checkpoint["id"] in checkpoint_ids or checkpoint_date in checkpoint_dates:
            raise ValueError(f"Duplicate checkpoint: {checkpoint['id']}")
        checkpoint_ids.add(checkpoint["id"])
        checkpoint_dates.add(checkpoint_date)
        questions = checkpoint["questions"]
        if len(questions) != 3:
            raise ValueError(f"Checkpoint needs three questions: {checkpoint['id']}")
        event_dates = sorted(date.fromisoformat(question["eventDate"]) for question in questions)
        if event_dates[1] != checkpoint_date or event_dates[-1] > as_of:
            raise ValueError(f"Checkpoint date must be the middle event: {checkpoint['id']}")
        if (event_dates[-1] - event_dates[0]).days > 90:
            raise ValueError(f"Checkpoint events span more than 90 days: {checkpoint['id']}")
        social_count = 0
        for question in questions:
            if question["id"] in question_ids:
                raise ValueError(f"Duplicate question: {question['id']}")
            question_ids.add(question["id"])
            if question["category"] not in {"society", "technology"}:
                raise ValueError(f"Invalid question category: {question['id']}")
            social_count += question["category"] == "society"
            if not question["prompt"].strip() or len(question["options"]) != 4:
                raise ValueError(f"Incomplete question: {question['id']}")
            options = question["options"]
            ids = [option["id"] for option in options]
            labels = [option["label"] for option in options]
            if len(set(ids)) != 4 or len(set(labels)) != 4 or any(not label.strip() for label in labels):
                raise ValueError(f"Invalid options: {question['id']}")
            if question["correctOptionId"] not in ids or question["unknownOptionId"] != "unknown" or "unknown" not in ids:
                raise ValueError(f"Invalid answer keys: {question['id']}")
            if question["correctOptionId"] == "unknown":
                raise ValueError(f"Unknown is correct: {question['id']}")
            if next(option["label"] for option in options if option["id"] == "unknown") != "不知道／不确定":
                raise ValueError(f"Invalid unknown label: {question['id']}")
            validate_url(question["sourceUrl"])
            published = date.fromisoformat(question["sourcePublishedDate"])
            event = date.fromisoformat(question["eventDate"])
            if not event <= published <= min(as_of, event + timedelta(days=7)):
                raise ValueError(f"Source publication date is too far from event: {question['id']}")
        if social_count < 2:
            raise ValueError(f"Checkpoint needs two social events: {checkpoint['id']}")
    checkpoints.sort(key=lambda item: item["date"])


def fit(row, lower, upper, as_of):
    model_lower, model_upper = parse_cutoff(row["cutoff"])
    lo = max(lower or date(2020, 1, 1), model_lower or date(2020, 1, 1))
    hi = min(upper or as_of, model_upper or as_of)
    if lo > hi:
        return 0.0
    if row["cutoff_basis"] == "release_date_upper_bound":
        release = model_upper or as_of
        preferred = release - timedelta(days=150)
        midpoint = lo + (hi - lo) / 2
        distance = abs((midpoint - preferred).days)
        return round(0.55 / (1 + distance / 180), 4)
    width = ((model_upper or as_of) - (model_lower or date(2020, 1, 1))).days + 1
    overlap = (hi - lo).days + 1
    return round(overlap / width, 4)


def make_result(node_id, lower, upper, rows, as_of):
    matches = []
    for row in rows:
        score = fit(row, lower, upper, as_of)
        if score <= 0:
            continue
        matches.append({
            "provider": row["provider"],
            "modelId": row["model_id"],
            "cutoff": row["cutoff"],
            "basis": row["cutoff_basis"],
            "evidenceUrl": row["evidence_url"],
            "fit": score,
        })
    matches.sort(key=lambda item: (-item["fit"], item["provider"], item["modelId"]))
    return {
        "type": "result",
        "id": node_id,
        "range": {"from": str(lower) if lower else None, "through": str(upper) if upper else None},
        "candidateCount": len(matches),
        "candidates": matches[:20],
    }


def build_tree(questions, rows, as_of):
    nodes = {}

    def build(start, end, lower, upper, path):
        if start == end:
            node_id = f"result_{path or 'root'}"
            nodes[node_id] = make_result(node_id, lower, upper, rows, as_of)
            return node_id
        middle = (start + end) // 2
        question = questions[middle]
        event = date.fromisoformat(question["eventDate"])
        node_id = f"question_{question['id']}"
        options = [option for option in question["options"] if option["id"] != question["unknownOptionId"]]
        random.Random(question["id"]).shuffle(options)
        options.append(next(option for option in question["options"] if option["id"] == question["unknownOptionId"]))
        incorrect = build(start, middle, lower, min(upper, event - timedelta(days=1)) if upper else event - timedelta(days=1), path + "0")
        correct = build(middle + 1, end, max(lower, event) if lower else event, upper, path + "1")
        nodes[node_id] = {
            "type": "question",
            "id": node_id,
            "eventDate": question["eventDate"],
            "prompt": question["prompt"],
            "options": options,
            "correctOptionId": question["correctOptionId"],
            "unknownOptionId": question["unknownOptionId"],
            "sourceUrl": question["sourceUrl"],
            "next": {"correct": correct, "incorrect": incorrect},
        }
        return node_id

    root = build(0, len(questions), None, None, "")
    return root, dict(sorted(nodes.items()))


def build_checkpoint_tree(checkpoints, rows, as_of):
    nodes = {}

    def build(start, end, lower, upper, path):
        if start == end:
            node_id = f"result_{path or 'root'}"
            nodes[node_id] = make_result(node_id, lower, upper, rows, as_of)
            return node_id
        middle = (start + end) // 2
        checkpoint = checkpoints[middle]
        event = date.fromisoformat(checkpoint["date"])
        node_id = f"checkpoint_{checkpoint['id']}"
        incorrect = build(start, middle, lower, min(upper, event - timedelta(days=1)) if upper else event - timedelta(days=1), path + "0")
        correct = build(middle + 1, end, max(lower, event) if lower else event, upper, path + "1")
        questions = []
        correct_positions = [0, 1, 2]
        random.Random(checkpoint["id"]).shuffle(correct_positions)
        for question, correct_position in zip(checkpoint["questions"], correct_positions):
            correct_option = next(option for option in question["options"] if option["id"] == question["correctOptionId"])
            options = [option for option in question["options"] if option["id"] not in {"unknown", question["correctOptionId"]}]
            random.Random(question["id"]).shuffle(options)
            options.insert(correct_position, correct_option)
            options.append(next(option for option in question["options"] if option["id"] == "unknown"))
            questions.append({**question, "options": options})
        nodes[node_id] = {
            "type": "checkpoint",
            "id": node_id,
            "date": checkpoint["date"],
            "threshold": 2,
            "questions": questions,
            "next": {"correct": correct, "incorrect": incorrect},
        }
        return node_id

    root = build(0, len(checkpoints), None, None, "")
    return root, dict(sorted(nodes.items()))


def validate_checkpoint_tree(root, nodes, checkpoint_count):
    visited = set()
    stack = [root]
    while stack:
        node_id = stack.pop()
        if node_id not in nodes or node_id in visited:
            raise ValueError(f"Invalid checkpoint path: {node_id}")
        visited.add(node_id)
        if nodes[node_id]["type"] == "checkpoint":
            stack.extend(nodes[node_id]["next"].values())
    if len(visited) != len(nodes):
        raise ValueError("Unreachable checkpoint nodes")
    if sum(node["type"] == "checkpoint" for node in nodes.values()) != checkpoint_count:
        raise ValueError("Not every checkpoint is reachable")
    if sum(node["type"] == "result" for node in nodes.values()) != checkpoint_count + 1:
        raise ValueError("Incorrect result interval count")


def validate_tree(root, nodes, question_count):
    visited = set()
    stack = [root]
    while stack:
        node_id = stack.pop()
        if node_id not in nodes:
            raise ValueError(f"Broken transition: {node_id}")
        if node_id in visited:
            raise ValueError(f"Repeated node: {node_id}")
        visited.add(node_id)
        node = nodes[node_id]
        if node["type"] == "question":
            stack.extend(node["next"].values())
    if len(visited) != len(nodes):
        raise ValueError("Unreachable questionnaire nodes")
    if sum(node["type"] == "question" for node in nodes.values()) != question_count:
        raise ValueError("Not every question is reachable")
    if sum(node["type"] == "result" for node in nodes.values()) != question_count + 1:
        raise ValueError("Incorrect number of result intervals")


def compile_version(version):
    bank, as_of = load_bank(version)
    rows = load_catalog(as_of)
    if "checkpoints" in bank:
        checkpoint_count = len(bank["checkpoints"])
        question_count = checkpoint_count * 3
        root, nodes = build_checkpoint_tree(bank["checkpoints"], rows, as_of)
        validate_checkpoint_tree(root, nodes, checkpoint_count)
        schema_version = 2
    else:
        question_count = len(bank["questions"])
        root, nodes = build_tree(bank["questions"], rows, as_of)
        validate_tree(root, nodes, question_count)
        schema_version = 1
    compiled = {
        "schemaVersion": schema_version,
        "version": version,
        "asOf": str(as_of),
        "catalogSize": len(rows),
        "questionCount": question_count,
        "root": root,
        "nodes": nodes,
    }
    serialized = json.dumps(compiled, ensure_ascii=False, indent=2) + "\n"
    target = QUESTIONNAIRES / version / "questionnaire.json"
    if target.exists() and target.read_text(encoding="utf-8") != serialized:
        raise ValueError("Published questionnaire changed; create a new version")
    target.write_text(serialized, encoding="utf-8")
    (QUESTIONNAIRES / "current.json").write_text(serialized, encoding="utf-8")
    print(f"Compiled {version}: {question_count} questions, {len(nodes)} nodes, {len(rows)} models")


if __name__ == "__main__":
    compile_version(sys.argv[1] if len(sys.argv) > 1 else "1.0.0")
