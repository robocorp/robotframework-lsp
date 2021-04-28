package robocorp.dap;

import com.intellij.openapi.util.SystemInfo;
import robocorp.lsp.intellij.FastStringBuffer;

import java.util.ArrayList;
import java.util.List;

/**
 * Helper for parsing command line back and forth.
 */
public class ProcessUtils {

    /**
     * copied from org.eclipse.jdt.internal.launching.StandardVMRunner
     *
     * @param args - other arguments to be added to the command line (may be null)
     * @return
     */
    public static String getArgumentsAsStr(String[] commandLine, String... args) {
        if (args != null && args.length > 0) {
            String[] newCommandLine = new String[commandLine.length + args.length];
            System.arraycopy(commandLine, 0, newCommandLine, 0, commandLine.length);
            System.arraycopy(args, 0, newCommandLine, commandLine.length, args.length);
            commandLine = newCommandLine;
        }

        if (commandLine.length < 1) {
            return ""; //$NON-NLS-1$
        }
        FastStringBuffer buf = new FastStringBuffer();
        FastStringBuffer command = new FastStringBuffer();
        for (int i = 0; i < commandLine.length; i++) {
            if (commandLine[i] == null) {
                continue; //ignore nulls (changed from original code)
            }

            buf.append(' ');
            char[] characters = commandLine[i].toCharArray();
            command.clear();
            boolean containsSpace = false;
            for (int j = 0; j < characters.length; j++) {
                char character = characters[j];
                if (character == '\"') {
                    command.append('\\');
                } else if (character == ' ') {
                    containsSpace = true;
                }
                command.append(character);
            }
            if (containsSpace) {
                buf.append('\"');
                buf.append(command.toString());
                buf.append('\"');
            } else {
                buf.append(command.toString());
            }
        }
        return buf.toString();
    }

    /**
     * Parses the given command line into separate arguments that can be passed to
     * <code>DebugPlugin.exec(String[], File)</code>. Embedded quotes and slashes
     * are escaped.
     * <p>
     * Parses the argument text into an array of individual
     * strings using the space character as the delimiter.
     * An individual argument containing spaces must have a
     * double quote (") at the start and end. Two double
     * quotes together is taken to mean an embedded double
     * quote in the argument text.
     *
     * @param args command line arguments as a single string
     * @return individual arguments
     * @since 3.1
     * <p>
     * Gotten from org.eclipse.debug.core.DebugPlugin
     */
    public static String[] parseArguments(String args) {
        if (args == null || args.length() == 0) {
            return new String[0];
        }

        if (SystemInfo.isWindows) {
            return parseArgumentsWindows(args);
        }

        return parseArgumentsImpl(args);
    }

    /**
     * Gotten from org.eclipse.debug.core.DebugPlugin
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    private static String[] parseArgumentsImpl(String args) {
        // man sh, see topic QUOTING
        List result = new ArrayList();

        final int DEFAULT = 0;
        final int ARG = 1;
        final int IN_DOUBLE_QUOTE = 2;
        final int IN_SINGLE_QUOTE = 3;

        int state = DEFAULT;
        StringBuffer buf = new StringBuffer();
        int len = args.length();
        for (int i = 0; i < len; i++) {
            char ch = args.charAt(i);
            if (Character.isWhitespace(ch)) {
                if (state == DEFAULT) {
                    // skip
                    continue;
                } else if (state == ARG) {
                    state = DEFAULT;
                    result.add(buf.toString());
                    buf.setLength(0);
                    continue;
                }
            }
            switch (state) {
                case DEFAULT:
                case ARG:
                    if (ch == '"') {
                        state = IN_DOUBLE_QUOTE;
                    } else if (ch == '\'') {
                        state = IN_SINGLE_QUOTE;
                    } else if (ch == '\\' && i + 1 < len) {
                        state = ARG;
                        ch = args.charAt(++i);
                        buf.append(ch);
                    } else {
                        state = ARG;
                        buf.append(ch);
                    }
                    break;

                case IN_DOUBLE_QUOTE:
                    if (ch == '"') {
                        state = ARG;
                    } else if (ch == '\\' && i + 1 < len &&
                            (args.charAt(i + 1) == '\\' || args.charAt(i + 1) == '"')) {
                        ch = args.charAt(++i);
                        buf.append(ch);
                    } else {
                        buf.append(ch);
                    }
                    break;

                case IN_SINGLE_QUOTE:
                    if (ch == '\'') {
                        state = ARG;
                    } else {
                        buf.append(ch);
                    }
                    break;

                default:
                    throw new IllegalStateException();
            }
        }
        if (buf.length() > 0 || state != DEFAULT) {
            result.add(buf.toString());
        }

        return (String[]) result.toArray(new String[result.size()]);
    }

    /**
     * Gotten from org.eclipse.debug.core.DebugPlugin
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    private static String[] parseArgumentsWindows(String args) {
        // see http://msdn.microsoft.com/en-us/library/a1y7w461.aspx
        List result = new ArrayList();

        final int DEFAULT = 0;
        final int ARG = 1;
        final int IN_DOUBLE_QUOTE = 2;

        int state = DEFAULT;
        int backslashes = 0;
        StringBuffer buf = new StringBuffer();
        int len = args.length();
        for (int i = 0; i < len; i++) {
            char ch = args.charAt(i);
            if (ch == '\\') {
                backslashes++;
                continue;
            } else if (backslashes != 0) {
                if (ch == '"') {
                    for (; backslashes >= 2; backslashes -= 2) {
                        buf.append('\\');
                    }
                    if (backslashes == 1) {
                        if (state == DEFAULT) {
                            state = ARG;
                        }
                        buf.append('"');
                        backslashes = 0;
                        continue;
                    } // else fall through to switch
                } else {
                    // false alarm, treat passed backslashes literally...
                    if (state == DEFAULT) {
                        state = ARG;
                    }
                    for (; backslashes > 0; backslashes--) {
                        buf.append('\\');
                    }
                    // fall through to switch
                }
            }
            if (Character.isWhitespace(ch)) {
                if (state == DEFAULT) {
                    // skip
                    continue;
                } else if (state == ARG) {
                    state = DEFAULT;
                    result.add(buf.toString());
                    buf.setLength(0);
                    continue;
                }
            }
            switch (state) {
                case DEFAULT:
                case ARG:
                    if (ch == '"') {
                        state = IN_DOUBLE_QUOTE;
                    } else {
                        state = ARG;
                        buf.append(ch);
                    }
                    break;

                case IN_DOUBLE_QUOTE:
                    if (ch == '"') {
                        if (i + 1 < len && args.charAt(i + 1) == '"') {
                            /* Undocumented feature in Windows:
                             * Two consecutive double quotes inside a double-quoted argument are interpreted as
                             * a single double quote.
                             */
                            buf.append('"');
                            i++;
                        } else if (buf.length() == 0) {
                            // empty string on Windows platform. Account for bug in constructor of JDK's java.lang.ProcessImpl.
                            result.add("\"\""); //$NON-NLS-1$
                            state = DEFAULT;
                        } else {
                            state = ARG;
                        }
                    } else {
                        buf.append(ch);
                    }
                    break;

                default:
                    throw new IllegalStateException();
            }
        }
        if (buf.length() > 0 || state != DEFAULT) {
            result.add(buf.toString());
        }

        return (String[]) result.toArray(new String[result.size()]);
    }

}
