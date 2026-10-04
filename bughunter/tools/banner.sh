#!/usr/bin/env bash
# Shared agentnarna shell banner. Quiet for pipes and repeat child processes.

_an_center() {
    local text="$1" width=48 pad
    pad=$(( (width - ${#text}) / 2 )); [ "$pad" -lt 0 ] && pad=0
    printf '%*s%s' "$pad" '' "$text"
}

print_banner() {
    local subtitle="${1:-}" target="${2:-}"
    shift 2 2>/dev/null || true
    [ -n "${AGENTNARNA_BANNER_SHOWN:-${BBHUNT_BANNER_SHOWN:-}}" ] && return 0
    [ -n "${AGENTNARNA_NO_BANNER:-${BBHUNT_NO_BANNER:-}}" ] && return 0
    [ -t 1 ] || return 0

    local PINK=$'\033[38;5;213m' CYAN=$'\033[38;5;51m' WHITE=$'\033[1;37m' DIM=$'\033[2m' NC=$'\033[0m'
    [ -n "${NO_COLOR:-}" ] && PINK='' CYAN='' WHITE='' DIM='' NC=''
    printf '\n  %s%s%s\n' "$PINK" '▄▀█ █▀▀ █▀▀ █▄░█ ▀█▀ █▄░█ ▄▀█ █▀█ █▄░█ ▄▀█' "$NC"
    printf '  %s%s%s\n' "$CYAN" '█▀█ █▄█ ██▄ █░▀█ ░█░ █░▀█ █▀█ █▀▄ █░▀█ █▀█' "$NC"
    printf '  %s%s%s\n' "$DIM" "$(_an_center 'lead → adapt → verify → report')" "$NC"
    [ -n "$subtitle" ] && printf '  %s%s%s\n' "$WHITE" "$(_an_center "$subtitle")" "$NC"
    [ -n "$target" ] && printf '  %s%s%s\n' "$CYAN" "$(_an_center "target: $target")" "$NC"
    local idx=1 step label detail
    for step in "$@"; do
        label="${step%%|*}"; detail=''; [[ "$step" == *'|'* ]] && detail="${step#*|}"
        printf '  %s%02d%s  %s%s%s  %s%s%s\n' "$CYAN" "$idx" "$NC" "$WHITE" "$label" "$NC" "$DIM" "$detail" "$NC"
        idx=$((idx + 1))
    done
    printf '\n'
    export AGENTNARNA_BANNER_SHOWN=1 BBHUNT_BANNER_SHOWN=1
}
