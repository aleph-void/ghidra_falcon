#!/usr/bin/env python3
"""Compare Ghidra's slot decode (DumpSlots.java) with envydis's (slotdis.c), or a real-code
listing pairing (realcmp.py uses classify()/report()).
  compare.py <ghidra.txt> <envydis.txt> [--show N]
Exact: same length and same text after the syntax mapping in norm() (envydis' "$r0" and blank
separators vs Ghidra's "r0" and commas, "add b8" vs "add_b8"). Semantic: same after numbers are
canonicalised. Differences are bucketed; buckets in EXPLAINED are explained, others make the
script exit 1."""
import collections
import re
import sys

NUM = re.compile(r"(?<![\w.])([-+]?)(0x[0-9a-fA-F]+|\d+)(?![\w])")


# envydis calls the csw special register $flags
SREG = {"flags": "csw"}


def syntax(t):
    # envydis marks branch/call targets with a leading "B"/"C" label tag
    t = re.sub(r"^[A-Z] ", "", t.strip())
    t = t.lower().replace("$", "").replace(",", " ")
    t = re.sub(r"\b(" + "|".join(SREG) + r")\b", lambda m: SREG[m.group(1)], t)
    # memory operands: "D[r0 + 0x0]" and "D[r0]" are the same address
    t = re.sub(r"\[\s*([^\]]*?)\s*\]", lambda m: "[" + re.sub(r"\s+", "", m.group(1)) + "]", t)
    t = re.sub(r"\+0x0\]", "]", t)
    t = re.sub(r"\*(1|0x1)\]", "]", t)
    t = re.sub(r"^(\S+)_(b8|b16|b32)\b", r"\1 \2", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def num(m):
    v = int(m.group(2), 0)
    if v > 0xffffffff:
        v &= 0xffffffff   # envydis prints 64-bit wrapped branch targets
    if m.group(1) == "-":
        v = -v
    return ("-" if v < 0 else "") + hex(abs(v))


def norm(t):
    t = syntax(t)
    t = NUM.sub(num, t)
    return t


def mn(t):
    return syntax(t).split(" ")[0] if t else ""


# (bucket regex, explanation); see GHIDRA-RARE.md
EXPLAINED = [
    (r"^image end:", "the last instruction address of a linear sweep lies within the final bytes of the "
     "image: envydis reports [incomplete], Ghidra's decoder reads zero bytes past the end"),
]


def classify(gt, et, gl, el):
    gbad = gl == 0 or gt == "BAD"
    ebad = el == 0
    if gbad and ebad:
        return "both-invalid"
    if "[incomplete]" in et:
        return "image end: envydis has too few bytes left ([incomplete])"
    if not gbad and not ebad and gl == el and syntax(gt) == syntax(et):
        return "exact"
    if not gbad and not ebad and gl == el and norm(gt) == norm(et):
        return "semantic"
    if gbad:
        return "ghidra BAD, envydis %s" % mn(et)
    if ebad:
        return "envydis invalid, ghidra %s" % mn(gt)
    if gl != el:
        return "%s/%s length %d/%d" % (mn(gt), mn(et), gl, el)
    return "%s/%s" % (mn(gt), mn(et))


def explain(key):
    return next((why for pat, why in EXPLAINED if re.search(pat, key)), None)


def report(pairs, show=3, out=sys.stdout):
    counts = collections.Counter()
    buckets = collections.Counter()
    examples = collections.defaultdict(list)
    for label, (gl, gt), (el, et) in pairs:
        k = classify(gt, et, gl, el)
        if k in ("exact", "semantic", "both-invalid"):
            counts[k] += 1
            continue
        buckets[k] += 1
        if len(examples[k]) < show:
            examples[k].append("%s | %s | %s" % (label, gt, et))
    total = sum(counts.values()) + sum(buckets.values())
    print("%d: exact %d, semantic %d, both invalid %d, differences %d" % (
        total, counts["exact"], counts["semantic"], counts["both-invalid"], sum(buckets.values())), file=out)
    unexplained = 0
    for k, n in sorted(buckets.items(), key=lambda kv: -kv[1]):
        tag = explain(k)
        if tag is None:
            unexplained += n
        print(f"  {n:7d} {'explained: ' + tag if tag else 'UNEXPLAINED'}  [{k}]", file=out)
        for e in examples[k]:
            print("          " + e, file=out)
    print(f"unexplained differences: {unexplained}", file=out)
    return unexplained


def load(path):
    out = []
    for line in open(path):
        f = line.rstrip("\n").split(" ", 2)
        out.append((f[0], int(f[1]), f[2] if len(f) > 2 else ""))
    return out


def main():
    args = sys.argv[1:]
    show = 3
    if "--show" in args:
        i = args.index("--show"); show = int(args[i + 1]); del args[i:i + 2]
    gh, en = load(args[0]), load(args[1])
    assert len(gh) == len(en)
    data = open(args[2], "rb").read() if len(args) > 2 else None
    pairs = []
    for (a, gl, gt), (_, el, et) in zip(gh, en):
        lab = a + (" " + data[int(a, 16):int(a, 16) + 6].hex(" ") if data else "")
        pairs.append((lab, (gl, gt), (el, et)))
    print("slots ", end="")
    sys.exit(1 if report(pairs, show) else 0)


if __name__ == "__main__":
    main()
