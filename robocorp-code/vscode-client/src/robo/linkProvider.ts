import { env, ExtensionContext, TerminalLinkContext, Uri, window } from "vscode";
import * as fs from "fs";

export async function registerLinkProviders(extensionContext: ExtensionContext) {
    extensionContext.subscriptions.push(
        window.registerTerminalLinkProvider({
            provideTerminalLinks(context: TerminalLinkContext) {
                if(context.line.indexOf("Robocorp Log") != -1){
                    console.log('here');
                }
                const regex = /(Robocorp Log(\s*\(html\)\s*)?:\s*)(.+\.html)/;
                const match = context.line.match(regex);
                if(match){
                    let path: string = match[3].trim();
                    if (fs.existsSync(path)) {
                        return [
                            {
                                startIndex: match.index + match[1].length,
                                length: path.length,
                                tooltip:
                                    "Open Log in external Browser.",
                                path: path,
                            },
                        ];
                    }

                }

                return [];
            },
            handleTerminalLink(link: any) {
                env.openExternal(Uri.file(link.path));
            },
        })
    );
}
