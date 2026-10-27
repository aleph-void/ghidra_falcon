# Nvidia Falcon plugin for Ghidra

This is pretty immature, so you'll probably need to do some development to use it, but it's likely good enough to save a bit of time over an `envydis` dead-listing.

> **Ghidra-Rare fork.** This fork has been tested against envydis and fixed: decoding of every
> language matches envydis on every two-byte prefix and random words, the semantics are checked in
> Ghidra's emulator, and nouveau's falcon firmware is used as real code. See
> [GHIDRA-RARE.md](GHIDRA-RARE.md) for the results and remaining gaps, and
> [CREDITS.md](CREDITS.md) for the list of changes. Prebuilt zips for Ghidra 12.1.3, 12.1.4 and
> 12.2 are on this fork's Releases page. Languages: `falcon:LE:32:v0`, `v3`, `v4`, `v5` and `v6`
> (v5/v6 with the crypto coprocessor).

![Screenshot](/images/screenshot1.png)

## Setup instructions

- Ensure you have the ``JAVA_HOME`` environment variable set to the JDK your Ghidra uses (JDK 21 for Ghidra 12.1, JDK 25 for 12.2).
- Set the ``GHIDRA_INSTALL_DIR`` environment variable to your Ghidra install directory.
- Run ``gradle buildExtension`` (or download a prebuilt zip from the Releases page).
- You'll find the output zip file inside ``/dist``.
- Copy the output zip to ``<Ghidra install directory>/Extensions/Ghidra``
- Start Ghidra and use the "Install Extensions" dialog to finish the installation. (``File -> Install Extensions...``)

## Development

This is just how I do it:

Open up the [envytools Falcon ISA documentation](https://envytools.readthedocs.io/en/latest/hw/falcon/isa.html) to compare the semantic information with the reference pseudocode. Open Ghidra's `doc/languages/index.html` for a reference for how the Sleigh language works.

Load your test binary in Ghidra.

Use [envydis](https://github.com/envytools/envytools) on the binary you're looking at so you can quickly check the disassembly for errors if anything seems off.

In Ghidra enable PCode display by clicking the "Edit the Listing fields" icon at the top of the Listing view, right clicking "PCode" and clicking "Enable Field" (you may wish to toggle this on-and-off during reversing as it is quite verbose).

In Ghidra open the script manager ("Window" -> "Script Manager") and add key-bindings for `DebugSleighInstructionParse.java` and `ReloadSleighLangauge.java`.

`DebugSleighInstructionParse.java` will log detailed debug information about the instruciton parse for the byte under the cursor. I usually use it to find the `{line# 756} ld_b32 <reg2>, D[<reg1>]` so I know what line to go to to fix the PCode output.

`ReloadSleighLangauge.java` will reload most changes to the slaspec, including new instructions and new semantic definitions. However, if you add new registers or new `define pcodeop ...` statements, you will need to restart Ghidra to get correct output.

### Adding instructions to the decompiler

At the moment any particularly poorly implemented instruction should show up as a call to the `todo` pcodeop in the decompiler output - this is a hint that the instruction should be implemented for correct decompilation. Get the line number using `DebugSleighInstructionParse.java` on the corresponding instruction, and add the implementation to the slaspec/sinc file.

See Ghidra's `doc/languages/index.html` for more information about how to describe instructions.

Run `ReloadSleighLangauge.java`, or, if you've added a new pcodeop for the instruction, close and re-open Ghidra to see the new output.


### Adding instructions to the disassembler

If you hit undecodable instruction bytes, find the correct decoding in your `envydis` output, then search through the `envydis.sinc` file for the envydis source comment that matches. For example:

```
#	{ 0x0004003c, 0x000f003f, OP3B, N("shl"), T(sz), REG3, REG1, REG2 },
```

Try to find an implemented instruction using the same encoding/operands, for example:

```
#	{ 0x0002003c, 0x000f003f, OP3B, N("sub"), T(sz), REG3, REG1, REG2 },
:sub_b32 reg3, reg1, reg2 is op_format=0x3c & op_size=2; reg2 & reg1; subopcode3=0x2 & reg3 {
  sub(reg3, reg1, reg2);
}
```

Copy-paste and change the opcode/subopcode, mnemonic, and implementation:

```
:shl_b32 reg3, reg1, reg2 is op_format=0x3c & op_size=2; reg2 & reg1; subopcode3=0x4 & reg3 {
  todo();
}
```

Reload (with your `ReloadSleighLangauge.java` hotkey), disassemble the bytes (by pressing `D`), and check the output is correct. If it fails to disassemble, double check your code, or use `DebugSleighInstructionParse.java` to see where it goes wrong.

If you hit errors reloading, you can view the log by clicking the "Show Console" icon at the bottom Ghidra project window (the one with the file listing, not the CodeBrowser/disassembly window). The errors are only helpful some of the time, so I usually check my changes by hand first to see if I can spot what I did wrong.

### Syntax highlighting

If you like syntax highlighting, Sleigh often looks okay highlighted as a bash script. I got tired of this and wrote a very basic sublime-syntax, which can be found at: https://github.com/hthh/sleigh-sublime-syntax

## To-Do

~~Finish adding instructions and figure out how to do thorough automated testing.~~ Done in the
Ghidra-Rare fork: `test/run-tests.sh` compares every two-byte prefix and 50,000 random words with
envydis for each language, reaches every SLEIGH constructor and runs hand-computed emulator cases
(see GHIDRA-RARE.md).

Known issues/todo-list (status in the Ghidra-Rare fork):

* ~~add other falcon variants~~ fixed: v0, v3 and v6 added beside v4 and v5 (envytools knows no separate v1/v2 ISA)
* ~~fix mpop/mpush (and variants) to read/write all values~~ fixed: they push/pop r0..rN
* ~~rename "ram" to "iram" and document adding a "dram" section for globals~~ fixed earlier: the spaces are `imem` and `dmem`
* ~~try making "io" a real address space?~~ fixed: `iord`/`iowr` access an `io` address space (volatile)
* ~~see if there's a way to make crypto stuff decompile as `csecret(c1, 0x2)` instead of `csecret(1, 2)`~~ fixed earlier: crypto operations take the `c` registers
* global stores can be reordered to come after pcodeop calls that implicitly read from them: remaining, a decompiler property (a pcodeop does not declare the memory it reads); fewer pcodeops remain now (I/O is plain memory)
* can we bundle types? remaining: I/O register names differ per falcon unit (PMU, GR, SEC, ...), so no single list fits the processor module
* ~~finish adding packflags and unpackflags anywhere the flags register is used directly~~ fixed: the flags are bit ranges of `csw`, no packing needed
* ~~make the flags register actually show up when not just used for condition codes~~ fixed (same change)
* update readme screenshot sometime: not a code issue

## Resources

* https://envytools.readthedocs.io/en/latest/hw/falcon/index.html - thorough hardware documentation
* https://switchbrew.org/wiki/TSEC - crypt functionality
* http://0x04.net/~mwk/Falcon.html - calling convention
