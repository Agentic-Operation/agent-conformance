# Agent Conformance

Canonical conformance kit for the agent triad (Spec-443 / Spec-444 / Spec-445):

- `validators/` — `profile_lint.py`, `bootstrap_validate.py`, `card_validate.py` (per-artifact),
  `crosscheck.py` (triad joins C1–C20, manifest in agent-profile-management `spec/annexes/cross-check-manifest.md`)
- `runtime-check/verify_integrity.py` — stage-3 startup integrity check (CID + integrity_wrapper, optional cosign)
- `run-all.sh` — clones the three spec repos and runs validators + pytest suites + cross-check end-to-end
- `ci-templates/` — CI gate template for agent-instance repos

Spec repos run these from their `cross-triad` CI job (checkout of this repo). Validators resolve schemas
via `SPEC44X_SCHEMAS` env vars (set by `run-all.sh` / CI).

Spec repos: agent-profile-management · agent-bootstrap-management · agent-discovery-card · docs: agent-standard-docs
License: Apache-2.0
