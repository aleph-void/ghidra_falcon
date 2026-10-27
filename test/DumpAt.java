// Decode one instruction at each listed address of the current program (no disassembly is
// stored). Prints "<address-hex> <len> <text>" ("<address> 0 BAD" when the language rejects it).
// Script args: <address-list> <outfile>
//@category Testing

import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;

import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.InstructionPrototype;
import ghidra.program.model.lang.Language;
import ghidra.program.model.lang.ProcessorContextImpl;
import ghidra.program.model.lang.Register;
import ghidra.program.model.mem.DumbMemBufferImpl;
import ghidra.program.model.mem.MemBuffer;

public class DumpAt extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		PrintStream out = new PrintStream(args[1]);
		Language lang = currentProgram.getLanguage();
		ProcessorContextImpl ctx = new ProcessorContextImpl(lang);
		Register cr = lang.getContextBaseRegister();
		if (cr != null && cr != Register.NO_CONTEXT) {
			ctx.setRegisterValue(currentProgram.getProgramContext().getDefaultDisassemblyContext());
		}
		for (String line : Files.readAllLines(Path.of(args[0]))) {
			if (line.isBlank()) {
				continue;
			}
			long off = Long.parseLong(line.trim().split("\\s+")[0], 16);
			Address a = currentProgram.getMinAddress().getNewAddress(off);
			try {
				MemBuffer buf = new DumbMemBufferImpl(currentProgram.getMemory(), a);
				InstructionPrototype proto = lang.parse(buf, ctx, false);
				PseudoInstruction pi = new PseudoInstruction(currentProgram, a, proto, buf, ctx);
				out.printf("%08x %d %s%n", off, pi.getLength(), pi.toString());
			}
			catch (Exception e) {
				out.printf("%08x 0 BAD%n", off);
			}
		}
		out.close();
	}
}
