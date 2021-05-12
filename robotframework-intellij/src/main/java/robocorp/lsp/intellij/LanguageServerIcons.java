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

import com.intellij.icons.AllIcons;
import com.intellij.icons.AllIcons.Nodes;
import org.eclipse.lsp4j.CompletionItemKind;
import org.eclipse.lsp4j.SymbolKind;

import javax.swing.*;

public class LanguageServerIcons {
    public static Icon getCompletionIcon(CompletionItemKind kind) {

        if (kind == null) {
            return null;
        }

        switch (kind) {
            case Class:
                return Nodes.Class;
            case Enum:
                return Nodes.Enum;
            case Field:
                return Nodes.Field;
            case File:
                return AllIcons.FileTypes.Any_type;
            case Function:
                return Nodes.Function;
            case Interface:
                return Nodes.Interface;
            case Keyword:
                return Nodes.UpLevel;
            case Method:
                return Nodes.Method;
            case Module:
                return Nodes.Module;
            case Property:
                return Nodes.Property;
            case Reference:
                return Nodes.MethodReference;
            case Snippet:
                return Nodes.Static;
            case Text:
                return AllIcons.FileTypes.Text;
            case Unit:
                return Nodes.Artifact;
            case Variable:
                return Nodes.Variable;
            default:
                return null;
        }
    }

    public static Icon getSymbolIcon(SymbolKind kind) {

        if (kind == null) {
            return null;
        }

        switch (kind) {
            case Field:
            case EnumMember:
                return Nodes.Field;
            case Method:
            case Function:
                return Nodes.Method;
            case Variable:
                return Nodes.Variable;
            case Class:
                return Nodes.Class;
            case Constructor:
                return Nodes.ClassInitializer;
            case Enum:
                return Nodes.Enum;
            case Namespace:
                return AllIcons.General.Settings;
            default:
                return Nodes.Tag;
        }
    }

}
