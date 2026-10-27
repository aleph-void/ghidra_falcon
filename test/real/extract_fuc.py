#!/usr/bin/env python3
"""Extract the IMEM code array of a nouveau falcon firmware header (envyas output, e.g.
nvkm/subdev/pmu/fuc/gt215.fuc3.h) into a raw little-endian image.
  extract_fuc.py <header.h> <out.bin>"""
import re
import struct
import sys

src = open(sys.argv[1]).read()
m = re.search(r"static uint32_t \w+_code\[\] = \{(.*?)\};", src, re.S)
words = [int(w, 16) for w in re.findall(r"0x[0-9a-fA-F]+", re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S))]
open(sys.argv[2], "wb").write(struct.pack("<%dI" % len(words), *words))
print("%s: %d bytes" % (sys.argv[2], 4 * len(words)))
