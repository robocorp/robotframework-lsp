/*
 * Copyright (c) Robocorp Inc. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package robocorp.lsp.intellij;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.ui.MessageType;
import org.apache.commons.lang3.tuple.Pair;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.Launcher;
import org.eclipse.lsp4j.launch.LSPLauncher;
import org.eclipse.lsp4j.services.LanguageClient;
import org.eclipse.lsp4j.services.LanguageServer;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.*;
import java.util.concurrent.*;

class DefaultLanguageClient implements LanguageClient {

    @Override
    public void telemetryEvent(Object object) {

    }

    @Override
    public void publishDiagnostics(PublishDiagnosticsParams diagnostics) {

    }

    @Override
    public void showMessage(MessageParams messageParams) {

    }

    @Override
    public CompletableFuture<MessageActionItem> showMessageRequest(ShowMessageRequestParams requestParams) {
        return null;
    }

    @Override
    public void logMessage(MessageParams message) {

    }
}

public class LanguageServerManager {

    private static final Map<LanguageServerDefinition, LanguageServerManager> definitionToManager = new ConcurrentHashMap<>();
    private static final Object lockDefinitionToManager = new Object();
    private static final Logger LOG = Logger.getInstance(LanguageServerManager.class);

    public static @Nullable LanguageServerManager getInstance(@NotNull String ext) {
        if (!ext.startsWith(".")) {
            throw new AssertionError("Expected extension to start with '.'");
        }
        Set<Map.Entry<LanguageServerDefinition, LanguageServerManager>> entries = definitionToManager.entrySet();
        for (Map.Entry<LanguageServerDefinition, LanguageServerManager> entry : entries) {
            if(entry.getKey().ext.contains(ext)){
                return entry.getValue();
            }
        }
        return null;
    }

    public static LanguageServerManager getInstance(LanguageServerDefinition definition) {
        // First get unsynchronized for performance... if it doesn't work, sync it afterwards.
        LanguageServerManager languageServerManager = definitionToManager.get(definition);
        if (languageServerManager != null) {
            return languageServerManager;
        }
        synchronized (lockDefinitionToManager) {
            languageServerManager = definitionToManager.get(definition);
            if (languageServerManager == null) {
                languageServerManager = new LanguageServerManager(definition);
                definitionToManager.put(definition, languageServerManager);
            }
        }
        return languageServerManager;
    }

    public static LanguageServerManager start(LanguageServerDefinition definition, String ext, String projectRootPath) throws IOException {
        LanguageServerManager instance = getInstance(definition);
        instance.start(ext, projectRootPath);
        return instance;
    }

    public static void disposeAll() {
        synchronized (lockDefinitionToManager) {
            Set<Map.Entry<LanguageServerDefinition, LanguageServerManager>> entries = definitionToManager.entrySet();
            for (Map.Entry<LanguageServerDefinition, LanguageServerManager> entry : entries) {
                try {
                    entry.getValue().dispose();
                } catch (Exception e) {
                    LOG.error(e);
                }
            }
            entries.clear();
        }
    }

    private final LanguageServerDefinition languageServerDefinition;

    private final Map<String, LanguageServerComm> projectRootPathToComm = new ConcurrentHashMap<>();

    private final Object lockProjectRootPathToComm = new Object();

    private LanguageServerManager(LanguageServerDefinition definition) {
        this.languageServerDefinition = definition;
    }

    private void start(String ext, String projectRootPath) throws IOException {
        if (!ext.startsWith(".")) {
            throw new AssertionError("Expected extension to start with '.'");
        }
        if (languageServerDefinition.ext.contains(ext)) {
            synchronized (lockProjectRootPathToComm) {
                LanguageServerComm languageServerComm = projectRootPathToComm.get(projectRootPath);
                if (languageServerComm == null || !languageServerComm.isConnected()) {
                    Pair<InputStream, OutputStream> streams = languageServerDefinition.start(projectRootPath);
                    InputStream inputStream = streams.getKey();
                    OutputStream outputStream = streams.getValue();
                    DefaultLanguageClient client = new DefaultLanguageClient();
                    Launcher<LanguageServer> launcher = LSPLauncher.createClientLauncher(
                            client, inputStream, outputStream);

                    languageServerComm = new LanguageServerComm(client, launcher, projectRootPath, languageServerDefinition);
                    projectRootPathToComm.put(projectRootPath, languageServerComm);
                }
            }
        }
    }

    private void dispose() {
        synchronized (lockProjectRootPathToComm) {
            Set<Map.Entry<String, LanguageServerComm>> entries = projectRootPathToComm.entrySet();
            for (Map.Entry<String, LanguageServerComm> entry : entries) {
                try {
                    entry.getValue().shutdown();
                } catch (Exception e) {
                    LOG.error(e);
                }
            }
            projectRootPathToComm.clear();
        }
    }

    public LanguageServerComm getComm(String projectRootPath){
        return projectRootPathToComm.get(projectRootPath);
    }
}
