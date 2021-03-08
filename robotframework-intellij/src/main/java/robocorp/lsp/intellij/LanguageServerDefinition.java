/*
 * Original work Copyright (c) 2019, WSO2 Inc. (http://www.wso2.org) (Apache 2.0)
 * See ThirdPartyNotices.txt in the project root for license information.
 * All modifications Copyright (c) Robocorp Technologies Inc.
 * All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License")
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http: // www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import org.jetbrains.annotations.Nullable;

import java.io.*;
import java.net.Socket;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.TimeUnit;

public abstract class LanguageServerDefinition {

    /**
     * Subclasses must override to return the settings to be sent to the language server.
     */
    public abstract Object getPreferences();

    public interface IPreferencesListener {
        void onChanged(String property, String oldValue, String newValue);
    }

    /**
     * Subclasses must notify when a setting has changed so that it can be sent to the language server.
     */
    public abstract void unregisterPreferencesListener(IPreferencesListener preferencesListener);

    /**
     * Subclasses must notify when a setting has changed so that it can be sent to the language server.
     */
    public abstract void registerPreferencesListener(IPreferencesListener o);

    private static final class SocketStreamProvider {

        private final String host;
        private final int port;
        private InputStream fInputStream;
        private OutputStream fOutputStream;

        public SocketStreamProvider(String host, int port) {
            this.host = host;
            this.port = port;
        }

        private void initializeConnection() throws IOException {
            Socket socket = new Socket(host, port);
            fInputStream = socket.getInputStream();
            fOutputStream = socket.getOutputStream();
        }

        public InputStream getInputStream() throws IOException {
            if (fInputStream == null) {
                initializeConnection();
            }
            return fInputStream;
        }

        public OutputStream getOutputStream() throws IOException {
            if (fOutputStream == null) {
                initializeConnection();
            }
            return fOutputStream;
        }
    }

    public static class LanguageServerStreams {

        private final Logger LOG = Logger.getInstance(LanguageServerStreams.class);

        @Nullable
        private final ProcessBuilder builder;
        private final int port;

        @Nullable
        private Process process = null;

        @Nullable
        private SocketStreamProvider socketStreamProvider = null;
        private File file;

        public LanguageServerStreams(@Nullable ProcessBuilder processBuilder, int port) {
            this.builder = processBuilder;
            this.port = port;
        }

        public void start() throws IOException {
            LOG.info("Starting server process.");

            if (port > 0) {
                LOG.info("Server connecting to " + port);
                this.socketStreamProvider = new SocketStreamProvider("127.0.0.1", port);
            } else {
                if (this.builder == null) {
                    throw new IOException("Unable to start language server: " + this.toString() + " python executable must be set.");
                }
                process = builder.start();
                String property = System.getProperty("user.home");
                File dir = new File(property, ".robotframework-ls");
                dir.mkdirs();

                DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyy-MM-dd HH_mm");
                File file = new File(dir, ".intellij-rf-ls-" + dtf.format(LocalDateTime.now()) + ".log");
                this.file = file;

                StreamRedirectorThread thread = new StreamRedirectorThread(process.getErrorStream(), new FileOutputStream(file, true));
                thread.start();
                verifyProcess();
                LOG.info("Server process started " + process + ".\nStderr may be seen at:\n" + file);
            }
        }

        public void verifyProcess() throws IOException {
            if (this.port <= 0) {
                if (!process.isAlive()) {
                    String msg;
                    if (builder == null) {
                        msg = "<N/A> (ProcessBuilder is null!)";
                    } else {
                        msg = "" + builder.command();
                    }
                    throw new IOException("Language server process exited.\nCommand line: " + msg + ".\nStderr may be seen at:\n" + file + "\n");
                }
            }
        }

        @Nullable
        public InputStream getInputStream() {
            if (this.socketStreamProvider != null) {
                try {
                    return this.socketStreamProvider.getInputStream();
                } catch (IOException e) {
                    throw new RuntimeException(e);
                }
            }
            return process != null ? process.getInputStream() : null;
        }

        @Nullable
        public OutputStream getOutputStream() {
            if (this.socketStreamProvider != null) {
                try {
                    return this.socketStreamProvider.getOutputStream();
                } catch (IOException e) {
                    throw new RuntimeException(e);
                }
            }
            return process != null ? process.getOutputStream() : null;
        }

        public void stop() {
            if (this.socketStreamProvider != null) {
                return; // We can't really stop in this case.
            }
            if (process != null) {
                boolean exited = false;

                try {
                    exited = process.waitFor(1, TimeUnit.SECONDS);
                } catch (InterruptedException e) {
                    // ignore
                }
                if (!exited) {
                    process.destroy();
                }
            }
        }

        @Override
        public boolean equals(Object obj) {
            if (obj instanceof LanguageServerStreams) {
                LanguageServerStreams other = (LanguageServerStreams) obj;
                return Objects.equals(builder, other.builder);
            }
            return false;
        }

        @Override
        public int hashCode() {
            return Objects.hashCode(builder);
        }
    }

    private static final Logger LOG = Logger.getInstance(LanguageServerDefinition.class);
    private final String languageId;

    public final Set<String> ext;

    // May be changed when preferences change.
    private int port;

    // May be changed when preferences change.
    private @Nullable ProcessBuilder processBuilder;

    public final Callbacks<LanguageServerDefinition> onChangedLanguageDefinition = new Callbacks<>();

    /**
     * @param processBuilder may be null if the python executable is not available.
     */
    public LanguageServerDefinition(Set<String> ext, @Nullable ProcessBuilder processBuilder, int port, String languageId) {
        this.languageId = languageId;
        for (String s : ext) {
            if (!s.startsWith(".")) {
                throw new AssertionError("Expected extension to start with '.'");
            }
        }

        this.ext = Set.copyOf(ext);
        this.port = port;
        this.processBuilder = processBuilder;
    }

    public void setProcessBuilder(@Nullable ProcessBuilder processBuilder) {
        this.processBuilder = processBuilder;
        onChangedLanguageDefinition.onCallback(this);
    }

    public void setPort(int port) {
        this.port = port;
        onChangedLanguageDefinition.onCallback(this);
    }

    /**
     * Creates a StreamConnectionProvider given the working directory
     *
     * @return The stream connection provider or null if it's not possible to create one.
     */
    public @Nullable LanguageServerStreams createConnectionProvider() {
        if (processBuilder == null && port <= 0) {
            return null;
        }
        return new LanguageServerStreams(processBuilder, port);
    }

    @Override
    public String toString() {
        return "ServerDefinition for " + ext + " - " + languageId;
    }

    public String getLanguageId() {
        return languageId;
    }

}