#!/usr/bin/env bash
# Smoke-test a running stack: the web app, the API and the data it serves.
#
#   scripts/smoke-test.sh                        # local Compose stack
#   scripts/smoke-test.sh https://app.example.ca # a deployment (API behind the same host)
#
# API_URL overrides where the API is reached (default: $BASE_URL, falling back to :8000 locally).
# INSECURE=1 accepts a self-signed certificate (e.g. Caddy's for https://localhost).
set -euo pipefail

BASE_URL="${1:-http://localhost}"
API_URL="${API_URL:-$BASE_URL}"
if [[ "$BASE_URL" == "http://localhost" && -z "${1:-}" ]]; then API_URL="${API_URL/http:\/\/localhost/http://localhost:8000}"; fi

failures=0
check() { # name url [jq-ish grep pattern]
  local name="$1" url="$2" pattern="${3:-}" body status
  body="$(curl -fsS --max-time 15 ${INSECURE:+--insecure} "$url" 2>/dev/null)" && status=ok || status=fail
  if [[ "$status" == ok && -n "$pattern" ]] && ! grep -q "$pattern" <<<"$body"; then status="unexpected response"; fi
  if [[ "$status" == ok ]]; then printf '  \033[32m✓\033[0m %s\n' "$name"; else printf '  \033[31m✗\033[0m %s (%s) %s\n' "$name" "$status" "$url"; failures=$((failures + 1)); fi
}

echo "Web app  $BASE_URL"
check "SPA served" "$BASE_URL/" '<div id="app"'
echo "API      $API_URL"
check "health + database" "$API_URL/api/v1/health" '"database": *"up"'
check "listings" "$API_URL/api/v1/houses?page_size=1" '"items"'
check "markets" "$API_URL/api/v1/markets" '\['
check "cash-flow defaults" "$API_URL/api/v1/cashflow/defaults" 'interest_rate_pct'
check "data sources" "$API_URL/api/v1/data-sources" '{'

if ((failures)); then echo "$failures check(s) failed"; exit 1; fi
echo "All checks passed"
