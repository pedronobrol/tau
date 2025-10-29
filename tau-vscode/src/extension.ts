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

    // Register completion provider for @safe
    completionProvider = new CompletionProvider(tauClient);
    context.subscriptions.push(
        vscode.languages.registerInlineCompletionItemProvider(
            { language: 'python' },
            completionProvider
        )
    );

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
        vscode.commands.registerCommand('tau.generateSpecs', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }
            await completionProvider.generateSpecsAtCursor(editor);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('tau.verify', async (document: vscode.TextDocument, line: number) => {
            await verifyFunction(document, line);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('tau.verifyFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }
            await verifyFile(editor.document);
        })
    );

    // Auto-verify on save if enabled
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            const config = vscode.workspace.getConfiguration('tau');
            const autoVerify = config.get<boolean>('autoVerifyOnSave', false);

            if (autoVerify && document.languageId === 'python') {
                await verifyFile(document);
            }
        })
    );

    // Update decorations when document changes
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (editor) {
                decorationProvider.updateDecorations(editor);
            }
        })
    );

    // Initial decoration update
    if (vscode.window.activeTextEditor) {
        decorationProvider.updateDecorations(vscode.window.activeTextEditor);
    }
}

async function verifyFunction(document: vscode.TextDocument, line: number) {
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

    // Show progress
    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: `Verifying ${functionName}...`,
            cancellable: false
        },
        async (progress) => {
            // Start spinner decoration
            decorationProvider.showSpinner(editor, line);

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

                // Update decorations
                if (result && result.verified) {
                    decorationProvider.showSuccess(editor, line, result.hash || '');
                    vscode.window.showInformationMessage(`✓ ${functionName} verified successfully!`);
                } else {
                    decorationProvider.showFailure(editor, line);
                    vscode.window.showErrorMessage(`✗ ${functionName} verification failed`);

                    // Add diagnostics
                    if (result) {
                        diagnosticsManager.addDiagnostic(document, line, result.reason || 'Verification failed');
                    }
                }
            } catch (error) {
                decorationProvider.clearSpinner(editor, line);
                vscode.window.showErrorMessage(`Error: ${error}`);
            }
        }
    );
}

async function verifyFile(document: vscode.TextDocument) {
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

                // Update decorations and diagnostics
                for (const result of summary.results) {
                    const line = result.line;

                    if (result.verified) {
                        decorationProvider.showSuccess(editor, line, result.hash || '');
                    } else {
                        decorationProvider.showFailure(editor, line);
                        diagnosticsManager.addDiagnostic(document, line, result.reason || 'Verification failed');
                    }
                }

                vscode.window.showInformationMessage(`Verification complete: ${summary.passed}/${summary.total} passed`);
            } catch (error) {
                vscode.window.showErrorMessage(`Error: ${error}`);
            }
        }
    );
}

function findFunctionNameAtLine(document: vscode.TextDocument, line: number): string | null {
    // Search backwards from the line to find the function definition
    for (let i = line; i >= Math.max(0, line - 20); i--) {
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
