#!/bin/bash
# Verify the architecture and minimum macOS version of a .app bundle.
#
# Usage: scripts/verify_bundle.sh <path-to-app> <expected-arch> [max-macos-version]
# Example: scripts/verify_bundle.sh dist/AirType.app x86_64 12.0
#
# Exits non-zero if any Mach-O file inside the bundle has a different
# architecture or requires a macOS version newer than max-macos-version.

set -euo pipefail

APP="${1:?usage: verify_bundle.sh <path-to-app> <expected-arch> [max-macos-version]}"
EXPECT_ARCH="${2:?expected arch is required, e.g. x86_64 or arm64}"
MAX_MACOS="${3:-12.0}"

if [ ! -d "$APP" ]; then
    echo "error: bundle not found: $APP" >&2
    exit 1
fi

status=0

# version_gt A B: exits 0 when A > B, 1 otherwise.
version_gt() {
    awk -v a="$1" -v b="$2" 'BEGIN {
        na = split(a, x, ".")
        nb = split(b, y, ".")
        for (i = 1; i <= 3; i++) {
            xi = (i <= na) ? x[i] + 0 : 0
            yi = (i <= nb) ? y[i] + 0 : 0
            if (xi > yi) exit 0
            if (xi < yi) exit 1
        }
        exit 1
    }'
}

while IFS= read -r file; do
    ftype="$(file -b "$file" 2>/dev/null || true)"
    case "$ftype" in
        *Mach-O*) ;;
        *) continue ;;
    esac

    archs="$(lipo -archs "$file" 2>/dev/null || true)"
    case " $archs " in
        *" $EXPECT_ARCH "*) ;;
        *)
            echo "error: wrong architecture: $file (found: $archs, expected: $EXPECT_ARCH)" >&2
            status=1
            ;;
    esac

    minos="$(otool -l "$file" | awk '$1 == "cmd" && $2 == "LC_BUILD_VERSION" { build = 1; next } build && $1 == "minos" { print $2; exit }')"
    if [ -z "$minos" ]; then
        minos="$(otool -l "$file" | awk '$1 == "cmd" && $2 == "LC_VERSION_MIN_MACOSX" { old = 1; next } old && $1 == "version" { print $2; exit }')"
    fi

    if [ -n "$minos" ] && version_gt "$minos" "$MAX_MACOS"; then
        echo "error: requires macOS $minos, above the allowed $MAX_MACOS: $file" >&2
        status=1
    fi
done < <(find "$APP" -type f -print)

if [ "$status" -ne 0 ]; then
    exit 1
fi

echo "OK: every Mach-O file in $APP supports $EXPECT_ARCH and macOS <= $MAX_MACOS"
