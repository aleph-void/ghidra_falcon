#!/usr/bin/env bash
# Falcon module test suite: everything that needs no downloaded inputs.
#
#   GHIDRA_INSTALL_DIR=<Ghidra 12.1.x/12.2> test/run-tests.sh [workdir] [--real]
#
# 1. the five specs (v0, v3, v4, v5, v6) compile
# 2. decode differential against envydis (envytools, a black box through slotdis.c) per language:
#    every value of the first two bytes with 4 tails, plus 50,000 random slots; 0 unexplained
# 3. every SLEIGH constructor of every language is reached by that corpus
# 4. p-code: hand-computed emulator cases (EmuCheck.java) for v5 and v6 (42 incl. one deliberately
#    wrong expectation) and for v0 (6, idem)
# 5. upstream's own test program data/testing/faucon.asm, assembled with envyas, decodes like envydis
# --real adds step 6: nouveau's falcon firmware (real-binaries.sh)
#
# Environment: GHIDRA_INSTALL_DIR, PROJ_DIR (headless projects; no path component may start with a
# dot), FALCON_SLOTDIS, ENVYDIS, ENVYAS (test/build-oracles.sh builds them), QUICK=1 (10,000 random).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
MOD=$(cd "$HERE/.." && pwd)
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
: "${FALCON_SLOTDIS:?set FALCON_SLOTDIS (test/build-oracles.sh)}" "${ENVYDIS:?set ENVYDIS}" "${ENVYAS:?set ENVYAS}"
export FALCON_SLOTDIS ENVYDIS
REAL=0
ARGS=()
for a in "$@"; do if [[ $a == --real ]]; then REAL=1; else ARGS+=("$a"); fi; done
W=$(readlink -m "${ARGS[0]:-${TMPDIR:-/tmp}/falcon-tests}")
mkdir -p "$W"
export TMPDIR=$W PROJ_DIR=${PROJ_DIR:-$W}
source "$HERE/env.sh"
fail=0
P="$GHIDRA_INSTALL_DIR/Ghidra/Processors/Falcon"
if [[ ! -e $P ]]; then ln -s "$MOD" "$P"; elif [[ $(readlink -f "$P") != "$MOD" ]]; then echo "warning: $P exists and is not this module" >&2; fi
# language variant, envydis variant and features
VERS=("v0 fuc0" "v3 fuc3" "v4 fuc4" "v5 fuc5 -F crypt" "v6 fuc6 -F crypt")

echo "== 1. SLEIGH compiles"
for v in 0 3 4 5 6; do
	"$GHIDRA_INSTALL_DIR/support/sleigh" "$MOD/data/languages/falcon_v$v.slaspec" 2>&1 | grep -E "^ERROR" && exit 1 || true
	echo "   falcon_v$v.sla: $(stat -c %s "$MOD/data/languages/falcon_v$v.sla") bytes"
done

RAND=50000; [[ -n ${QUICK:-} ]] && RAND=10000
python3 "$HERE/gen_corpus.py" "$W/all.bin" $RAND 1 | sed 's/^/   /'
echo "== 2. decode differential against envydis"
for e in "${VERS[@]}"; do
	read -r lv var feat <<<"$e"
	"$FALCON_SLOTDIS" "$var" 8 "$W/all.bin" $feat >"$W/en_$lv.txt"
	"$HERE/ghidra-slots.sh" "falcon:LE:32:$lv" "$W/all.bin" 8 "$W/gh_$lv.txt"
	python3 "$HERE/compare.py" "$W/gh_$lv.txt" "$W/en_$lv.txt" "$W/all.bin" --show 2 >"$W/compare_$lv.txt" || fail=1
	echo "   $lv: $(head -1 "$W/compare_$lv.txt" | sed 's/^slots //'); $(tail -1 "$W/compare_$lv.txt")"
done

echo "== 3. every constructor is reached"
for e in "${VERS[@]}"; do
	read -r lv _ <<<"$e"
	"$HERE/ghidra-script.sh" raw "falcon:LE:32:$lv" "$W/all.bin" CoverageCheck.java "$W/coverage_$lv.txt" 64 1 8
	echo "   $lv: $(tail -1 "$W/coverage_$lv.txt")"
	grep -q " 0 unreached" "$W/coverage_$lv.txt" || { grep ^unreached "$W/coverage_$lv.txt"; fail=1; }
done

echo "== 4. p-code: hand-computed emulator cases"
python3 "$HERE/emu_tests.py" "$W/emu" | sed 's/^/   /'
for lv in v5 v6 v0; do
	sfx=""; [[ $lv == v0 ]] && sfx=_v0
	"$HERE/ghidra-script.sh" raw "falcon:LE:32:$lv" "$W/emu/emu$sfx.bin" EmuCheck.java "$W/emu/tests$sfx.txt" "$W/emu/out_$lv.txt"
	echo "   $lv: $(tail -1 "$W/emu/out_$lv.txt")"
	grep -q " 0 failed, [1-9][0-9]* broken expectations detected, 0 missed" "$W/emu/out_$lv.txt" || { grep ^FAIL "$W/emu/out_$lv.txt"; fail=1; }
done

echo "== 5. upstream's test program (data/testing/faucon.asm, envyas -V fuc5 -F crypt)"
"$ENVYAS" -m falcon -V fuc5 -F crypt "$MOD/data/testing/faucon.asm" -i -o "$W/faucon.bin"
"$ENVYDIS" -m falcon -V fuc5 -F crypt -i -n <"$W/faucon.bin" | sed -n 's/^\([0-9a-f]\{8\}\):.*/\1/p' >"$W/faucon.addrs"
"$FALCON_SLOTDIS" fuc5 8 "$W/faucon.bin" -F crypt -l "$W/faucon.addrs" -b 0 >"$W/faucon.env"
"$HERE/ghidra-script.sh" raw falcon:LE:32:v5 "$W/faucon.bin" DumpAt.java "$W/faucon.addrs" "$W/faucon.gh"
python3 "$HERE/compare.py" "$W/faucon.gh" "$W/faucon.env" "$W/faucon.bin" >"$W/faucon.cmp" || fail=1
echo "   $(head -1 "$W/faucon.cmp" | sed 's/^slots //'); $(tail -1 "$W/faucon.cmp")"

if ((REAL)); then
	echo "== 6. real code: nouveau falcon firmware"
	"$HERE/real-binaries.sh" "$W/real" || fail=1
fi
echo
((fail == 0)) && echo "ALL TESTS PASSED" || echo "TESTS FAILED"
exit $fail
