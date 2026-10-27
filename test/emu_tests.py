#!/usr/bin/env python3
"""Hand-computed p-code cases for EmuCheck.java (falcon v5 language, with the crypto coprocessor).
Each case is a short sequence assembled once with envytools' envyas (MIT; `--rebuild`), placed at
0x100 * index in IMEM; test/emu/cases.txt keeps the bytes so the suite needs no assembler.
Expected values are worked out by hand from the envytools Falcon ISA documentation
(docs/hw/falcon/arith.rst, data.rst, branch.rst): csw bits 8-11 are c, o, s, z (0x100 ... 0x800).
  emu_tests.py <outdir>            -> <outdir>/emu.bin, <outdir>/tests.txt
  emu_tests.py --rebuild <envyas>  -> regenerate test/emu/cases.txt"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_FILE = os.path.join(HERE, "emu", "cases.txt")

# name, assembly ({BASE} = address of the case), init, expect
CASES = [
    ("add_imm", "mov $r1 0x5\nadd b32 $r1 $r1 0x7", "-", "r1=c,csw=0"),
    ("add_overflow", "add b32 $r1 0x1", "r1=7fffffff", "r1=80000000,csw=600"),      # o, s
    ("add_carry_zero", "add b32 $r1 0x1", "r1=ffffffff", "r1=0,csw=900"),           # c, z
    ("sub_borrow", "sub b32 $r1 0x1", "r1=0", "r1=ffffffff,csw=500"),               # c (borrow), s
    ("adc_carry_in", "adc b32 $r1 0x1", "r1=1,csw=100", "r1=3,csw=0"),
    ("sbb_borrow_in", "sbb b32 $r1 0x2", "r1=5,csw=100", "r1=2,csw=0"),
    ("add_b8_keeps_high", "add b8 $r1 0x1", "r1=123456ff", "r1=12345600,csw=900"),
    ("add_b16_overflow", "add b16 $r1 0x1", "r1=aaaa7fff", "r1=aaaa8000,csw=600"),
    ("shl_carry_out", "shl b32 $r1 0x1", "r1=80000001", "r1=2,csw=100"),
    ("shr_carry_out", "shr b32 $r1 0x1", "r1=3", "r1=1,csw=100"),
    ("sar_sign", "sar b32 $r1 0x4", "r1=80000000", "r1=f8000000,csw=400"),
    ("shl_b8_count_mod8", "shl b8 $r1 0x9", "r1=1", "r1=2,csw=0"),
    ("shlc_carry_in", "shlc b32 $r1 0x1", "r1=0,csw=100", "r1=1,csw=0"),
    ("neg", "neg b32 $r2 $r2", "r2=1", "r2=ffffffff,csw=400"),
    ("not_b32", "not b32 $r1", "r1=f0f0f0f0", "r1=f0f0f0f,csw=0"),
    ("cmp_less", "cmp b32 $r1 $r2", "r1=1,r2=2", "csw=500"),
    ("cmpu_equal", "cmpu b32 $r1 $r2", "r1=5,r2=5", "csw=800"),
    ("cmps_signed_less", "cmps b32 $r1 $r2", "r1=ffffffff,r2=1", "csw=100"),
    ("mulu_16x16", "mulu $r1 $r2", "r1=10003,r2=20004", "r1=c"),
    ("muls_16x16", "muls $r1 $r2", "r1=ffff,r2=2", "r1=fffffffe"),
    ("and_flags", "and $r1 $r2", "r1=f0,r2=f,csw=f00", "r1=0,csw=800"),
    ("xor_3op", "xor $r1 $r2 $r3", "r2=ff,r3=f", "r1=f0,csw=0"),
    ("extr", "extr $r1 $r2 0x4:0x7", "r2=abcd", "r1=c"),                            # bits 4-7
    ("extrs", "extrs $r1 $r2 0x4:0x7", "r2=abcd", "r1=fffffffc,csw=400"),           # sign = bit 7
    ("ins", "ins $r1 $r2 0x8:0xb", "r1=ffffffff,r2=5", "r1=fffff5ff"),
    ("sext_bit7", "sext $r1 0x7", "r1=180", "r1=ffffff80,csw=400"),
    ("xbit", "xbit $r1 $r2 0x3", "r2=8", "r1=1,csw=0"),
    ("bset_bclr", "bset $r1 0x3\nbclr $r2 0x0", "r1=0,r2=ff", "r1=8,r2=fe"),
    ("push_pop", "push $r1\npop $r2", "r1=deadbeef,sp=800", "r2=deadbeef,sp=800"),
    ("call_ret", "call {T}\nmov $r1 0x9\nbra #end\nmov $r0 0x7\nret\nend:", "sp=800", "r0=7,r1=9,sp=800"),
    ("bra_e_taken", "cmp b32 $r1 $r2\nbra e #x\nmov $r3 0x1\nx:", "r1=4,r2=4", "r3=0"),
    ("bra_ne_not_taken", "cmp b32 $r1 $r2\nbra ne #x\nmov $r3 0x1\nx:", "r1=4,r2=4", "r3=1"),
    ("st_ld_offset", "st b32 D[$r2+0x4] $r1\nld b32 $r3 D[$r2+0x4]", "r1=12345678,r2=100", "r3=12345678"),
    ("st_ld_b8_b16", "st b16 D[$r2+0x2] $r1\nld b8 $r3 D[$r2+0x3]", "r1=abcd,r2=100", "r3=ab"),
    ("mpush_mpop", "mpush $r2\nmov $r0 0x0\nmov $r1 0x0\nmov $r2 0x0\nmpop $r2",
     "r0=10,r1=11,r2=12,sp=800", "r0=10,r1=11,r2=12,sp=800"),
    ("hswap_b32", "hswap b32 $r1", "r1=12345678", "r1=56781234,csw=0"),
    ("setp_bra_p3", "setp $p3 $r1\nbra $p3 #x\nmov $r3 0x1\nx:", "r1=1", "r3=0,csw=8"),
    ("div_mod", "div $r3 $r1 $r2\nmod $r4 $r1 $r2", "r1=11,r2=5", "r3=3,r4=2"),
    ("mov_imm_signed", "mov $r1 -0x1", "-", "r1=ffffffff"),
    ("io_write_read", "iowr I[$r2+0x4] $r1\niord $r3 I[$r2+0x4]", "r1=cafe,r2=100", "r3=cafe"),
    ("mov_b16_keeps_high", "mov b16 $r1 $r2", "r1=aaaaaaaa,r2=12345678", "r1=aaaa5678"),
    # deliberately wrong expectation: must be reported
    ("broken_add_imm", "mov $r1 0x5\nadd b32 $r1 $r1 0x7", "-", "r1=d"),
]


# Falcon v0 differences (arith.rst): logic operations and xbit set no flags, shifts set only c,
# xbit changes only bit 0 of the destination, movf moves and sets s/z (o = 0)
CASES_V0 = [
    ("v0_and_no_flags", "and $r1 $r2", "r1=f0,r2=f,csw=f00", "r1=0,csw=f00"),
    ("v0_shl_c_only", "shl b32 $r1 0x1", "r1=80000000,csw=c00", "r1=0,csw=d00"),
    ("v0_xbit_bit0", "xbit $r1 $r2 0x3", "r1=fffffff0,r2=8", "r1=fffffff1,csw=0"),
    ("v0_movf", "movf b32 $r1 $r2", "r2=80000000,csw=200", "r1=80000000,csw=400"),
    ("v0_add_flags", "add b32 $r1 0x1", "r1=7fffffff", "r1=80000000,csw=600"),
    ("broken_v0_movf", "movf b32 $r1 $r2", "r2=80000000", "r1=0"),
]


def rebuild(envyas):
    rebuild_set(envyas, CASES, "fuc5", ["-F", "crypt"], CASES_FILE)
    rebuild_set(envyas, CASES_V0, "fuc0", [], CASES_FILE.replace("cases.txt", "cases_v0.txt"))


def rebuild_set(envyas, cases, variant, feats, path):
    rows = []
    for i, (name, asm, _, _) in enumerate(cases):
        base = 0x100 * (i + 1)
        # call_ret: the subroutine sits after "call (3) + mov (2) + bra (3)"
        asm = asm.replace("{T}", hex(base + 8))
        with tempfile.NamedTemporaryFile("w", suffix=".s", delete=False) as f:
            f.write(asm + "\n")
        out = subprocess.run([envyas, "-m", "falcon", "-V", variant] + feats + [f.name],
                             capture_output=True, text=True, check=True).stdout
        os.unlink(f.name)
        code = bytes(int(x, 16) for x in out.replace("\n", "").split(",") if x.strip())
        rows.append("%s %s" % (name, code.hex()))
    open(path, "w").write("\n".join(rows) + "\n")


if sys.argv[1] == "--rebuild":
    rebuild(sys.argv[2])
    sys.exit(0)


def emit(cases, path, out, suffix):
    code = dict(l.split() for l in open(path))
    img = bytearray(0x100 * (len(cases) + 2))
    with open(os.path.join(out, "tests%s.txt" % suffix), "w") as f:
        for i, (name, _, init, exp) in enumerate(cases):
            base = 0x100 * (i + 1)
            b = bytes.fromhex(code[name])
            img[base:base + len(b)] = b
            f.write("%s %x %x %s %s\n" % (name, base, base + len(b), init, exp))
    open(os.path.join(out, "emu%s.bin" % suffix), "wb").write(img)


out = sys.argv[1]
os.makedirs(out, exist_ok=True)
emit(CASES, CASES_FILE, out, "")
emit(CASES_V0, CASES_FILE.replace("cases.txt", "cases_v0.txt"), out, "_v0")
print("%d cases (v3-v6), %d cases (v0)" % (len(CASES), len(CASES_V0)))
