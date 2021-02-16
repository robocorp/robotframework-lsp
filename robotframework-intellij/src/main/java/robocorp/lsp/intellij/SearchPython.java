package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.util.SystemInfo;
import org.jetbrains.annotations.Nullable;

import java.io.File;
import java.io.IOException;
import java.nio.file.LinkOption;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

public class SearchPython {

    private static final Logger LOG = Logger.getInstance(SearchPython.class);

    public static Set<String> getPathsToSearchPython() {
        Set<String> pathsToSearch = new LinkedHashSet<String>();
        try {
            String pythonHome = System.getenv("PYTHON_HOME");
            if (pythonHome != null) {
                pathsToSearch.add(pythonHome);
            }
            pythonHome = System.getenv("PYTHONHOME");
            if (pythonHome != null) {
                pathsToSearch.add(pythonHome);
            }
            String path = System.getenv("PATH");
            if (path != null) {
                final List<String> split = StringUtils.split(path, File.pathSeparator);
                pathsToSearch.addAll(split);
            }
        } catch (Exception e) {
            LOG.error(e);
        }
        if (!SystemInfo.isWindows) {
            // Paths to search on linux/mac
            pathsToSearch.add("/usr/bin");
            pathsToSearch.add("/usr/local/bin");
        }
        if (SystemInfo.isMac) {
            // Path to search on mac
            pathsToSearch.add("/Library/Frameworks/Python.framework/Versions/Current/bin");
        }
        return pathsToSearch;
    }

    private static final int INVALID = -1;

    private static int matchesPattern(Pattern[] patterns, File afile) {
        // Add other conditions here if stricter file validation is necessary.
        for (int i = 0; i < patterns.length; i++) {
            Pattern pattern = patterns[i];
            if (pattern.matcher(afile.getName().toLowerCase()).matches()) {
                return i;
            }
        }
        return INVALID;
    }

    public static String getFileAbsolutePath(File f) {
        try {
            if (!SystemInfo.isWindows) {
                // We don't want to follow links on Linux.
                return f.toPath().toRealPath(LinkOption.NOFOLLOW_LINKS).toString();
            } else {
                // On Windows, this is needed to get the proper case of files (because it's case-preserving
                // and we have to get the proper case when resolving module names).
                // Especially annoying if something starts with 'C:' and sometimes is entered with 'c:'.
                return f.getCanonicalPath();
            }
        } catch (IOException e) {
            return f.getAbsolutePath();
        }
    }

    /**
     * Searches a set of paths for files whose names match any of the provided patterns.
     *
     * @param pathsToSearch    The paths to search for files.
     * @param expectedPatterns A list of regex patterns that the filenames to find must match.
     *                         The patterns are in order of decreasing priority, meaning that filenames matching the
     *                         pattern at index i will appear earlier in the returned array than filenames matching
     *                         patterns at index i+1.
     * @return An array of all matching filenames found, in order of decreasing priority.
     */
    public static String[] searchPaths(java.util.Set<String> pathsToSearch, final List<String> expectedPatterns) {
        int n = expectedPatterns.size();

        @SuppressWarnings("unchecked")
        LinkedHashSet<String>[] pathSetsByPriority = new LinkedHashSet[n];
        LinkedHashSet<String> prioritizedPaths = new LinkedHashSet<String>();

        Pattern[] patterns = new Pattern[n];
        for (int i = 0; i < n; i++) {
            patterns[i] = Pattern.compile(expectedPatterns.get(i));
        }

        for (String s : pathsToSearch) {
            String pathname = s.trim();
            if (pathname.length() > 0) {
                File file = new File(pathname);
                if (file.isDirectory()) {
                    File[] available = file.listFiles();
                    if (available != null) {
                        for (File afile : available) {
                            int priority = matchesPattern(patterns, afile);
                            if (priority != INVALID) {
                                if (pathSetsByPriority[priority] == null) {
                                    pathSetsByPriority[priority] = new LinkedHashSet<String>();
                                }
                                LinkedHashSet<String> pathSet = pathSetsByPriority[priority];
                                File f = new File(file, afile.getName());
                                pathSet.add(getFileAbsolutePath(f));
                            }
                        }
                    }
                }
            }
        }

        for (LinkedHashSet<String> pathSet : pathSetsByPriority) {
            if (pathSet != null) {
                prioritizedPaths.addAll(pathSet);
            }
        }
        return prioritizedPaths.toArray(new String[prioritizedPaths.size()]);
    }

    public static @Nullable String getDefaultPythonExecutable() {
        List<String> searchPatterns;
        if (SystemInfo.isWindows) {
            searchPatterns = Arrays.asList("python.exe");

        } else {
            searchPatterns = Arrays.asList("python", "python\\d(\\.\\d)*");
        }
        Set<String> pathsToSearchPython = getPathsToSearchPython();
        final String[] ret = searchPaths(pathsToSearchPython, searchPatterns);
        if (ret.length > 0) {
            return ret[0];
        }
        return null;
    }
}
