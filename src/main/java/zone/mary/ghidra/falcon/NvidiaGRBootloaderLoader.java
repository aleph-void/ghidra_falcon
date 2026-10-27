package zone.mary.ghidra.falcon;

import java.io.IOException;
import java.util.*;

import ghidra.app.util.bin.BinaryReader;
import ghidra.app.util.bin.ByteProvider;
import ghidra.app.util.opinion.AbstractProgramWrapperLoader;
import ghidra.app.util.opinion.LoadSpec;
import ghidra.app.util.opinion.LoaderTier;
import ghidra.program.flatapi.FlatProgramAPI;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.CompilerSpecID;
import ghidra.program.model.lang.LanguageCompilerSpecPair;
import ghidra.program.model.lang.LanguageID;
import ghidra.program.model.listing.Program;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.util.exception.CancelledException;

/**
 * Loader for NVIDIA GR falcon bootloader images: a 16-byte header (start offset, size, IMEM load
 * address, entry point) followed by the code. Ported to the Ghidra 12 loader API by Ghidra-Rare.
 */
public class NvidiaGRBootloaderLoader extends AbstractProgramWrapperLoader {
	private static final LanguageID FALCON4_LANGUAGE_ID = new LanguageID("falcon:LE:32:v4");
	private static final LanguageID FALCON5_LANGUAGE_ID = new LanguageID("falcon:LE:32:v5");

	@Override
	public String getName() {
		return "NVIDIA GR BootLoader";
	}

	@Override
	public Collection<LoadSpec> findSupportedLoadSpecs(ByteProvider provider) throws IOException {
		List<LoadSpec> loadSpecs = new ArrayList<>();
		if (provider.length() < 0x14) {
			return loadSpecs;
		}
		BinaryReader reader = new BinaryReader(provider, true);
		long startOffset = reader.readUnsignedInt(0x0);
		long size = reader.readUnsignedInt(0x4);
		// the header must describe a non-empty, word-sized code image inside the file
		if (size == 0 || (size & 3) != 0 || startOffset + 0x10 + size > provider.length()) {
			return loadSpecs;
		}
		loadSpecs.add(new LoadSpec(this, 0,
			new LanguageCompilerSpecPair(FALCON4_LANGUAGE_ID, new CompilerSpecID("default")), true));
		loadSpecs.add(new LoadSpec(this, 0,
			new LanguageCompilerSpecPair(FALCON5_LANGUAGE_ID, new CompilerSpecID("default")), true));
		return loadSpecs;
	}

	@Override
	public LoaderTier getTier() {
		return LoaderTier.SPECIALIZED_TARGET_LOADER;
	}

	@Override
	public int getTierPriority() {
		return 100;
	}

	@Override
	protected void load(Program program, ImporterSettings settings)
			throws CancelledException, IOException {
		ByteProvider provider = settings.provider();
		BinaryReader reader = new BinaryReader(provider, true);
		FlatProgramAPI api = new FlatProgramAPI(program);

		long startOffset = reader.readUnsignedInt(0x0);
		long size = reader.readUnsignedInt(0x4);
		long instructionMemoryOffset = reader.readUnsignedInt(0x8);
		long entrypointOffset = reader.readUnsignedInt(0xC);

		Address instructionMemoryAddress = api.toAddr(instructionMemoryOffset);
		Address entrypointAddress = api.toAddr(entrypointOffset);
		byte[] data = provider.readBytes(startOffset + 0x10, size);
		try {
			MemoryBlock block =
				api.createMemoryBlock("bootloader", instructionMemoryAddress, data, false);
			block.setPermissions(true, false, true);
		}
		catch (Exception e) {
			throw new IOException("Failed to load image: " + e.getMessage(), e);
		}
		api.addEntryPoint(entrypointAddress);
		api.disassemble(entrypointAddress);
		api.createFunction(entrypointAddress, "_bootloader_entrypoint");
	}
}
