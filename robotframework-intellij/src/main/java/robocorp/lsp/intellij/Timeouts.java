package robocorp.lsp.intellij;

public class Timeouts {
    // Initial values (after the first one succeeds, the timeout becomes lower).
    private static long definitionTimeout = 5;
    private static long hoverTimeout = 5;

    private static long symbolsTimeout = 8;
    private static long completionsTimeout = 8;

    public static long getDefinitionTimeout() {
        long ret = definitionTimeout;
        definitionTimeout = 2;
        return ret;
    }

    public static long getSymbolsTimeout() {
        long ret = symbolsTimeout;
        symbolsTimeout = 3;
        return ret;

    }

    public static long getCompletionTimeout() {
        long ret = completionsTimeout;
        completionsTimeout = 3;
        return ret;
    }

    public static long getHoverTimeout() {
        long ret = hoverTimeout;
        hoverTimeout = 3;
        return ret;
    }

    public static long getSemanticHighlightingTimeout() {
        return 3;
    }

    public static long getFoldingRangeTimeout() {
        return 3;
    }

    public static long getDocumentSymbolTimeout() {
        return 3;
    }
}
