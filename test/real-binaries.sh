#!/usr/bin/env bash
# Real Falcon code: nouveau's falcon firmware (Linux kernel, MIT; the envyas-built images that
# nouveau ships as C headers), downloaded from a pinned kernel tag and checked against SHA-256;
# nothing is committed.
#   1. linear sweep: every instruction address of envydis' linear disassembly of the image is
#      decoded by Ghidra (DumpAt.java) and envydis (slotdis.c -l), and compared (compare.py)
#   2. flow analysis: headless import (raw, entry at 0), auto-analysis, every function decompiled
#      (RealCheck.java): functions, bad-instruction/error bookmarks, decompile failures
#   test/real-binaries.sh <workdir>     Environment: GHIDRA_INSTALL_DIR, FALCON_SLOTDIS, ENVYDIS
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/env.sh"
: "${FALCON_SLOTDIS:?set FALCON_SLOTDIS}" "${ENVYDIS:?set ENVYDIS}"
W=$(mkdir -p "$1" && cd "$1" && pwd)
cd "$W"
B=https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/gpu/drm/nouveau/nvkm
# file, sha256, envydis variant, Ghidra language variant
SAMPLES=(
	"subdev/pmu/fuc/gt215.fuc3.h a90747e3c30fb4ae2b8865a2c0057f3541aa00d0d9798c14311cee013e1bdd46 fuc3 v3"
	"engine/gr/fuc/hubgf100.fuc3.h 608c7a1c63d12ebeb56839cdab28dfd96eba0170a17f1eb9b509859561f31ec7 fuc3 v3"
	"subdev/pmu/fuc/gf119.fuc4.h ee3c298ed99d665fc251528597c6f8bfb978d529f478ed063e123209cf1b9c2b fuc4 v4"
	"engine/gr/fuc/hubgk208.fuc5.h a85e8918462f1f5c1e85d3b0619f80aa3c42af2aec74b809acda2495ae20e32e fuc5 v5"
	"engine/gr/fuc/hubgm107.fuc5.h e79f3007e309f078335d8514b4cc5d50a5c23ffa8e6dbb082eae9e0f86f7acc4 fuc5 v5"
	"engine/gr/fuc/gpcgm107.fuc5.h 9a25b7c9d0bb1c40887e76f2883f4d5d397462603d055124d80960622e062812 fuc5 v5"
)
rc=0
for s in "${SAMPLES[@]}"; do
	read -r f sum var lv <<<"$s"
	n=$(echo "$f" | tr / _)
	[[ -f $n ]] || curl -sSLf -o "$n" "$B/$f"
	echo "$sum  $n" | sha256sum -c --quiet - || { echo "checksum mismatch: $n" >&2; exit 1; }
	python3 "$HERE/real/extract_fuc.py" "$n" "$n.bin" >/dev/null
	echo "-- $f (falcon:LE:32:$lv)"
	"$ENVYDIS" -m falcon -V "$var" -i -n <"$n.bin" | sed -n 's/^\([0-9a-f]\{8\}\):.*/\1/p' >"$n.addrs"
	"$FALCON_SLOTDIS" "$var" 8 "$n.bin" -l "$n.addrs" -b 0 >"$n.env"
	"$HERE/ghidra-script.sh" raw "falcon:LE:32:$lv" "$n.bin" DumpAt.java "$W/$n.addrs" "$W/$n.gh"
	r=$(python3 "$HERE/compare.py" "$n.gh" "$n.env" "$n.bin" --show 3 >"$n.cmp" && echo ok || echo FAIL)
	echo "   linear sweep vs envydis: $(head -1 "$n.cmp" | sed 's/^slots //') ($r)"
	[[ $r == ok ]] || rc=1
	p=$(mktemp -d "${PROJ_DIR:-${TMPDIR:-/tmp}}/falcon-real.XXXXXX")
	"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$p" p -import "$W/$n.bin" -loader BinaryLoader \
		-processor "falcon:LE:32:$lv" -scriptPath "$HERE" -preScript FalconEntry.java \
		-postScript RealCheck.java "$W/$n.sum" "$W/$n.lst" "$W/$n.c" 60 -deleteProject >"$W/$n.log" 2>&1 ||
		{ tail -20 "$W/$n.log" >&2; rc=1; }
	rm -rf "$p"
	grep -E "^(functions|instructions|bad-instruction|error bookmarks|decompile|functions whose)" "$W/$n.sum" | sed 's/^/   /'
done
exit $rc
