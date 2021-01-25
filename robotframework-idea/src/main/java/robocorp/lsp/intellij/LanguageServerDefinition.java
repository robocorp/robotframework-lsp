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
import org.apache.commons.lang3.tuple.ImmutablePair;
import org.apache.commons.lang3.tuple.Pair;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * A trait representing a ServerDefinition
 */
public class LanguageServerDefinition {

    private static final Logger LOG = Logger.getInstance(LanguageServerDefinition.class);

    public Set<String> ext;
    private Map<String, StreamConnectionProvider> streamConnectionProviders = new ConcurrentHashMap<>();
    private static final Object streamConnectionProvidersLock = new Object();
    protected ProcessBuilder processBuilder;

    public LanguageServerDefinition(Set<String> ext, ProcessBuilder process) {
        for(String s:ext) {
            if (!s.startsWith(".")) {
                throw new AssertionError("Expected extension to start with '.'");
            }
        }

        this.ext = ext;
        this.processBuilder = process;
    }

    /**
     * Starts a Language server for the given directory and returns a tuple (InputStream, OutputStream)
     *
     * @param workingDir The root directory
     * @return The input and output streams of the server
     * @throws IOException if the stream connection provider is crashed
     */
    public Pair<InputStream, OutputStream> start(String workingDir) throws IOException {
        synchronized (streamConnectionProvidersLock) {
            StreamConnectionProvider streamConnectionProvider = streamConnectionProviders.get(workingDir);
            if (streamConnectionProvider != null) {
                return new ImmutablePair<>(streamConnectionProvider.getInputStream(), streamConnectionProvider.getOutputStream());
            } else {
                streamConnectionProvider = createConnectionProvider(workingDir);
                streamConnectionProvider.start();
                streamConnectionProviders.put(workingDir, streamConnectionProvider);
                return new ImmutablePair<>(streamConnectionProvider.getInputStream(), streamConnectionProvider.getOutputStream());
            }
        }
    }

    /**
     * Stops the Language server corresponding to the given working directory
     *
     * @param workingDir The root directory
     */
    public void stop(String workingDir) {
        synchronized (streamConnectionProvidersLock) {
            StreamConnectionProvider streamConnectionProvider = streamConnectionProviders.get(workingDir);
            if (streamConnectionProvider != null) {
                streamConnectionProvider.stop();
                streamConnectionProviders.remove(workingDir);
            } else {
                LOG.warn("No connection for workingDir " + workingDir + " and ext " + ext);
            }
        }
    }

    @Override
    public String toString() {
        return "ServerDefinition for " + ext;
    }

    /**
     * Creates a StreamConnectionProvider given the working directory
     *
     * @param workingDir The root directory
     * @return The stream connection provider
     */
    public StreamConnectionProvider createConnectionProvider(String workingDir) {
        return new StreamConnectionProvider(processBuilder);
    }

}