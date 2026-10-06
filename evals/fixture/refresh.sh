#!/usr/bin/env bash
# Regenerate evals/fixture/project/ from the spaceflights-pandas starter.
#
# The snapshot is committed so evals run offline and deterministically. Re-run
# this script when the starter changes, then review the diff before committing.
#
# Usage: evals/fixture/refresh.sh                        # latest Kedro release
#        KEDRO_VERSION=1.7.0 evals/fixture/refresh.sh    # a specific release
# Requires: uv (Kedro runs in an isolated env via uvx; the starter version
# follows the Kedro version).
set -euo pipefail

KEDRO_VERSION="${KEDRO_VERSION:-latest}"
FIXTURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$FIXTURE_DIR/project"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Resolve "latest" to a concrete version first, so the scaffold and the
# recorded STARTER_VERSION always match.
if [ "$KEDRO_VERSION" = "latest" ]; then
  KEDRO_VERSION="$(uvx --from kedro@latest python -c 'import kedro; print(kedro.__version__)' 2>/dev/null)" || {
    echo "Could not resolve the latest Kedro release. Set KEDRO_VERSION to pin one." >&2
    exit 1
  }
fi

(cd "$TMP" && KEDRO_DISABLE_TELEMETRY=1 uvx --from "kedro==$KEDRO_VERSION" \
  kedro new --name eval-project --starter spaceflights-pandas >/dev/null)
SRC="$TMP/eval-project"

# Text files only: config, source and tests. Data, docs and notebooks are not
# useful as prompt context.
rm -rf "$TARGET"
mkdir -p "$TARGET"
(
  cd "$SRC"
  find conf src tests pyproject.toml requirements.txt -type f \
    \( -name '*.py' -o -name '*.yml' -o -name '*.yaml' -o -name '*.toml' -o -name '*.txt' \) \
    -print0 | xargs -0 -I{} cp --parents {} "$TARGET"
)

echo "kedro $KEDRO_VERSION" > "$FIXTURE_DIR/STARTER_VERSION"
echo "Refreshed $TARGET with kedro $KEDRO_VERSION"
