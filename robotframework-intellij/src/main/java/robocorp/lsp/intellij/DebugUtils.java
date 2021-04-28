package robocorp.lsp.intellij;

import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

public class DebugUtils {

    /**
     * Helper to add a breakpoint with a condition such as:
     * <p>
     * robocorp.lsp.intellij.DebugUtils.debug(content)
     * <p>
     * So that it'd print the `content` to the output and proceed execution.
     * <p>
     * In the LSP/DAP context, it may be useful to add such a breakpoint in:
     * org.eclipse.lsp4j.jsonrpc.json.StreamMessageProducer
     * to see the actual messages being received.
     */
    public static boolean debug(Object s) {
        try {
            FileOutputStream f = new FileOutputStream("c:/temp/dap_out.txt", true);
            f.write(("" + s).getBytes(StandardCharsets.UTF_8));
            f.write("\n\n".getBytes(StandardCharsets.UTF_8));
            f.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }
}
