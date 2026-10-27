#!/usr/bin/env python3
"""Decode corpus for the Falcon differential: one instruction per 8-byte slot (the longest Falcon
instruction is 4 bytes; envydis needs the trailing bytes of an incomplete one).
  gen_corpus.py <out.bin> [random-slots] [seed]
Every value of the first two bytes with 4 tails (two random, all-zero, all-ones), then
<random-slots> fully random slots (default 50000)."""
import random
import sys

out = sys.argv[1]
nrand = int(sys.argv[2]) if len(sys.argv) > 2 else 50000
rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
with open(out, "wb") as f:
    n = 0
    for w in range(0x10000):
        for t in (bytes(6), b"\xff" * 6, rnd.randbytes(6), rnd.randbytes(6)):
            f.write(bytes([w & 0xff, w >> 8]) + t)
            n += 1
    for _ in range(nrand):
        f.write(rnd.randbytes(8))
        n += 1
print(f"{n} slots -> {out}")
