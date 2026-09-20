import copy
import json
from pathlib import Path
import tempfile
import unittest

from check_project import audit_preservation, evaluate_gate, validate_model


ROOT = Path(__file__).resolve().parents[1]


class ProjectChecks(unittest.TestCase):
    def setUp(self):
        self.model = json.loads((ROOT / "assets/project.example.json").read_text())
        self.report = json.loads((ROOT / "assets/evidence.example.json").read_text())
        self.report.update(spec_hash="a" * 64, source_hash="b" * 64)
        self.report["calibration"] = {
            "status": "validated", "id": "fixture-calibration", "artifact": "fixture-calibration.json",
            "evaluator_version": "fixture-1", "applicable": True,
        }
        record = self.report["criteria"][0]
        record.update(status="pass", confidence=0.995, analysis_complete=True)
        for check in record["checks"]:
            check.update(status="pass", artifacts=["fixture-artifact.json"])

    def gate(self):
        return evaluate_gate(self.model, self.report, "T-001", "a" * 64, "b" * 64)

    def test_valid_model_and_metadata(self):
        self.assertEqual(validate_model(self.model), ([], []))
        self.assertEqual(self.gate()["status"], "pass")

    def test_dependency_cycle(self):
        self.model["tasks"][0]["depends_on"] = ["T-001"]
        self.assertTrue(any("cycle" in issue for issue in validate_model(self.model)[0]))

    def test_missing_reference(self):
        self.model["tasks"][0]["requirement_ids"] = ["FR-MISSING"]
        self.assertTrue(validate_model(self.model)[0])

    def test_cross_requirement_criterion(self):
        second = copy.deepcopy(self.model["requirements"][0])
        second.update(id="FR-02")
        second["acceptance"][0]["id"] = "AC-02"
        self.model["requirements"].append(second)
        self.model["tasks"][0]["acceptance_ids"] = ["AC-02"]
        self.assertTrue(any("unreferenced" in issue for issue in validate_model(self.model)[0]))

    def test_unaccepted_decision(self):
        self.model["decisions"][0]["status"] = "proposed"
        self.assertEqual(self.gate()["status"], "inconclusive")

    def test_stale_evidence(self):
        for field in ("source_hash", "spec_hash"):
            with self.subTest(field=field):
                previous = self.report[field]
                self.report[field] = "c" * 64
                self.assertEqual(self.gate()["status"], "inconclusive")
                self.report[field] = previous

    def test_failure_overrides_high_confidence(self):
        self.report["criteria"][0]["confidence"] = 1.0
        self.report["criteria"][0]["checks"][0]["status"] = "fail"
        self.assertEqual(self.gate()["status"], "fail")

    def test_incomplete_evidence_never_passes(self):
        for key, value in (("confidence", None), ("confidence", 0.98), ("confidence", True),
                           ("confidence", float("nan")), ("confidence", float("inf")),
                           ("analysis_complete", False), ("status", "not_run"), ("checks", [])):
            with self.subTest(key=key, value=value):
                previous = self.report["criteria"][0][key]
                self.report["criteria"][0][key] = value
                self.assertEqual(self.gate()["status"], "inconclusive")
                self.report["criteria"][0][key] = previous

    def test_calibration_required(self):
        self.report["calibration"]["status"] = "unavailable"
        self.assertEqual(self.gate()["status"], "inconclusive")
        self.model["verification"]["calibration_required_for_auto_advance"] = False
        self.assertTrue(validate_model(self.model)[0])

    def test_unapproved_preservation_break_is_invalid(self):
        artifact = self.model["preservation"]["artifacts"][0]
        artifact["disposition"] = "remove"
        self.assertTrue(any("explicit approval" in issue for issue in validate_model(self.model)[0]))
        artifact["approval"] = "USER-APPROVAL-001"
        self.assertFalse(any("explicit approval" in issue for issue in validate_model(self.model)[0]))

    def test_supersession_requires_replacement(self):
        artifact = self.model["preservation"]["artifacts"][0]
        artifact.update(disposition="supersede", approval="USER-APPROVAL-001")
        self.assertTrue(any("replacement_ids" in issue for issue in validate_model(self.model)[0]))
        artifact["replacement_ids"] = ["ART-TASK"]
        self.assertFalse(any("replacement_ids" in issue for issue in validate_model(self.model)[0]))
        artifact["replacement_ids"] = ["ART-MISSING"]
        self.assertTrue(any("unknown replacement" in issue for issue in validate_model(self.model)[0]))

    def test_preservation_audit_checks_declared_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [
                root / "docs/requirements/functional/FR-01.md",
                root / "docs/task/TASK-001.md",
                root / "docs/implement/IMPL-TASK-001.md",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")
            self.assertEqual(audit_preservation(self.model, root)["status"], "valid")
            paths[-1].unlink()
            result = audit_preservation(self.model, root)
            self.assertEqual(result["status"], "invalid")
            self.assertTrue(any("ART-IMPL" in issue for issue in result["errors"]))

    def test_preservation_audit_can_be_unconfigured(self):
        self.model.pop("preservation")
        self.assertEqual(audit_preservation(self.model, ".")["status"], "not_configured")

    def test_missing_or_duplicate_criteria(self):
        record = self.report["criteria"][0]
        for criteria in ([], [record, record]):
            self.report["criteria"] = criteria
            self.assertEqual(self.gate()["status"], "inconclusive")

    def test_missing_artifacts(self):
        self.report["criteria"][0]["checks"][0]["artifacts"] = []
        self.assertEqual(self.gate()["status"], "inconclusive")

    def test_malformed_values_are_reported(self):
        for value in (None, [], {}, {"schema_version": True}, "invalid"):
            self.assertTrue(validate_model(value)[0])
        self.model["requirements"][0]["risk"] = []
        self.model["decisions"][0]["status"] = {}
        self.assertTrue(validate_model(self.model)[0])


if __name__ == "__main__":
    unittest.main()
