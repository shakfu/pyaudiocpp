#!/usr/bin/env bash
# Test pyaudiocpp on Linux x86-64: upstream's prebuilt lib, then a source build.
#
# Usage: scripts/test-linux.sh            (from anywhere in the checkout)
#   VARIANT=vulkan scripts/test-linux.sh  lib variant: cpu (default), cpu-portable,
#                                         vulkan, vulkan-portable, cuda12.8, cuda13.3
#   SKIP_SOURCE=1                         skip the source build
#
# Needs: git gh (logged in) uv cmake make c++, and libespeak-ng1 for Kokoro.
# Writes build/linux-check.log. Exits nonzero if any step failed.

set -uo pipefail

RUN_ID=37571363883
ARTIFACT_PREFIX=audio-v0.9.1-lib-test-2-lib-ubuntu-x64
VARIANT=${VARIANT:-cpu}
case $VARIANT in
    vulkan*) BACKEND=vulkan ;;
    cuda*) BACKEND=cuda ;;
    *) BACKEND=cpu ;;
esac

cd "$(dirname "$0")/.." || exit 2
mkdir -p build
LOG=build/linux-check.log
exec > >(tee "$LOG") 2>&1

FAILED=()
step() {
    echo
    echo "=== $*"
    "$@" || { echo "--- FAILED ($?): $*"; FAILED+=("$*"); }
}

for cmd in git gh uv cmake make c++; do
    command -v "$cmd" >/dev/null || { echo "missing: $cmd"; exit 2; }
done
ldconfig -p | grep -q libespeak-ng || echo "warning: libespeak-ng not found; Kokoro tests will fail"

echo "=== host"
uname -srm
lscpu | grep -E '^(Model name|CPU\(s\)|Thread|Core|Socket|Flags)' | cut -c1-200
echo "nproc: $(nproc)"

step make sync models

LIBDIR=thirdparty/lib-linux-$VARIANT
if [ ! -d "$LIBDIR" ]; then
    step gh run download "$RUN_ID" -R 0xShug0/audio.cpp -n "$ARTIFACT_PREFIX-$VARIANT" -D "$LIBDIR"
    # The artifact may wrap a tarball.
    find "$LIBDIR" -name '*.tar.gz' -exec tar -xzf {} -C "$LIBDIR" \;
fi
LIB=$(find "$PWD/$LIBDIR" -name 'libaudiocpp.so*' -type f | head -1)
if [ -z "$LIB" ]; then
    echo "no libaudiocpp.so in $LIBDIR"
    FAILED+=("find prebuilt")
else
    export AUDIOCPP_LIBRARY=$LIB
    echo
    echo "=== prebuilt: $LIB"
    ldd "$LIB"
    echo "non-audiocpp exports:"
    nm -D --defined-only "$LIB" | awk '{print $NF}' | grep -v '^audiocpp_' | head -20

    export AUDIOCPP_TEST_BACKEND=$BACKEND
    step make test
    step make demo DEMO_ARGS="--backend $BACKEND"
    unset AUDIOCPP_TEST_BACKEND

    backends=(--backend cpu)
    [ "$BACKEND" != cpu ] && backends+=(--backend "$BACKEND")
    step env PYTHONPATH=src uv run python tests/bench.py "${backends[@]}" \
        --threads 1 --threads 2 --threads 4 --threads "$(nproc)"
    unset AUDIOCPP_LIBRARY
fi

if [ -z "${SKIP_SOURCE:-}" ]; then
    step make lib
    step make test
    step make demo
fi

echo
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "=== all steps passed; log: $LOG"
else
    echo "=== ${#FAILED[@]} step(s) failed; log: $LOG"
    printf '  %s\n' "${FAILED[@]}"
    exit 1
fi
