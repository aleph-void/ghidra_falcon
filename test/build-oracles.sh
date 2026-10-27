#!/usr/bin/env bash
# Build envytools (MIT) at a pinned commit: envydis/envyas for the tests and the libraries
# test/slotdis.c links against (envydis is run as a black-box reference disassembler).
#   test/build-oracles.sh <dir>     prints FALCON_SLOTDIS, ENVYDIS, ENVYAS
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
D=$(mkdir -p "$1" && cd "$1" && pwd)
cd "$D"
[[ -d envytools ]] || git clone -q https://github.com/envytools/envytools
cd envytools && git checkout -q f102b82381f3f11cee113d16374c87091db039d9
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release >/dev/null && make -j"$(nproc)" envydis envyas >/dev/null
gcc -O2 -w -o "$D/falcon-slotdis" "$HERE/slotdis.c" -I../include -Wl,--start-group envydis/libenvy.a \
	easm/libeasm.a util/libenvyutil.a -Wl,--end-group
echo "FALCON_SLOTDIS=$D/falcon-slotdis"
echo "ENVYDIS=$D/envytools/build/envydis/envydis"
echo "ENVYAS=$D/envytools/build/envydis/envyas"
