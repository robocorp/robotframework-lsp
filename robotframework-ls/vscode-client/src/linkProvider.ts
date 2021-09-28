import { env, ExtensionContext, TerminalLinkContext, Uri, window } from "vscode";
import * as fs from "fs";

export async function registerLinkProviders(extensionContext: ExtensionContext) {
    extensionContext.subscriptions.push(
        window.registerTerminalLinkProvider({
            provideTerminalLinks(context: TerminalLinkContext) {
                let found = 0;
                const FOUND_LOG = 1;
                const FOUND_REPORT = 2;
                if (context.line.startsWith("Log:")) {
                    found = FOUND_LOG;
                } else if (context.line.startsWith("Report:")) {
                    found = FOUND_REPORT;
                } else {
                    return [];
                }

                if (context.line.endsWith("html")) {
                    let firstNonWhitespaceChar = found == FOUND_LOG ? 4 : 7;

                    for (; firstNonWhitespaceChar < context.line.length; firstNonWhitespaceChar++) {
                        let ch = context.line.charAt(firstNonWhitespaceChar);
                        if (ch != " " && ch != "\t") {
                            break;
                        }
                    }

                    if (firstNonWhitespaceChar < context.line.length - 1) {
                        let path: string = context.line.substring(firstNonWhitespaceChar).trim();
                        if (fs.existsSync(path)) {
                            return [
                                {
                                    startIndex: firstNonWhitespaceChar,
                                    length: path.length,
                                    tooltip:
                                        "Open " + (found == FOUND_LOG ? "Log" : "Report") + " in external Browser.",
                                    path: path,
                                },
                            ];
                        }
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
