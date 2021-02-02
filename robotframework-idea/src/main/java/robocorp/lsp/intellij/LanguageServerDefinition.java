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
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.TimeUnit;

public class LanguageServerDefinition {

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

        @NotNull
        private final ProcessBuilder builder;

        @Nullable
        private Process process = null;

        @Nullable
        private SocketStreamProvider socketStreamProvider = null;

        public LanguageServerStreams(@NotNull ProcessBuilder processBuilder) {
            this.builder = processBuilder;
        }

        public void start() throws IOException {
            LOG.info("Starting server process.");

            String lsp_socket_ip = System.getenv("LSP_SOCKET_IP");
            String lsp_socket_port = System.getenv("LSP_SOCKET_PORT");
            // lsp_socket_ip = "127.0.0.1";
            // lsp_socket_port = "1456";
            if (lsp_socket_ip != null && lsp_socket_port != null) {
                LOG.info("Server connecting to " + lsp_socket_ip + " - " + lsp_socket_port);
                this.socketStreamProvider = new SocketStreamProvider(lsp_socket_ip, Integer.parseInt(lsp_socket_port));
            } else {
                process = builder.start();
                if (!process.isAlive()) {
                    throw new IOException("Unable to start language server: " + this.toString());
                } else {
                    LOG.info("Server process started " + process);
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
                return builder.equals(other.builder);
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

    public Set<String> ext;
    protected ProcessBuilder processBuilder;

    public LanguageServerDefinition(Set<String> ext, ProcessBuilder process, String languageId) {
        this.languageId = languageId;
        for (String s : ext) {
            if (!s.startsWith(".")) {
                throw new AssertionError("Expected extension to start with '.'");
            }
        }

        this.ext = ext;
        this.processBuilder = process;
    }

    /**
     * Creates a StreamConnectionProvider given the working directory
     *
     * @param workingDir The root directory
     * @return The stream connection provider
     */
    public LanguageServerStreams createConnectionProvider(String workingDir) {
        return new LanguageServerStreams(processBuilder);
    }

    @Override
    public String toString() {
        return "ServerDefinition for " + ext + " - " + languageId;
    }

    public String getLanguageId() {
        return languageId;
    }

}