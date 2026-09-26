import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from check_project import (audit_agent_contract, audit_preservation, audit_task_status_index,
                           evaluate_gate, validate_model)


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
                root / "docs/task/README.md",
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

    def test_task_status_index_accepts_all_execution_states(self):
        rows = [
            "| [] | `TASK-001` | Todo | `todo` | `current` | — | Next input | — |",
            "| [] | `TASK-002` | Ready | `ready` | `current` | TASK-001 | Dependencies met | — |",
            "| [!] | `TASK-003` | Active | `in_progress` | `current` | TASK-002 | Implementing parser | — |",
            "| [!] | `TASK-004` | Verify | `verifying` | `current` | TASK-003 | Running integration checks | — |",
            "| [!] | `TASK-005` | Blocked | `blocked` | `current` | TASK-004 | Waiting for schema decision | — |",
            "| [!] | `TASK-006` | Revalidate | `needs_revalidation` | `current` | TASK-005 | Dependency changed | old-run.json |",
            "| [x] | `TASK-007` | Done | `done` | `superseded` | TASK-006 | Replaced later | IMPL-TASK-007.md |",
        ]
        content = "\n".join([
            "| Status | ID | Title | Execution | Relevance | Depends on | Detail | Evidence |",
            "|---|---|---|---|---|---|---|---|",
            *rows,
        ])
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "README.md"
            index.write_text(content, encoding="utf-8")
            result = audit_task_status_index(index)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(len(result["checked"]), 7)

    def test_task_status_index_rejects_drift(self):
        content = "\n".join([
            "| Status | ID | Title | Execution | Relevance | Detail | Evidence |",
            "|---|---|---|---|---|---|---|",
            "| [x] | TASK-001 | Wrong marker | todo | current | — | proof.json |",
            "| [!] | TASK-001 | Duplicate blocked | blocked | current | — | — |",
            "| [x] | TASK-003 | No evidence | done | current | Complete | — |",
        ])
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "README.md"
            index.write_text(content, encoding="utf-8")
            result = audit_task_status_index(index)
        issues = " ".join(result["errors"])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("must render", issues)
        self.assertIn("Duplicate task status ID", issues)
        self.assertIn("requires an attention detail", issues)
        self.assertIn("requires current evidence", issues)

    def test_task_status_index_requires_contract_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "README.md"
            index.write_text("| Status | ID |\n|---|---|\n| [] | TASK-001 |\n", encoding="utf-8")
            result = audit_task_status_index(index)
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("missing columns" in issue for issue in result["errors"]))

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


ADAPTER = """<!-- pdd:generated:begin id={id} source=.agent/AGENTS.md -->
Read [`.agent/AGENTS.md`](.agent/AGENTS.md) before doing any work here.
<!-- pdd:generated:end id={id} -->
"""


class AgentContractChecks(unittest.TestCase):
    def build(self, *, canonical="Agent contract\n", adapters=None, rules=(), context=()):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / ".agent").mkdir()
        (root / ".agent/AGENTS.md").write_text(canonical, encoding="utf-8")
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if adapters is None:
            adapters = [{"id": "claude", "host": "Claude Code", "path": "CLAUDE.md",
                         "kind": "file", "source_hash": digest}]
        for adapter in adapters:
            target = root / adapter["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(ADAPTER.format(id=adapter["id"]), encoding="utf-8")
        index = {"schema_version": 1, "canonical": ".agent/AGENTS.md",
                 "rules": list(rules), "context": list(context), "adapters": adapters}
        (root / ".agent/index.json").write_text(json.dumps(index), encoding="utf-8")
        return root, digest

    def test_bundled_templates_satisfy_the_contract(self):
        canonical = (ROOT / "assets/agent/AGENTS.template.md").read_text(encoding="utf-8")
        root, _ = self.build(canonical=canonical)
        self.assertEqual(audit_agent_contract(root)["status"], "valid")

    def test_index_example_is_well_formed(self):
        index = json.loads((ROOT / "assets/agent/index.example.json").read_text())
        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(index["canonical"], ".agent/AGENTS.md")
        self.assertTrue(index["adapters"])
        self.assertEqual(len({adapter["id"] for adapter in index["adapters"]}), len(index["adapters"]))

    def test_unconfigured_when_no_index(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(audit_agent_contract(empty)["status"], "not_configured")

    def test_missing_adapter_is_invalid(self):
        root, _ = self.build()
        (root / "CLAUDE.md").unlink()
        result = audit_agent_contract(root)
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("missing" in issue for issue in result["errors"]))

    def test_adapter_without_managed_region_is_invalid(self):
        root, _ = self.build()
        (root / "CLAUDE.md").write_text("See .agent/AGENTS.md\n", encoding="utf-8")
        result = audit_agent_contract(root)
        self.assertTrue(any("managed region" in issue for issue in result["errors"]))

    def test_adapter_not_pointing_at_canonical_is_invalid(self):
        root, _ = self.build()
        (root / "CLAUDE.md").write_text(ADAPTER.format(id="claude").replace(".agent/AGENTS.md", "docs/x.md"),
                                        encoding="utf-8")
        result = audit_agent_contract(root)
        self.assertTrue(any("never points at" in issue for issue in result["errors"]))

    def test_stale_source_hash_is_invalid(self):
        root, _ = self.build()
        (root / ".agent/AGENTS.md").write_text("Agent contract, revised\n", encoding="utf-8")
        result = audit_agent_contract(root)
        self.assertTrue(any("regenerate" in issue for issue in result["errors"]))

    def test_null_source_hash_warns_without_failing(self):
        root, _ = self.build(adapters=[{"id": "claude", "path": "CLAUDE.md", "source_hash": None}])
        result = audit_agent_contract(root)
        self.assertEqual(result["status"], "valid")
        self.assertTrue(any("source_hash" in note for note in result["warnings"]))

    def test_duplicate_adapter_ids_are_invalid(self):
        root, _ = self.build(adapters=[
            {"id": "claude", "path": "CLAUDE.md", "source_hash": None},
            {"id": "claude", "path": "AGENTS.md", "source_hash": None},
        ])
        self.assertTrue(any("Duplicate adapter id" in issue for issue in audit_agent_contract(root)["errors"]))

    def test_listed_rule_must_exist(self):
        root, _ = self.build(rules=[".agent/rules/absent.md"])
        self.assertTrue(any("absent.md" in issue for issue in audit_agent_contract(root)["errors"]))

    def test_empty_canonical_is_invalid(self):
        root, _ = self.build(canonical="   \n")
        self.assertTrue(any("empty" in issue for issue in audit_agent_contract(root)["errors"]))


class RegistryManifestChecks(unittest.TestCase):
    """Every per-host manifest is generated; none is hand-maintained."""

    def render(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/render_adapters.py"), *args],
                              capture_output=True, text=True)

    def setUp(self):
        import yaml
        self.manifest = yaml.safe_load((ROOT / ".agent/manifest.yaml").read_text())

    def test_generated_manifests_match_the_source(self):
        result = self.render("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        generated = json.loads(result.stdout)["generated"]
        declared = [target["path"] for target in self.manifest["targets"].values() if target.get("path")]
        self.assertEqual(sorted(generated), sorted(declared))

    def test_every_target_declares_a_known_layout(self):
        for name, target in self.manifest["targets"].items():
            with self.subTest(target=name):
                self.assertIn(target.get("layout"), {"repo-root", "skill-subdirectory", None})

    def test_openai_manifest_parses_and_keeps_its_schema(self):
        import yaml
        data = yaml.safe_load((ROOT / "agents/openai.yaml").read_text())
        self.assertEqual(set(data), {"interface", "policy"})
        self.assertEqual(set(data["interface"]),
                         {"display_name", "short_description", "default_prompt", "icon_small", "icon_large"})
        self.assertTrue(data["policy"]["products"])
        self.assertTrue((ROOT / data["interface"]["icon_small"]).is_file())

    def test_claude_plugin_manifest_is_valid_json_with_a_kebab_name(self):
        data = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertRegex(data["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertNotIn("skills", data)
        self.assertTrue((ROOT / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skills").exists(), "a skills/ directory would load as a second skill")

    def test_gemini_manifest_has_its_required_fields_only(self):
        data = json.loads((ROOT / "gemini-extension.json").read_text())
        self.assertLessEqual(set(data), {"name", "version", "description"})
        self.assertTrue(data["name"] and data["version"])
        self.assertNotIn("contextFileName", data)

    def test_identity_is_consistent_across_hosts(self):
        import yaml
        frontmatter = yaml.safe_load((ROOT / "SKILL.md").read_text().split("---")[1])
        skill_id = self.manifest["skill"]["id"]
        self.assertEqual(skill_id, frontmatter["name"])
        self.assertEqual(json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["name"], skill_id)
        self.assertEqual(json.loads((ROOT / "gemini-extension.json").read_text())["name"], skill_id)

    def test_no_generated_manifest_contains_a_null(self):
        for relative in (".claude-plugin/plugin.json", "gemini-extension.json"):
            with self.subTest(path=relative):
                self.assertNotIn(None, json.loads((ROOT / relative).read_text()).values())

    def test_packaging_relocates_the_payload_with_working_links(self):
        with tempfile.TemporaryDirectory() as staging:
            work = Path(staging) / "repo"
            shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"))
            result = subprocess.run(
                [sys.executable, str(work / "scripts/render_adapters.py"), "--package", "gemini-cli",
                 "--manifest", str(work / ".agent/manifest.yaml"), "--root", str(work)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            built = json.loads(result.stdout)["packaged"]
            skill_dir = work / built["root"] / built["skill_path"]
            self.assertTrue((skill_dir / "SKILL.md").is_file())
            self.assertTrue((work / built["root"] / "gemini-extension.json").is_file())
            for excluded in self.manifest.get("payload_exclude", []):
                self.assertFalse((skill_dir / excluded).exists(), excluded)
            unresolved = []
            for md in skill_dir.rglob("*.md"):
                if md.parent.name == "agent":
                    continue  # templates link relative to a generated project root
                for link in re.findall(r"\]\(([^)#][^)]*)\)", md.read_text()):
                    if link.startswith(("http://", "https://", "mailto:")):
                        continue
                    if not (md.parent / link).exists():
                        unresolved.append(f"{md.relative_to(skill_dir)} -> {link}")
            self.assertEqual(unresolved, [])

    def test_packaging_refuses_a_host_that_needs_none(self):
        result = self.render("--package", "claude-code")
        self.assertEqual(result.returncode, 2)
        self.assertIn("needs no packaging", json.loads(result.stdout)["error"])

    def test_packaging_rejects_an_unknown_host(self):
        self.assertEqual(self.render("--package", "no-such-host").returncode, 2)


if __name__ == "__main__":
    unittest.main()
