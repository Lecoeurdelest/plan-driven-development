#!/usr/bin/env python3
"""Validate project structure and gate supplied evidence metadata."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys


RISKS = {"standard", "critical"}
SHA256 = re.compile(r"[0-9a-f]{64}")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def score(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def strings(value):
    return isinstance(value, list) and all(nonempty(item) for item in value)


def load(path):
    raw = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() == ".json":
        return json.loads(raw)
    try:
        import yaml
    except ImportError as exc:
        raise ValueError("YAML requires PyYAML; alternatively use JSON.") from exc
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc


def validate_model(model):
    errors, warnings = [], []
    if not isinstance(model, dict):
        return ["Model must be an object."], warnings
    if type(model.get("schema_version")) is not int or model["schema_version"] != 1:
        errors.append("schema_version must be integer 1.")
    project = model.get("project")
    if not isinstance(project, dict) or not all(nonempty(project.get(k)) for k in ("id", "plan_file")):
        errors.append("project requires id and plan_file.")

    indexes, used_ids = {}, set()
    for kind in ("components", "decisions", "requirements", "tasks"):
        items = model.get(kind)
        indexes[kind] = {}
        if not isinstance(items, list):
            errors.append(f"{kind} must be a list.")
            continue
        if kind in ("requirements", "tasks") and not items:
            errors.append(f"{kind} cannot be empty.")
        for item in items:
            if not isinstance(item, dict) or not nonempty(item.get("id")):
                errors.append(f"Every {kind} entry needs an id.")
                continue
            identifier = item["id"]
            if identifier in used_ids:
                errors.append(f"Duplicate id: {identifier}.")
            used_ids.add(identifier)
            indexes[kind][identifier] = item
            if not nonempty(item.get("title")):
                errors.append(f"{identifier}: title is required.")

    for identifier, decision in indexes["decisions"].items():
        if not isinstance(decision.get("status"), str) or decision["status"] not in {"proposed", "accepted", "rejected", "superseded"}:
            errors.append(f"{identifier}: invalid decision status.")

    criteria = {}
    for identifier, requirement in indexes["requirements"].items():
        if not isinstance(requirement.get("risk"), str) or requirement["risk"] not in RISKS:
            errors.append(f"{identifier}: risk must be standard or critical.")
        source = requirement.get("source")
        if not isinstance(source, dict) or not all(nonempty(source.get(k)) for k in ("file", "section")):
            errors.append(f"{identifier}: source file and section are required.")
        acceptance = requirement.get("acceptance")
        if not isinstance(acceptance, list) or not acceptance:
            errors.append(f"{identifier}: acceptance criteria are required.")
            continue
        for criterion in acceptance:
            if not isinstance(criterion, dict) or not nonempty(criterion.get("id")):
                errors.append(f"{identifier}: criterion needs an id.")
                continue
            cid = criterion["id"]
            if cid in used_ids:
                errors.append(f"Duplicate id: {cid}.")
            used_ids.add(cid)
            criteria[cid] = identifier
            if not nonempty(criterion.get("statement")):
                errors.append(f"{cid}: statement is required.")
            methods = criterion.get("verification")
            if not strings(methods) or not methods or len(set(methods)) != len(methods):
                errors.append(f"{cid}: verification needs unique nonempty method names.")

    graph, mapped = {}, set()
    for identifier, task in indexes["tasks"].items():
        for field, target in (("requirement_ids", "requirements"), ("component_ids", "components"),
                              ("decision_ids", "decisions"), ("depends_on", "tasks"), ("acceptance_ids", None)):
            values = task.get(field)
            if not strings(values):
                errors.append(f"{identifier}: {field} must be a list of strings.")
                continue
            if len(values) != len(set(values)):
                errors.append(f"{identifier}: duplicate {field} references.")
            if field in {"requirement_ids", "acceptance_ids"} and not values:
                errors.append(f"{identifier}: {field} cannot be empty.")
            available = criteria if target is None else indexes[target]
            for value in values:
                if value not in available:
                    errors.append(f"{identifier}: unknown {field} reference {value}.")
            if field == "requirement_ids":
                mapped.update(values)
            if field == "depends_on":
                graph[identifier] = [v for v in values if v in available]
        requirement_ids = task.get("requirement_ids", [])
        if strings(task.get("acceptance_ids")) and strings(requirement_ids):
            for cid in task["acceptance_ids"]:
                if cid in criteria and criteria[cid] not in requirement_ids:
                    errors.append(f"{identifier}: {cid} belongs to an unreferenced requirement.")
        if strings(task.get("decision_ids")):
            for did in task["decision_ids"]:
                if did in indexes["decisions"] and indexes["decisions"][did].get("status") != "accepted":
                    warnings.append(f"{identifier}: decision {did} is not accepted.")

    remaining = {key: set(values) for key, values in graph.items()}
    while remaining:
        ready = {key for key, deps in remaining.items() if not deps}
        if not ready:
            errors.append("Dependency cycle involving: " + ", ".join(sorted(remaining)))
            break
        remaining = {key: deps - ready for key, deps in remaining.items() if key not in ready}

    for identifier in sorted(set(indexes["requirements"]) - mapped):
        warnings.append(f"{identifier}: no task mapping; confirm explicit deferral or ownership.")

    policy = model.get("verification")
    if not isinstance(policy, dict):
        errors.append("verification policy is required.")
    else:
        thresholds = policy.get("thresholds")
        if not isinstance(thresholds, dict) or not all(score(thresholds.get(k)) for k in RISKS):
            errors.append("thresholds must contain finite standard/critical scores in [0,1].")
        elif thresholds["critical"] < thresholds["standard"]:
            errors.append("Critical threshold cannot be below standard threshold.")
        if policy.get("calibration_required_for_auto_advance") is not True:
            errors.append("This automatic gate requires calibration; manual policy uses a separate recorded workflow.")
    return errors, warnings


def evaluate_gate(model, report, task_id, spec_hash, source_hash):
    failures, blockers, confidences = [], [], []

    def outcome():
        status = "fail" if failures else "inconclusive" if blockers else "pass"
        return {"status": status, "task_id": task_id, "failures": failures, "blockers": blockers,
                "minimum_criterion_confidence": min(confidences) if confidences else None,
                "scope": "Supplied metadata only; independently verify artifacts, calibration, and dependency state."}

    errors, _ = validate_model(model)
    if errors:
        blockers.extend(errors)
        return outcome()
    task = next((t for t in model["tasks"] if t["id"] == task_id), None)
    if task is None or not isinstance(report, dict):
        blockers.append("Unknown task or unusable evidence report.")
        return outcome()
    if type(report.get("schema_version")) is not int or report.get("schema_version") != 1:
        blockers.append("Evidence schema_version must be integer 1.")
    if report.get("task_id") != task_id:
        blockers.append("Evidence belongs to a different task.")
    for field, expected in (("spec_hash", spec_hash), ("source_hash", source_hash)):
        if not isinstance(expected, str) or SHA256.fullmatch(expected) is None:
            blockers.append(f"Current {field} must be a SHA-256 digest.")
        if report.get(field) != expected:
            blockers.append(f"Missing or stale {field}.")
    if blockers:
        return outcome()

    decisions = {d["id"]: d for d in model["decisions"]}
    for identifier in task["decision_ids"]:
        if decisions[identifier]["status"] != "accepted":
            blockers.append(f"Decision {identifier} is not accepted.")

    calibration = report.get("calibration")
    if not isinstance(calibration, dict) or calibration.get("status") != "validated" or calibration.get("applicable") is not True:
        blockers.append("Applicable validated calibration is unavailable.")
    elif not all(nonempty(calibration.get(k)) for k in ("id", "artifact", "evaluator_version")):
        blockers.append("Calibration provenance is incomplete.")

    expected = {c["id"]: (r, c) for r in model["requirements"] for c in r["acceptance"]}
    records = report.get("criteria")
    if not isinstance(records, list):
        blockers.append("Criterion evidence is missing.")
        return outcome()
    evidence = {}
    for record in records:
        if not isinstance(record, dict) or not nonempty(record.get("id")):
            blockers.append("Unusable criterion evidence entry.")
            continue
        identifier = record["id"]
        if identifier in evidence:
            blockers.append(f"Duplicate criterion evidence: {identifier}.")
        evidence[identifier] = record
    if set(evidence) != set(task["acceptance_ids"]):
        blockers.append("Evidence criteria must exactly match the scoped task criteria.")

    for identifier in task["acceptance_ids"]:
        if identifier not in evidence:
            continue
        requirement, criterion = expected[identifier]
        record = evidence[identifier]
        status = record.get("status")
        if status == "fail":
            failures.append(f"{identifier}: confirmed criterion failure.")
        elif status != "pass":
            blockers.append(f"{identifier}: criterion did not pass.")
        if record.get("analysis_complete") is not True:
            blockers.append(f"{identifier}: analysis is incomplete.")
        confidence = record.get("confidence")
        if not score(confidence):
            blockers.append(f"{identifier}: finite measured confidence is unavailable.")
        else:
            confidences.append(confidence)
            threshold = model["verification"]["thresholds"][requirement["risk"]]
            if confidence < threshold:
                blockers.append(f"{identifier}: confidence {confidence} is below {threshold}.")
        checks = record.get("checks")
        if not isinstance(checks, list):
            blockers.append(f"{identifier}: verification checks are missing.")
            continue
        seen = set()
        for check in checks:
            if not isinstance(check, dict) or not nonempty(check.get("method")):
                blockers.append(f"{identifier}: unusable verification check.")
                continue
            method = check["method"]
            seen.add(method)
            check_status = check.get("status")
            if check_status == "fail":
                failures.append(f"{identifier}/{method}: failed check.")
            elif check_status != "pass":
                blockers.append(f"{identifier}/{method}: check did not pass.")
            artifacts = check.get("artifacts")
            if not strings(artifacts) or not artifacts:
                blockers.append(f"{identifier}/{method}: artifact references are missing.")
        for method in set(criterion["verification"]) - seen:
            blockers.append(f"{identifier}: required {method} check is missing.")
    return outcome()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("model")
    gate = commands.add_parser("gate")
    gate.add_argument("model")
    gate.add_argument("report")
    gate.add_argument("--task", required=True)
    gate.add_argument("--source-hash", required=True)
    args = parser.parse_args()
    try:
        model = load(args.model)
        if args.command == "validate":
            errors, warnings = validate_model(model)
            result = {"status": "invalid" if errors else "valid", "errors": errors, "warnings": warnings}
            code = 1 if errors else 0
        else:
            spec_hash = hashlib.sha256(Path(args.model).read_bytes()).hexdigest()
            result = evaluate_gate(model, load(args.report), args.task, spec_hash, args.source_hash)
            code = {"pass": 0, "fail": 1, "inconclusive": 2}[result["status"]]
    except (OSError, ValueError) as exc:
        result, code = {"status": "inconclusive", "error": str(exc)}, 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
