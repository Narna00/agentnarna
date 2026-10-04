#!/bin/bash
# =============================================================================
# Auth-helper — sourced by recon_engine.sh, vuln_scanner.sh, full_hunt.sh.
#
# Reads AGENTNARNA_AUTH_HEADERS (newline-separated "Name: value" entries) and
# AGENTNARNA_SESSION_ID from the environment. BBHUNT_* remains a fallback.
# The helper exposes them as:
#
#   BB_AUTH_ARGS=(-H 'Name1: value1' -H 'Name2: value2' ...)    # bash array
#   BB_AUTH_SESSION_ID="<12-char-hex>"                          # safe to log
#
# Callers splat the array into curl/httpx/katana/nuclei/ffuf invocations:
#
#   curl -sk ${BB_AUTH_ARGS[@]+"${BB_AUTH_ARGS[@]}"} "$url"
#   nuclei -l "$list" ${BB_AUTH_ARGS[@]+"${BB_AUTH_ARGS[@]}"} -o "$out"
#
# The verbose expansion is intentional: bash 3.2 on macOS aborts under set -u
# when expanding an empty array as "${BB_AUTH_ARGS[@]}".
# Empty session = empty array = no behavior change for anonymous hunts.
# Compatible with bash 3.2 (macOS default).
# =============================================================================

# Guard: source-only, no execution.
[ "${BASH_SOURCE[0]}" = "$0" ] && {
    echo "auth_helper.sh must be sourced, not executed" >&2
    return 1 2>/dev/null || exit 1
}

BB_AUTH_ARGS=()
_bb_headers="${AGENTNARNA_AUTH_HEADERS:-${BBHUNT_AUTH_HEADERS:-}}"
BB_AUTH_SESSION_ID="${AGENTNARNA_SESSION_ID:-${BBHUNT_SESSION_ID:-}}"

if [ -n "$_bb_headers" ]; then
    # Read newline-separated headers into the array. Use here-string + read
    # so this works on bash 3.2 (no mapfile).
    while IFS= read -r _bb_h; do
        # Skip empty / commented entries.
        case "$_bb_h" in
            ''|'#'*) continue ;;
        esac
        # Reject any header containing CR — protects against injection
        # if the env var was poorly handled upstream. (LF can't appear
        # inside a single line read by `read`.)
        case "$_bb_h" in
            *$'\r'*) continue ;;
        esac
        BB_AUTH_ARGS+=(-H "$_bb_h")
    done <<< "$_bb_headers"
    unset _bb_h

    # Compute session_id if caller didn't already export one.
    # Falls back through shasum (mac) → sha256sum (linux) → md5sum (last
    # resort, still stable). Empty if no hasher is available.
    if [ -z "$BB_AUTH_SESSION_ID" ]; then
        _bb_hash=""
        if command -v shasum >/dev/null 2>&1; then
            _bb_hash=$(printf '%s' "$_bb_headers" | LC_ALL=C sort | shasum -a 256 2>/dev/null | cut -c1-12)
        elif command -v sha256sum >/dev/null 2>&1; then
            _bb_hash=$(printf '%s' "$_bb_headers" | LC_ALL=C sort | sha256sum 2>/dev/null | cut -c1-12)
        fi
        BB_AUTH_SESSION_ID="$_bb_hash"
        export AGENTNARNA_SESSION_ID="$_bb_hash" BBHUNT_SESSION_ID="$_bb_hash"
        unset _bb_hash
    fi
fi
unset _bb_headers

# Banner — only shows session_id, never raw values.
bb_auth_banner() {
    if [ -n "$BB_AUTH_SESSION_ID" ]; then
        echo "[auth] session=$BB_AUTH_SESSION_ID headers=$(( ${#BB_AUTH_ARGS[@]} / 2 ))"
    fi
}

# True if auth is active for this run.
bb_auth_active() {
    [ "${#BB_AUTH_ARGS[@]}" -gt 0 ]
}
