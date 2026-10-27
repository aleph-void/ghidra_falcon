/* Disassemble the first instruction of every fixed-size slot of a raw file with envytools'
 * envydis library (MIT; used as a black-box reference disassembler).
 *   falcon-slotdis <variant fuc0|fuc3|fuc4|fuc5|fuc6> <slot> <file> [-F feature]... [-l list -b base]
 * Prints "<offset-hex> <len> <text>" per slot ("<offset> 0 (bad)" for unknown instructions). With
 * -l, <file> is an image loaded at <base> and one instruction is decoded at each listed address. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "dis.h"
#include "colors.h"
#include "var.h"

int main(int argc, char **argv) {
	if (argc < 4) { fprintf(stderr, "usage\n"); return 2; }
	const struct disisa *isa = ed_getisa("falcon");
	struct varinfo *var = varinfo_new(isa->vardata);
	if (varinfo_set_variant(var, argv[1])) return 2;
	int slot = atoi(argv[2]);
	const char *lst = NULL; unsigned long base = 0;
	for (int i = 4; i + 1 < argc; i += 2) {
		if (!strcmp(argv[i], "-F")) { if (varinfo_set_feature(var, argv[i + 1])) return 2; }
		else if (!strcmp(argv[i], "-l")) lst = argv[i + 1];
		else if (!strcmp(argv[i], "-b")) base = strtoul(argv[i + 1], NULL, 16);
	}
	FILE *f = fopen(argv[3], "rb"); fseek(f, 0, SEEK_END); long sz = ftell(f); rewind(f);
	unsigned char *data = malloc(sz + 16); memset(data, 0, sz + 16);
	if (fread(data, 1, sz, f) != (size_t)sz) return 2; fclose(f);
	FILE *lf = lst ? fopen(lst, "r") : NULL;
	char line[1024];
	char *buf = NULL; size_t blen = 0;
	for (long off = 0;; off += slot) {
		long n = slot;
		if (lf) {
			if (!fgets(line, sizeof line, lf)) break;
			off = (long)(strtoul(line, NULL, 16) - base);
			if (off < 0 || off >= sz) continue;
			n = sz - off < 16 ? sz - off : 16;
		} else if (off + slot > sz) break;
		FILE *m = open_memstream(&buf, &blen);
		envydis(isa, m, data + off, base + off, n, var, 0, NULL, 0, &envy_null_colors);
		fclose(m);
		/* "XXXXXXXX: b0 b1 ...    text" ; take the first instruction line (envydis puts a blank
		 * line before a branch/call target) */
		char *line0 = buf;
		while (*line0 == '\n') line0++;
		char *nl = strchr(line0, '\n'); if (nl) *nl = 0;
		char *p = strchr(line0, ':'); int len = 0;
		p = p ? p + 1 : line0;
		while (1) {
			while (*p == ' ') p++;
			if (isxdigit((unsigned char)p[0]) && isxdigit((unsigned char)p[1]) && (p[2] == ' ' || p[2] == 0)) { len++; p += 2; }
			else if (p[0] == '?' && p[1] == '?') { p += 2; }
			else break;
		}
		while (*p == ' ') p++;
		if (strstr(p, "[unknown") || strstr(p, "[incomplete]") || len == 0)
			printf("%08lx 0 (bad) %s\n", base + off, p);
		else
			printf("%08lx %d %s\n", base + off, len, p);
		free(buf); buf = NULL;
	}
	return 0;
}
