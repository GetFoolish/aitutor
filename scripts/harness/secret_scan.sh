#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_REL="${1:-artifacts/harness/secret_scan.json}"
if [[ "$OUT_REL" = /* ]]; then
  OUT_PATH="$OUT_REL"
else
  OUT_PATH="$ROOT/$OUT_REL"
fi
mkdir -p "$(dirname "$OUT_PATH")"

cd "$ROOT"

# Build candidate file list (prefer PR diff, fallback to full tracked files)
FILES=()

if [[ -n "${HARNESS_SECRET_SCAN_FILES:-}" ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] && FILES+=("$line")
  done <<< "${HARNESS_SECRET_SCAN_FILES}"
else
  BASE_REF=""
  if [[ -n "${GITHUB_BASE_REF:-}" ]] && git rev-parse --verify "origin/${GITHUB_BASE_REF}" >/dev/null 2>&1; then
    BASE_REF="origin/${GITHUB_BASE_REF}"
  elif [[ -n "${HARNESS_SECRET_SCAN_BASE:-}" ]] && git rev-parse --verify "${HARNESS_SECRET_SCAN_BASE}" >/dev/null 2>&1; then
    BASE_REF="${HARNESS_SECRET_SCAN_BASE}"
  elif git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    BASE_REF="HEAD~1"
  fi

  if [[ -n "$BASE_REF" ]]; then
    while IFS= read -r f; do
      [[ -n "$f" ]] && FILES+=("$f")
    done < <(git diff --name-only "$BASE_REF...HEAD")
  else
    while IFS= read -r f; do
      [[ -n "$f" ]] && FILES+=("$f")
    done < <(git ls-files)
  fi
fi

# Fallback if diff had no files
if [[ ${#FILES[@]} -eq 0 ]]; then
  while IFS= read -r f; do
    [[ -n "$f" ]] && FILES+=("$f")
  done < <(git ls-files)
fi

# Exclude heavy/generated/vendor areas
FILTERED=()
for f in "${FILES[@]}"; do
  [[ ! -f "$f" ]] && continue
  case "$f" in
    artifacts/*|node_modules/*|venv/*|frontend/node_modules/*|frontend/bun.lock|frontend/package-lock.json)
      continue
      ;;
  esac
  FILTERED+=("$f")
done

if [[ ${#FILTERED[@]} -eq 0 ]]; then
  cat > "$OUT_PATH" <<JSON
{
  "ok": true,
  "scanned_files": 0,
  "matches": []
}
JSON
  exit 0
fi

# Patterns intentionally strict to reduce false positives.
PATTERN='(?i)(greptile[_-]?api[_-]?key|api[_-]?key|secret|token)\s*[:=]\s*["\x27]?[A-Za-z0-9_\-+/=]{24,}'

TMP_MATCH="$(mktemp)"
set +e
rg --pcre2 -n -H "$PATTERN" "${FILTERED[@]}" > "$TMP_MATCH"
RC=$?
set -e

if [[ $RC -eq 0 ]]; then
  MATCH_COUNT=$(wc -l < "$TMP_MATCH" | tr -d ' ')
  {
    echo '{'
    echo '  "ok": false,'
    echo "  \"scanned_files\": ${#FILTERED[@]},"
    echo "  \"match_count\": ${MATCH_COUNT},"
    echo '  "matches": ['
    awk 'BEGIN{first=1} {
      gsub(/\\/, "\\\\", $0);
      gsub(/"/, "\\\"", $0);
      if (!first) printf(",\n");
      first=0;
      printf("    \"%s\"", $0);
    } END{printf("\n")}' "$TMP_MATCH"
    echo '  ]'
    echo '}'
  } > "$OUT_PATH"
  rm -f "$TMP_MATCH"
  echo "Secret scan failed: potential leaked secrets detected"
  exit 1
fi

rm -f "$TMP_MATCH"
cat > "$OUT_PATH" <<JSON
{
  "ok": true,
  "scanned_files": ${#FILTERED[@]},
  "matches": []
}
JSON

exit 0
