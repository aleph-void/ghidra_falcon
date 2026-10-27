// After an auto import: print the loader-visible result (language, blocks, entry function) so the
// test can check that the NVIDIA GR bootloader loader picked up a synthetic header.
// Script args: <outfile>
//@category Testing

import java.io.PrintStream;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.MemoryBlock;

public class LoaderCheck extends GhidraScript {
	@Override
	protected void run() throws Exception {
		PrintStream out = new PrintStream(getScriptArgs()[0]);
		out.println("language " + currentProgram.getLanguageID());
		for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
			out.println("block " + b.getName() + " " + b.getStart() + " " + b.getSize());
		}
		var f = getFunctionAt(toAddr(0x100));
		out.println("entry " + (f == null ? "none" : f.getName()));
		out.println("functions " + currentProgram.getFunctionManager().getFunctionCount());
		out.close();
	}
}
