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
import java.util.Objects;

public class StreamConnectionProvider {

    private final Logger LOG = Logger.getInstance(StreamConnectionProvider.class);

    @NotNull
    private ProcessBuilder builder;
    @Nullable
    private Process process = null;

    public StreamConnectionProvider(@NotNull ProcessBuilder processBuilder) {
        this.builder = processBuilder;
    }

    public void start() throws IOException {
        LOG.info("Starting server process.");
        process = builder.start();
        if (!process.isAlive()) {
            throw new IOException("Unable to start language server: " + this.toString());
        } else {
            LOG.info("Server process started " + process);
        }
    }

    @Nullable
    public InputStream getInputStream() {
        return process != null ? process.getInputStream() : null;
    }

    @Nullable
    public OutputStream getOutputStream() {
        return process != null ? process.getOutputStream() : null;
    }

    public void stop() {
        if (process != null) {
            process.destroy();
        }
    }

    @Override
    public boolean equals(Object obj) {
        if (obj instanceof StreamConnectionProvider) {
            StreamConnectionProvider other = (StreamConnectionProvider) obj;
            return builder.equals(other.builder);
        }
        return false;
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(builder);
    }
}
