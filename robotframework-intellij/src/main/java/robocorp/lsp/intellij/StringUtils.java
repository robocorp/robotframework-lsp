package robocorp.lsp.intellij;

import java.util.ArrayList;
import java.util.List;

public class StringUtils {

    /**
     * Splits some string given some char (that char will not appear in the returned strings)
     * Empty strings are also never added.
     */
    public static List<String> split(String string, char toSplit) {
        int len = string.length();
        if (len == 0) {
            return new ArrayList<>(0);
        }
        ArrayList<String> ret = new ArrayList<String>();

        int last = 0;

        char c = 0;

        for (int i = 0; i < len; i++) {
            c = string.charAt(i);
            if (c == toSplit) {
                if (last != i) {
                    ret.add(string.substring(last, i));
                }
                while (c == toSplit && i < len - 1) {
                    i++;
                    c = string.charAt(i);
                }
                last = i;
            }
        }
        if (c != toSplit) {
            if (last == 0 && len > 0) {
                ret.add(string); //it is equal to the original (no char to split)

            } else if (last < len) {
                ret.add(string.substring(last, len));

            }
        }
        return ret;
    }

    /**
     * Splits the passed string based on the toSplit string.
     * <p>
     * Corner-cases:
     * if the delimiter to do the split is empty an error is raised.
     * if the entry is an empty string, the return should be an empty array.
     */
    public static List<String> split(final String string, final String toSplit) {
        int len = string.length();
        if (len == 0) {
            return new ArrayList<>(0);
        }

        int length = toSplit.length();

        if (length == 1) {
            return split(string, toSplit.charAt(0));
        }
        ArrayList<String> ret = new ArrayList<String>();
        if (length == 0) {
            ret.add(string);
            return ret;
        }

        int last = 0;

        char c = 0;

        for (int i = 0; i < len; i++) {
            c = string.charAt(i);
            if (c == toSplit.charAt(0) && matches(string, toSplit, i)) {
                if (last != i) {
                    ret.add(string.substring(last, i));
                }
                last = i + toSplit.length();
                i += toSplit.length() - 1;
            }
        }

        if (last < len) {
            ret.add(string.substring(last, len));
        }

        return ret;
    }

    private static boolean matches(final String string, final String toSplit, int i) {
        int length = string.length();
        int toSplitLen = toSplit.length();
        if (length - i >= toSplitLen) {
            for (int j = 0; j < toSplitLen; j++) {
                if (string.charAt(i + j) != toSplit.charAt(j)) {
                    return false;
                }
            }
            return true;
        }
        return false;
    }
}
