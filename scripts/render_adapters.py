#!/usr/bin/env python3
"""Render per-host manifests, and package the skill for hosts whose layout differs."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".agent/manifest.yaml"
YAML_BANNER = "# Generated from .agent/manifest.yaml by scripts/render_adapters.py. Do not edit.\n"
LAYOUTS = {"repo-root", "skill-subdirectory"}
DIST = "dist"
REQUIRED_SKILL_FIELDS = ("id", "display_name", "version", "short_description", "entrypoint")


def load_manifest(path):
    try:
        import yaml
    except ImportError as exc:
        raise ValueError("Reading the manifest requires PyYAML.") from exc
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Manifest requires schema_version 1.")
    for key in ("skill", "invocation", "targets"):
        if not isinstance(data.get(key), dict):
            raise ValueError(f"Manifest requires a {key} object.")
    missing = [key for key in REQUIRED_SKILL_FIELDS if not str(data["skill"].get(key) or "").strip()]
    if missing:
        raise ValueError(f"Manifest skill is missing: {', '.join(missing)}.")
    if not str(data["invocation"].get("default_prompt") or "").strip():
        raise ValueError("Manifest requires invocation.default_prompt.")
    payload = data.get("payload")
    if not isinstance(payload, list) or not payload or not all(str(item or "").strip() for item in payload):
        raise ValueError("Manifest requires a nonempty payload list.")
    for name, target in data["targets"].items():
        layout = target.get("layout") if isinstance(target, dict) else None
        if layout is not None and layout not in LAYOUTS:
            raise ValueError(f"Target {name} declares unknown layout {layout!r}.")
    return data


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def prune(mapping):
    """Drop keys whose value is None or empty, so a host never sees a null field."""
    return {key: value for key, value in mapping.items() if value not in (None, "", [], {})}


def as_json(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def prompt_for(manifest, target):
    return f"{target.get('prompt_prefix', '')}{manifest['invocation']['default_prompt']}".strip()


def render_openai(manifest, target):
    """OpenAI registry manifest. YAML; interface/policy split; no version field."""
    skill = manifest["skill"]
    products = target.get("products") or []
    if not products:
        raise ValueError("The openai target requires a nonempty products list.")
    icon = skill.get("icon")
    if not icon:
        raise ValueError("The openai target requires skill.icon.")
    lines = [
        YAML_BANNER,
        "interface:\n",
        f"  display_name: {quote(skill['display_name'])}\n",
        f"  short_description: {quote(skill['short_description'])}\n",
        f"  default_prompt: {quote(prompt_for(manifest, target))}\n",
        f"  icon_small: {icon}\n",
        f"  icon_large: {icon}\n",
        "policy:\n",
        "  products:\n",
    ]
    lines += [f"  - {product}\n" for product in products]
    lines.append(f"  allow_implicit_invocation: {str(bool(manifest['invocation']['allow_implicit'])).lower()}\n")
    return "".join(lines)


def render_claude_plugin(manifest, target):
    """Claude Code plugin manifest. JSON at .claude-plugin/plugin.json; only name is required."""
    skill = manifest["skill"]
    payload = prune({
        "name": skill["id"],
        "displayName": skill["display_name"],
        "version": skill["version"],
        "description": " ".join(str(skill.get("description") or skill["short_description"]).split()),
        "author": skill.get("author"),
        "homepage": skill.get("homepage"),
        "repository": skill.get("repository"),
        "license": skill.get("license"),
        "keywords": skill.get("keywords"),
        # No skills key: a plugin with SKILL.md at its root and no skills/
        # directory loads as a single skill from the repository as it stands.
    })
    return as_json(payload)


def render_gemini_extension(manifest, target):
    """Gemini CLI extension manifest. JSON at the repository root; name and version required."""
    skill = manifest["skill"]
    payload = prune({
        "name": skill["id"],
        "version": skill["version"],
        "description": " ".join(str(skill.get("description") or skill["short_description"]).split()),
    })
    return as_json(payload)


RENDERERS = {
    "openai-skill-manifest": render_openai,
    "claude-plugin-manifest": render_claude_plugin,
    "gemini-extension-manifest": render_gemini_extension,
    "skill-frontmatter": None,
}


def render_targets(manifest):
    rendered = {}
    for name, target in manifest["targets"].items():
        if not isinstance(target, dict):
            raise ValueError(f"Target {name} must be an object.")
        path, fmt = target.get("path"), target.get("format")
        if fmt not in RENDERERS:
            raise ValueError(f"Target {name} declares unsupported format {fmt!r}.")
        renderer = RENDERERS[fmt]
        if path is None or renderer is None:
            continue
        if path in rendered:
            raise ValueError(f"Two targets write to {path}.")
        rendered[path] = renderer(manifest, target)
    return rendered


def package_target(manifest, name, root, dist_root):
    """Assemble a distributable copy for a host whose layout differs from this repository."""
    target = manifest["targets"].get(name)
    if not isinstance(target, dict):
        raise ValueError(f"Unknown target {name!r}.")
    layout = target.get("layout")
    if layout != "skill-subdirectory":
        raise ValueError(f"Target {name} has layout {layout!r} and needs no packaging; "
                         "it installs from the repository as it stands.")

    skill_id = manifest["skill"]["id"]
    destination = dist_root / name
    if destination.exists():
        shutil.rmtree(destination)
    skill_dir = destination / "skills" / skill_id
    skill_dir.mkdir(parents=True)

    excluded = {str(item).strip().rstrip("/") for item in manifest.get("payload_exclude", [])}
    copied, skipped = [], sorted(excluded)
    for item in manifest["payload"]:
        source = root / item.rstrip("/")
        if not source.exists():
            raise ValueError(f"Payload entry {item} does not exist.")
        if item.rstrip("/") in excluded:
            continue
        target_path = skill_dir / source.name

        def skip(directory, names, _base=root):
            relative = Path(directory).relative_to(_base)
            return {name for name in names
                    if name in ("__pycache__",) or name.endswith(".pyc")
                    or str(relative / name) in excluded}

        if source.is_dir():
            shutil.copytree(source, target_path, ignore=skip)
        else:
            shutil.copy2(source, target_path)
        copied.append(item)

    rendered = render_targets(manifest)
    relative = target.get("path")
    if relative:
        manifest_path = destination / Path(relative).name
        manifest_path.write_text(rendered[relative], encoding="utf-8")

    leftover = sorted(path for path in excluded if (skill_dir / Path(path)).exists())
    if leftover:
        raise ValueError(f"Excluded payload entries were still copied: {leftover}.")
    return {"target": name, "layout": layout, "root": str(destination.relative_to(root)),
            "skill_path": str(skill_dir.relative_to(destination)), "payload": copied, "excluded": skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Exit 1 when a generated file is out of date.")
    group.add_argument("--write", action="store_true", help="Regenerate generated files in place.")
    group.add_argument("--package", metavar="TARGET",
                       help="Build a distributable copy under dist/ for a host with a different layout.")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()

    root = Path(args.root)
    try:
        manifest = load_manifest(Path(args.manifest))
        if args.package:
            built = package_target(manifest, args.package, root, root / DIST)
            print(json.dumps({"status": "valid", "packaged": built}, indent=2))
            return 0
        outputs = render_targets(manifest)
    except (OSError, ValueError, shutil.Error) as exc:
        print(json.dumps({"status": "inconclusive", "error": str(exc)}, indent=2))
        return 2

    stale, written = [], []
    for relative, content in sorted(outputs.items()):
        path = root / relative
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == content:
            continue
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(relative)
        else:
            stale.append(relative)

    result = {
        "status": "invalid" if stale else "valid",
        "generated": sorted(outputs),
        "stale": stale,
        "written": written,
        "manifest_sha256": hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest(),
    }
    print(json.dumps(result, indent=2))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
