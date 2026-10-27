# Ghidra-Rare notes: Falcon (NVIDIA Falcon)

This is the Ghidra-Rare fork of [marysaka/ghidra_falcon](https://github.com/marysaka/ghidra_falcon).
Ghidra-Rare tested it against envytools' `envydis` (MIT, run as a black box) and the envytools
Falcon documentation, and fixed what the tests found. Authors, upstream commit and the list of
changes are in [CREDITS.md](CREDITS.md); the upstream todo list and its status are in
[README.md](README.md). It targets Ghidra 12.1.4 and also builds on 12.1.3 and 12.2; prebuilt zips
are on the fork's Releases page.

## What it covers

| Language ID | envydis variant | Description |
|---|---|---|
| `falcon:LE:32:v0` | `-V fuc0` | Falcon v0 (G98-era units) |
| `falcon:LE:32:v3` | `-V fuc3` | Falcon v3 |
| `falcon:LE:32:v4` | `-V fuc4` | Falcon v4 |
| `falcon:LE:32:v5` | `-V fuc5 -F crypt` | Falcon v5 with the crypto coprocessor |
| `falcon:LE:32:v6` | `-V fuc6 -F crypt` | Falcon v6 with the crypto coprocessor |

- Every instruction envydis decodes for these variants, in envydis' syntax (with commas and without
  `$`).
- Semantics: sized (8/16/32-bit) ALU operations with the c/o/s/z flags in `csw`, shifts with carry,
  multiply, divide/modulo, bitfield `extr`/`extrs`/`ins`, `sext`, `xbit`, bit operations, every
  data addressing mode (`D[rN+imm]`, `D[rN+rM*size]`, `D[sp+imm]`, `D[sp+rN*size]`), stack
  `push`/`pop`/`mpush`/`mpop*`, calls and returns, conditional branches on flags and predicates,
  compare-and-branch, `setp`, I/O through an `io` address space. Pcodeops: see Known gaps.
- Spec files: cspec (arguments r10-r14, stack return address, as upstream), pspec (volatile I/O
  space), and the NVIDIA GR bootloader loader (Java).

## Testing

Requirements: Ghidra (`GHIDRA_INSTALL_DIR`; the suite links this directory in as
`Ghidra/Processors/Falcon`) and envytools: `test/build-oracles.sh <dir>` builds `envydis`,
`envyas` and the `test/slotdis.c` driver at a pinned commit.

```
test/run-tests.sh [workdir]          # compile, decode diff, every-entry test, emulator, faucon.asm
test/run-tests.sh [workdir] --real   # ... plus nouveau's falcon firmware
```

## Results

### Decoding vs envydis

`test/gen_corpus.py` writes one instruction per 8-byte slot: every value of the first two bytes
with four tails (all-zero, all-ones, two random: 262,144 slots) and 50,000 random slots.

| Language | Exact | Semantic | Both invalid | Differences |
|---|---|---|---|---|
| v0 | 86,944 | 1,219 | 223,981 | 0 |
| v3 | 98,476 | 1,256 | 212,412 | 0 |
| v4 | 98,476 | 3,716 | 209,952 | 0 |
| v5 | 185,424 | 9,329 | 117,391 | 0 |
| v6 | 185,424 | 9,329 | 117,391 | 0 |

"Exact" maps envydis' syntax (`$r0`, blank separators, `add b32`, `$flags`) to the module's
(`r0`, commas, `add_b32`, `csw`), drops envydis' branch-target label tags and `+0x0` offsets;
"semantic" additionally canonicalises numbers.

**Every-entry test** (`CoverageCheck.java`): all constructors of every language are reached (v0
198, v3 223, v4 228, v5 and v6 323).

### Emulator

`test/emu_tests.py` holds 42 cases for v3+ (run on v5 and v6) and 6 for v0, assembled once with
envyas (`test/emu/cases*.txt`), with expectations worked out from the envytools documentation:
add/adc/sub/sbb with carry, overflow and zero, 8/16-bit operations keeping the high bits, shifts
with the carry out and the size-masked count, `shlc`, `neg`, `not`, `cmp`/`cmpu`/`cmps`, `mulu`/
`muls`, logic flags, `extr`/`extrs`/`ins`, `sext`, `xbit`, `bset`/`bclr`, push/pop, call/ret,
conditional branches, loads/stores of each size, `mpush`/`mpop`, `hswap`, `setp` with a predicate
branch, `div`/`mod`, I/O write/read, and the v0 flag rules (`and`, `shl`, `xbit`, `movf`). Result:
all pass on v5, v6 and v0, and the deliberately wrong expectation of each set is reported.

### Real code

`test/real-binaries.sh` downloads nouveau's falcon firmware images (Linux v6.12, MIT; the
envyas-built images nouveau ships as C headers) by pinned URL and SHA-256 and checks (1) a linear
sweep: every address of envydis' linear disassembly decoded by both tools, and (2) a flow-based
import from the entry at 0 with auto-analysis and decompilation of every function.

| Image | Language | Linear sweep vs envydis | Functions | Bad instr. / errors | Decompiled |
|---|---|---|---|---|---|
| pmu/gt215.fuc3 | v3 | 1,131 agree (1 at the image end) | 1 | 0 / 0 | 1 / 1 |
| gr/hubgf100.fuc3 | v3 | 1,016 (1 at the image end) | 26 | 0 / 0 | 26 / 26 |
| pmu/gf119.fuc4 | v4 | 1,051 | 1 | 0 / 0 | 1 / 1 |
| gr/hubgk208.fuc5 | v5 | 891 (1 at the image end) | 24 | 0 / 0 | 24 / 24 |
| gr/hubgm107.fuc5 | v5 | 891 (1 at the image end) | 24 | 0 / 0 | 24 / 24 |
| gr/gpcgm107.fuc5 | v5 | 719 | 19 | 0 / 0 | 19 / 19 |

The PMU images dispatch through a process table held in DMEM (indirect calls), so flow analysis
from the entry reaches only the start-up code; the linear sweep covers all of them. The image-end
difference is envydis reporting `[incomplete]` for the padding byte at the end of the image.
Upstream's own test program `data/testing/faucon.asm`, assembled with envyas, decodes identically
(38 instructions). The GR bootloader loader was checked on a synthetic header around a nouveau
image (`test/LoaderCheck.java`); no freely licensed NVIDIA bootloader file exists.

## Known gaps

- **Pcodeops for state outside the core**: the crypto coprocessor commands (`c*`, `ci*`, its
  registers are modelled but the operations are not specified anywhere public), transfers
  (`xcld`, `xdld`, `xdst`, `xcwait`, `xdwait`, `xdfence`), TLB operations (`itlb`, `ptlb`,
  `vtlb`), `sleep`, `trap`, `exit`, interrupt-enable side effects. They are DMA engines, the MMU,
  the security engine and the interrupt controller.
- **`mpush`/`mpop` order**: no public documentation; the module pushes r0..rN (rN at the lowest
  address) and pops them back, which is what nouveau's prologues/epilogues need, unverified on
  hardware.
- **Calling convention**: the upstream cspec (r10-r14 arguments) is kept; nouveau's hand-written
  firmware does not follow a single convention, so it is unverified.
- **No ELF opinion or DWARF map**: Falcon code is not distributed as ELF and no compiler emits DWARF
  for it.
- Decompiler: memory reads implied by pcodeops are invisible to the decompiler (upstream todo); the
  I/O space being plain volatile memory now removes most such pcodeops.

## Unverified

- Hardware behaviour: everything follows the envytools documentation; there is no simulator.
- The v6-only opcodes `fa/7` and `fe/5` are unknown to envydis and stay undecoded.
- No freely licensed v0/v4 crypto or v6 code was available; v0 and v6 are covered by the decode
  differential and the emulator only.

## Confirmed reference-tool bugs

None found in envydis.
