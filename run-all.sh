#!/usr/bin/env bash
# Run the full triad conformance suite: checks out the three spec repos at main (or $SPEC_BRANCH),
# runs per-artifact validators, pytest suites, stage-3 integrity check, and the C1-C20 cross-check.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-/tmp/agent-conformance-run}"
BRANCH="${SPEC_BRANCH:-main}"
mkdir -p "$WORK"
for pair in "agent-profile-management:profile" "agent-bootstrap-management:bootstrap" "agent-discovery-card:card"; do
  repo="${pair%%:*}"; dir="${pair##*:}"
  if [ ! -d "$WORK/$dir" ]; then
    git clone -q --depth 1 --branch "$BRANCH" "https://github.com/Agentic-Operation/$repo.git" "$WORK/$dir"
  fi
done
export SPEC443_SCHEMAS="$WORK/profile/schemas" SPEC444_SCHEMAS="$WORK/bootstrap/schemas" SPEC445_SCHEMAS="$WORK/card/schemas"
pip install -q jsonschema pyyaml pytest
python "$HERE/validators/profile_lint.py" "$WORK/profile/examples/loyalty-agent/profile.json"
python "$HERE/validators/bootstrap_validate.py" "$WORK/bootstrap/examples/loyalty-agent/bootstrap.yaml"
python "$HERE/validators/card_validate.py" "$WORK/card/examples/loyalty-agent/card.json"
python "$HERE/runtime-check/verify_integrity.py" "$WORK/card/examples/loyalty-agent/card.json"
python -m pytest "$WORK/profile/conformance-kit/test-suites" "$WORK/bootstrap/conformance-kit/test-suites" "$WORK/card/conformance-kit/test-suites" -q
python "$HERE/validators/crosscheck.py" --profile "$WORK/profile/examples/loyalty-agent/profile.json" --bootstrap "$WORK/bootstrap/examples/loyalty-agent/bootstrap.yaml" --card "$WORK/card/examples/loyalty-agent/card.json"
echo "ALL TRIAD CHECKS PASSED"
