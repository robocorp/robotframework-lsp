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

import com.intellij.ide.util.gotoByName.ChooseByNamePopup;
import com.intellij.navigation.ChooseByNameContributorEx;
import com.intellij.navigation.ItemPresentation;
import com.intellij.navigation.NavigationItem;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.extensions.ExtensionPointName;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.LocalFileSystem;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.psi.search.GlobalSearchScope;
import com.intellij.util.Processor;
import com.intellij.util.indexing.FindSymbolParameters;
import com.intellij.util.indexing.IdFilter;
import org.eclipse.lsp4j.Location;
import org.eclipse.lsp4j.SymbolInformation;
import org.eclipse.lsp4j.WorkspaceSymbolParams;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public class FeatureSymbols implements ChooseByNameContributorEx {

    private static final Logger LOG = Logger.getInstance(FeatureSymbols.class);

    public static class LSPNavigationItem extends OpenFileDescriptor implements NavigationItem {

        private final ItemPresentation presentation;

        LSPNavigationItem(String name, String location, Icon icon, @NotNull Project project, @NotNull VirtualFile file,
                          int logicalLine, int logicalColumn) {
            super(project, file, logicalLine, logicalColumn);
            presentation = new LSPItemPresentation(location, name, icon);
        }

        @Nullable
        @Override
        public String getName() {
            return presentation.getPresentableText();
        }

        @Nullable
        @Override
        public ItemPresentation getPresentation() {
            return presentation;
        }

        @Override
        public boolean equals(Object obj) {
            if (obj instanceof LSPNavigationItem) {
                LSPNavigationItem other = (LSPNavigationItem) obj;
                return this.getLine() == other.getLine() && this.getColumn() == other.getColumn() &&
                        Objects.equals(this.getName(), other.getName());
            }
            return false;
        }

        @Override
        public int hashCode() {
            return Objects.hash(this.getLine(), this.getColumn(), this.getName());
        }

        private static class LSPItemPresentation implements ItemPresentation {

            private final String location;
            private final String presentableText;
            private final Icon icon;

            LSPItemPresentation(String location, String presentableText, Icon icon) {
                this.location = location;
                this.presentableText = presentableText;
                this.icon = icon;
            }

            @Nullable
            @Override
            public String getPresentableText() {
                return presentableText;
            }

            @Nullable
            @Override
            public String getLocationString() {
                return location;
            }

            @Nullable
            @Override
            public Icon getIcon(boolean unused) {
                return icon;
            }
        }
    }

    public static class WorkspaceSymbolProvider {

        public WorkspaceSymbolProvider() {
        }

        private static final Logger LOG = Logger.getInstance(WorkspaceSymbolProvider.class);
        private static final ExtensionPointName<ILanguageDefinitionContributor> EP_NAME =
                ExtensionPointName.create("robocorp.lsp.intellij.languageDefinitionContributor");

        public List<LSPNavigationItem> workspaceSymbols(String name, Project project) {
            List<LSPNavigationItem> lst = new ArrayList<>();
            try {
                String basePath = project.getBasePath();
                if (basePath == null) {
                    return lst;
                }
                for (ILanguageDefinitionContributor contributor : EP_NAME.getExtensionList()) {
                    LanguageServerDefinition languageDefinition = contributor.getLanguageDefinition();
                    LanguageServerManager languageServerManager = LanguageServerManager.getInstance(languageDefinition);
                    LanguageServerCommunication comm = languageServerManager.getLanguageServerCommunication(languageDefinition.ext.iterator().next(), basePath, project);
                    if (comm == null) {
                        return lst;
                    }

                    final WorkspaceSymbolParams symbolParams = new WorkspaceSymbolParams(name);
                    CompletableFuture<List<? extends SymbolInformation>> symbol = comm.symbol(symbolParams);
                    if (symbol == null) {
                        return lst;
                    }
                    List<? extends SymbolInformation> symbolInformation;
                    try {
                        symbolInformation = symbol.get(Timeouts.getSymbolsTimeout(), TimeUnit.SECONDS);
                    } catch (TimeoutException e) {
                        LOG.warn("Request for workspace symbols timed out.");
                        return lst;
                    }
                    if (symbolInformation == null) {
                        LOG.warn("Symbol information not available.");
                        return lst;
                    }
                    for (SymbolInformation information : symbolInformation) {
                        final Location location = information.getLocation();
                        String uri = location.getUri();
                        File file = Uris.toFile(uri);
                        if (file != null) {
                            VirtualFile virtualFile = LocalFileSystem.getInstance().findFileByIoFile(file);
                            if (virtualFile != null) {
                                lst.add(new LSPNavigationItem(
                                        information.getName(),
                                        information.getContainerName(),
                                        LanguageServerIcons.getSymbolIcon(information.getKind()),
                                        project,
                                        virtualFile,
                                        location.getRange().getStart().getLine(),
                                        location.getRange().getStart().getCharacter()
                                ));
                            }
                        }
                    }
                }
            } catch (ProcessCanceledException | CancellationException e) {
                // ignore
            } catch (Exception e) {
                LOG.error(e);
                return lst;
            }
            return lst;
        }
    }

    private final WorkspaceSymbolProvider workspaceSymbolProvider = new WorkspaceSymbolProvider();

    @Override
    public void processNames(@NotNull Processor<? super String> processor, @NotNull GlobalSearchScope globalSearchScope, @Nullable IdFilter idFilter) {
        Project project = globalSearchScope.getProject();
        if (project == null) {
            LOG.info("Not getting workspace symbols for language server (project is null).");
            return;
        }
        String queryString = project.getUserData(ChooseByNamePopup.CURRENT_SEARCH_PATTERN);
        if (queryString == null) {
            queryString = "";
        }

        for (LSPNavigationItem item : workspaceSymbolProvider.workspaceSymbols(queryString, project)) {
            if (globalSearchScope.isSearchInLibraries() || globalSearchScope.accept(item.getFile())) {
                if (!processor.process(item.getName())) {
                    break;
                }
            }
        }
    }

    @Override
    public void processElementsWithName(@NotNull String s, @NotNull Processor<? super NavigationItem> processor, @NotNull FindSymbolParameters findSymbolParameters) {
        GlobalSearchScope searchScope = findSymbolParameters.getSearchScope();

        for (LSPNavigationItem item : workspaceSymbolProvider.workspaceSymbols(s, findSymbolParameters.getProject())) {
            if (searchScope.isSearchInLibraries() || searchScope.accept(item.getFile())) {
                if (!processor.process(item)) {
                    break;
                }
            }
        }
    }
}