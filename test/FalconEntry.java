// Pre-analysis script for raw Falcon images: the code starts at address 0 (the reset entry).
// Marks it as an entry point and function so auto-analysis follows the code from there.
//@category Testing

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class FalconEntry extends GhidraScript {
	@Override
	protected void run() throws Exception {
		Address a = currentProgram.getMinAddress();
		currentProgram.getSymbolTable().addExternalEntryPoint(a);
		disassemble(a);
		createFunction(a, "entry");
	}
}
