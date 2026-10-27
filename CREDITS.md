# Credits: Falcon (NVIDIA Falcon) module

This module is a community SLEIGH module that Ghidra-Rare imported, tested and fixed.
Ghidra-Rare's changes are listed below.

## Upstream

| | |
|---|---|
| Source | [marysaka/ghidra_falcon](https://github.com/marysaka/ghidra_falcon), commit `b44f819db99cd1d673ff8334421917cb7f6edfd8` (2024-09-07) |
| License | ISC (`LICENSE`, Copyright 2019 marysaka, hthh) |
| Original authors | Mary Guillemard ([@marysaka](https://github.com/marysaka); commits as "Thog", "Mary", "Mary Guillemard"): module structure, decoding, falcon variants, the NVIDIA GR bootloader loader, CI; hthh (commits as "hthh"): semantics, crypto instructions, README; Valentin B. ([@vbe0201](https://github.com/vbe0201)): ISA description update, Ghidra 9.2 build; Antonio Vázquez Blanco ([@antoniovazquezblanco](https://github.com/antoniovazquezblanco)): CI for multiple Ghidra versions |
| envytools | `data/languages/envydis.sinc` and the comments in the other .sinc files quote envytools' Falcon instruction tables (`envydis/falcon.c`, MIT, copyright Marcin Kościelnicki and the envytools contributors; the notice is kept in envydis.sinc). Ghidra-Rare's semantics follow the envytools Falcon documentation (`docs/hw/falcon/*.rst`, MIT) |
| Test oracles | envytools ([envytools/envytools](https://github.com/envytools/envytools) commit `f102b823`): `envydis` (through the library, `test/slotdis.c`) and `envyas`, run as black boxes |
| Real code | nouveau's falcon firmware images from the Linux kernel (v6.12, `drivers/gpu/drm/nouveau/nvkm/.../fuc/*.h`, MIT), downloaded by pinned URL and SHA-256, not committed |

The upstream history is kept; every Ghidra-Rare change is a separate commit on top.

## Ghidra-Rare changes

1. **Decoding checked against envydis** for v0, v3, v4, v5 and v6 (every value of the first two
   bytes with four tails, 50,000 random words): 0 differences. Fixed on the way:
   - unused bits are checked as envydis checks them (byte 2 high nibble of two-register forms, byte
     1 high nibble of `ret`/`iret`/`exit`/`xdwait`/`xcwait`, bit 3 of the `mpop` family, byte 4 high
     nibble of the v5 3-operand immediate forms, the high bits of 16-bit bitfield immediates, the
     crypto command bits, predicate branches with byte 1 bit 7 set);
   - wrong decodings: `0xcc` is `div` (was `mod`), register `btgl` is subopcode 0xb (was 0xd), `ptlb`
     (was a second `vtlb`), `iords` (was `unkce`), `xdfence` (was `unk_f8_6`), `mpopadd` (two forms
     were named `mpopaddret`), the destination of `not`/`neg`/`mov`/`hswap` in the 0x39 forms, the
     24-bit `lbra`/`lcall` target (was sign-extended);
   - missing instructions: `st`/`ld` with `D[sp+rN*size]`, `adc`/`sbb` with 16-bit immediates,
     `hswap` (0x39), one-operand `mov`, `add sp, rN`, `sext`/`extr`/`extrs`/`iords` register forms,
     `trap`, `bra` with an absolute 8-bit target, the v0-v4 `iowr`/`iowrs` (0xd0/0xd1), `cxset`
     through the crypto command form, `movf` (v0);
   - envydis' spelling: `I[...]` I/O operands, `$flags` bit names (`p0`-`p7`, `c`, `o`, `s`, `z`,
     `ie0`..., in `setp`/`xbit`/`sleep`/`bset`/`bclr`/`btgl`), condition names `b`/`e`/`be`/`ae`/`ne`,
     special register names (`tv`, `xcbase`, `xdbase`, `cx`, `cauth`, `xtargets`, `tstatus`, `s2`,
     `s9`, `s10`, `s13`-`s15`, `cauth1`/`xcbase1`/`xdbase1` on v6), `cigfmul`;
   - F_FUC3P/F_FUC4P instructions limited to the versions that have them.
2. **Languages**: v0, v3 and v6 added (`falcon:LE:32:v0`, `v3`, `v6`); v5 and v6 include the crypto
   coprocessor; the shared spec moved to `base_falcon.sinc` so that the build compiles only the
   language files.
3. **Semantics** from the envytools documentation, checked by hand-computed emulator cases:
   - flags `c o s z` are bit ranges of `csw`, so every `csw` write (mov, setp, bset/bclr/btgl, iret)
     is visible to conditions (README todo items);
   - carry/borrow and overflow of `add`/`adc`/`sub`/`sbb`/`cmp`, `cmpu`/`cmps`; `adc`/`sbb`/`shlc`/
     `shrc` implemented (were `todo`); shift counts masked to the operation size and the carry from
     the last bit shifted out; 8/16-bit operations take truncated operands;
   - `pop`/`ret` read the stack before incrementing sp (they read the slot above); `iret`
     restores the interrupt enables; `mpush`/`mpop`/`mpopret`/`mpopadd`/`mpopaddret` push/pop r0..rN;
   - `mulu`/`muls` multiply the low 16 bits (register forms were `todo`); `extr` size (off by one in
     the 8-bit form), `extrs`, `ins` (was `todo`), `sext` flags and the `f0` form (was `todo`),
     `xbit`, `neg` overflow, `hswap` for every size, bit numbers modulo 32;
   - v0 rules: logic operations and `xbit` set no flags, shifts set only c;
   - `iord`/`iowr`/`iords`/`iowrs` access a volatile `io` address space instead of pcodeops.
4. **Loader** ported to the Ghidra 12 loader API (`NvidiaGRBootloaderLoader`), with a header sanity
   check.
5. **Ghidra-Rare notes, credits, tests** (`GHIDRA-RARE.md`, `CREDITS.md`, `test/`), README status
   of the upstream todo list, stand-alone `build.gradle`/`extension.properties`, `LICENSE.txt`
   renamed to `LICENSE`.
