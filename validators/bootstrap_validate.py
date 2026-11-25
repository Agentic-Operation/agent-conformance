#!/usr/bin/env python3
"""Spec-444 bootstrap validator — CI stage 2 (schema + structural rules).

Usage: bootstrap_validate.py <bootstrap.yaml> [more.yaml ...]
Exit 0 = conformant; exit 1 = violations on stderr.
"""
import os
import re
import sys

import yaml

SKILL_ID = re.compile(r"^(TMF-OASF [0-9]+|TMF-GB1033 F-[0-9]+|EXTENSION-[A-Za-z0-9-]+)$")
CID = re.compile(r"^sha256:[a-f0-9]{64}$")


def validate(doc, errors):
    bp = doc.get("bootstrap_profile")
    if not bp:
        errors.append("root key bootstrap_profile missing")
        return
    for k in ("id", "uuid", "version", "provider"):
        if k not in bp:
            errors.append(f"identity: missing {k}")
    if "content_identifier_cid" in bp and not CID.match(bp["content_identifier_cid"]):
        errors.append("identity: content_identifier_cid must be sha256:<64 hex>")

    gen = bp.get("generation", {})
    if gen.get("target_framework") not in ("open-agent-spec", "wayflow", "langgraph", "crewai", "autogen", "custom"):
        errors.append("generation: bad target_framework")

    model_refs = set()
    for s in bp.get("skill_bindings", []):
        if not SKILL_ID.match(s.get("skill_id", "")):
            errors.append(f"skill_bindings: bad skill_id {s.get('skill_id')!r} (TMF prefix is part of the ID)")
        impl = s.get("implementation", {})
        if impl.get("adapter") in ("mlflow_model", "huggingface_pipeline") and not impl.get("model_ref"):
            errors.append(f"skill_bindings: {s.get('skill_id')} model adapter without model_ref")
        if impl.get("model_ref"):
            model_refs.add(impl["model_ref"].split("@")[0])

    mb = {m["model_id"] for m in bp.get("model_bindings", [])}  # [EXT §2.2]
    for r in model_refs - mb:
        errors.append(f"model_bindings [EXT]: model_ref {r!r} has no authority binding (model_id/version/cid)")
    for m in bp.get("model_bindings", []):
        if not CID.match(m.get("cid", "")):
            errors.append(f"model_bindings: {m.get('model_id')} bad cid")

    servers = {s["name"] for s in bp.get("mcp_servers", [])}
    for name, t in bp.get("tool_bindings", {}).items():
        if t.get("type") in ("mcp_tool", "mcp_resource") and t.get("mcp_server") not in servers:
            errors.append(f"tool_bindings: {name!r} references unknown mcp_server {t.get('mcp_server')!r}")
    for s in bp.get("mcp_servers", []):
        for sec in s.get("env_secrets", []):
            if "=" in sec or len(sec) > 64:
                errors.append(f"mcp_servers: env_secrets must be names only, got {sec!r}")

    dep = bp.get("deployment", {})
    if dep.get("target_platform") == "local":
        errors.append("deployment: target_platform 'local' must not be committed; use environments[] [EXT §6.2]")

    envs = bp.get("environments", [])  # [EXT §6.2]
    env_names = {e["name"] for e in envs}
    for inv in bp.get("inventory", []):  # [EXT §6.3]
        if inv.get("environment") not in env_names:
            errors.append(f"inventory: environment {inv.get('environment')!r} not in environments[]")
        if not CID.match(inv.get("artifact_cid", "")):
            errors.append("inventory: artifact_cid must be sha256:<64 hex>")
        if inv.get("rollout", {}).get("state") == "rolled-back" and not inv["rollout"].get("previous_version"):
            errors.append("inventory: rolled-back entry must name previous_version")

    val = bp.get("validation", {})
    if val.get("failure_policy") != "fail_commit":
        errors.append("validation: production-bound bootstrap MUST use failure_policy=fail_commit")
    hooks = bp.get("lifecycle_hooks", {})
    if not hooks.get("pre_deploy"):
        errors.append("lifecycle_hooks: pre_deploy (signing) required")
    post = " ".join(h.get("script", "") for h in hooks.get("post_bootstrap", []))
    if "autonomy" not in post:
        errors.append("lifecycle_hooks: post_bootstrap should include autonomy-case generator (required at L3+)")


def validate_schema(doc, schema_path, errors):
    try:
        import json, warnings
        from pathlib import Path
        import jsonschema
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            schema = json.load(open(schema_path))
            base = schema.get("$id", Path(schema_path).resolve().as_uri())
            store = {base: schema}
            for name in ("environment-override.schema.json", "inventory-record.schema.json"):
                sub = json.load(open(Path(schema_path).parent / name))
                store[base.rsplit("/", 1)[0] + "/" + name] = sub
            resolver = jsonschema.RefResolver.from_schema(schema, store=store)
            jsonschema.validate(doc, schema, resolver=resolver)
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        errors.append(f"schema: {e}")


def main():
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        return 2
    from pathlib import Path
    schema_path = os.environ.get("SPEC444_SCHEMAS", "schemas") + "/bootstrap.schema.json"
    failed = False
    for p in paths:
        errors = []
        doc = yaml.safe_load(open(p))
        validate(doc, errors)
        validate_schema(doc, schema_path, errors)
        if errors:
            failed = True
            for e in errors:
                print(f"{p}: {e}", file=sys.stderr)
        else:
            print(f"{p}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
