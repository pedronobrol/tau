import * as vscode from 'vscode';
import { CompletionProvider } from './completionProvider';
import { CodeLensProvider } from './codeLensProvider';
import { DecorationProvider } from './decorationProvider';
import { TauClient } from './tauClient';
import { DiagnosticsManager } from './diagnosticsManager';

let decorationProvider: DecorationProvider;
let diagnosticsManager: DiagnosticsManager;
let tauClient: TauClient;
let completionProvider: CompletionProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('TAU Formal Verification extension activated');

    // Get configuration
    const config = vscode.workspace.getConfiguration('tau');
    const serverUrl = config.get<string>('serverUrl', 'http://localhost:8000');

    // Initialize services
    tauClient = new TauClient(serverUrl);
    decorationProvider = new DecorationProvider();
    diagnosticsManager = new DiagnosticsManager();

    // Initialize completion provider
    completionProvider = new CompletionProvider(tauClient);
    context.subscriptions.push(
        vscode.languages.registerInlineCompletionItemProvider(
            { language: 'python' },
            completionProvider
        )
    );

    // Check if server is running
    tauClient.healthCheck().then(isRunning => {
        if (!isRunning) {
            vscode.window.showWarningMessage(
                'TAU server is not running. Start it with: python3 tau/server.py',
                'Start Server'
            ).then((choice: string | undefined) => {
                if (choice === 'Start Server') {
                    const terminal = vscode.window.createTerminal('TAU Server');
                    terminal.sendText('cd ' + vscode.workspace.workspaceFolders?.[0].uri.fsPath);
                    terminal.sendText('python3 tau/server.py');
                    terminal.show();
                }
            });
        } else {
            vscode.window.showInformationMessage('TAU server is running');
        }
    });

    // Register CodeLens provider for verification triggers
    const codeLensProvider = new CodeLensProvider();
    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider(
            { language: 'python' },
            codeLensProvider
        )
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('tau.generateSpecs', async (_document?: vscode.TextDocument, line?: number) => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }

            // If line is provided (clicked from CodeLens), use it. Otherwise find current cursor line
            const targetLine = line !== undefined ? line : editor.selection.active.line;

            // Show loading state in CodeLens
            codeLensProvider.setGenerating(editor.document, targetLine, true);

            try {
                await completionProvider.generateSpecsAtCursor(editor);
            } finally {
                // Hide loading state
                codeLensProvider.setGenerating(editor.document, targetLine, false);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('tau.verify', async (document: vscode.TextDocument, line: number) => {
            await verifyFunction(document, line, codeLensProvider);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('tau.verifyFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }
            await verifyFile(editor.document, codeLensProvider);
        })
    );

    // Auto-verify on save if enabled
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            const config = vscode.workspace.getConfiguration('tau');
            const autoVerify = config.get<boolean>('autoVerifyOnSave', false);

            if (autoVerify && document.languageId === 'python') {
                await verifyFile(document, codeLensProvider);
            }
        })
    );

    // Clear verification status when document content changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument((event) => {
            // Clear verification status when user edits the document
            codeLensProvider.clearVerificationStatus(event.document);
        })
    );
}

async function verifyFunction(document: vscode.TextDocument, line: number, codeLensProvider: CodeLensProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }

    // Find function name at line
    const functionName = findFunctionNameAtLine(document, line);
    if (!functionName) {
        vscode.window.showErrorMessage('Could not find function at this line');
        return;
    }

    // Show verifying state
    codeLensProvider.setVerifying(document, line, true);

    // Show progress
    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: `Verifying ${functionName}...`,
            cancellable: false
        },
        async (progress) => {
            try {
                const result = await tauClient.verifyFunctionStream(
                    document.uri.fsPath,
                    functionName,
                    (progressUpdate) => {
                        progress.report({
                            message: progressUpdate.message,
                            increment: progressUpdate.progress * 100
                        });
                    }
                );

                // Update CodeLens status
                if (result && result.verified) {
                    codeLensProvider.setVerificationStatus(document, line, true, result.hash);
                } else {
                    const reason = result?.reason || 'Verification failed';
                    codeLensProvider.setVerificationStatus(document, line, false, undefined, reason);

                    // Add diagnostics
                    if (result) {
                        diagnosticsManager.addDiagnostic(document, line, reason);
                    }
                }
            } catch (error) {
                codeLensProvider.setVerificationStatus(document, line, false, undefined, `Error: ${error}`);
            } finally {
                // Clear verifying state
                codeLensProvider.setVerifying(document, line, false);
            }
        }
    );
}

async function verifyFile(document: vscode.TextDocument, codeLensProvider: CodeLensProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Verifying all functions...',
            cancellable: false
        },
        async () => {
            try {
                const summary = await tauClient.verifyFile(document.uri.fsPath);

                if (!summary) {
                    vscode.window.showErrorMessage('Failed to verify file. Is TAU server running?');
                    return;
                }

                // Clear existing diagnostics
                diagnosticsManager.clear(document);

                // Update CodeLens status and diagnostics
                for (const result of summary.results) {
                    const line = result.line;

                    if (result.verified) {
                        codeLensProvider.setVerificationStatus(document, line, true, result.hash);
                    } else {
                        const reason = result.reason || 'Verification failed';
                        codeLensProvider.setVerificationStatus(document, line, false, undefined, reason);
                        diagnosticsManager.addDiagnostic(document, line, reason);
                    }
                }
            } catch (error) {
                // Silent - errors shown in CodeLens and diagnostics
            }
        }
    );
}

function findFunctionNameAtLine(document: vscode.TextDocument, line: number): string | null {
    // Search forward from @safe to find the function definition (skipping decorators)
    for (let i = line; i < Math.min(document.lineCount, line + 20); i++) {
        const lineText = document.lineAt(i).text;
        const match = lineText.match(/def\s+(\w+)\s*\(/);
        if (match) {
            return match[1];
        }
    }
    return null;
}

export function deactivate() {
    if (diagnosticsManager) {
        diagnosticsManager.dispose();
    }
    if (decorationProvider) {
        decorationProvider.dispose();
    }
}
