"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const completionProvider_1 = require("./completionProvider");
const codeLensProvider_1 = require("./codeLensProvider");
const decorationProvider_1 = require("./decorationProvider");
const tauClient_1 = require("./tauClient");
const diagnosticsManager_1 = require("./diagnosticsManager");
let decorationProvider;
let diagnosticsManager;
let tauClient;
let completionProvider;
function activate(context) {
    console.log('TAU Formal Verification extension activated');
    // Get configuration
    const config = vscode.workspace.getConfiguration('tau');
    const serverUrl = config.get('serverUrl', 'http://localhost:8000');
    // Initialize services
    tauClient = new tauClient_1.TauClient(serverUrl);
    decorationProvider = new decorationProvider_1.DecorationProvider();
    diagnosticsManager = new diagnosticsManager_1.DiagnosticsManager();
    // Check if server is running
    tauClient.healthCheck().then(isRunning => {
        if (!isRunning) {
            vscode.window.showWarningMessage('TAU server is not running. Start it with: python3 tau/server.py', 'Start Server').then((choice) => {
                if (choice === 'Start Server') {
                    const terminal = vscode.window.createTerminal('TAU Server');
                    terminal.sendText('cd ' + vscode.workspace.workspaceFolders?.[0].uri.fsPath);
                    terminal.sendText('python3 tau/server.py');
                    terminal.show();
                }
            });
        }
        else {
            vscode.window.showInformationMessage('TAU server is running');
        }
    });
    // Register completion provider for @safe
    completionProvider = new completionProvider_1.CompletionProvider(tauClient);
    context.subscriptions.push(vscode.languages.registerInlineCompletionItemProvider({ language: 'python' }, completionProvider));
    // Register CodeLens provider for verification triggers
    const codeLensProvider = new codeLensProvider_1.CodeLensProvider();
    context.subscriptions.push(vscode.languages.registerCodeLensProvider({ language: 'python' }, codeLensProvider));
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('tau.generateSpecs', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }
        await completionProvider.generateSpecsAtCursor(editor);
    }));
    context.subscriptions.push(vscode.commands.registerCommand('tau.verify', async (document, line) => {
        await verifyFunction(document, line);
    }));
    context.subscriptions.push(vscode.commands.registerCommand('tau.verifyFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }
        await verifyFile(editor.document);
    }));
    // Auto-verify on save if enabled
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('tau');
        const autoVerify = config.get('autoVerifyOnSave', false);
        if (autoVerify && document.languageId === 'python') {
            await verifyFile(document);
        }
    }));
    // Update decorations when document changes
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
            decorationProvider.updateDecorations(editor);
        }
    }));
    // Initial decoration update
    if (vscode.window.activeTextEditor) {
        decorationProvider.updateDecorations(vscode.window.activeTextEditor);
    }
}
async function verifyFunction(document, line) {
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
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Verifying ${functionName}...`,
        cancellable: false
    }, async (progress) => {
        // Start spinner decoration
        decorationProvider.showSpinner(editor, line);
        try {
            const result = await tauClient.verifyFunctionStream(document.uri.fsPath, functionName, (progressUpdate) => {
                progress.report({
                    message: progressUpdate.message,
                    increment: progressUpdate.progress * 100
                });
            });
            // Update decorations
            if (result && result.verified) {
                decorationProvider.showSuccess(editor, line, result.hash || '');
                vscode.window.showInformationMessage(`✓ ${functionName} verified successfully!`);
            }
            else {
                decorationProvider.showFailure(editor, line);
                vscode.window.showErrorMessage(`✗ ${functionName} verification failed`);
                // Add diagnostics
                if (result) {
                    diagnosticsManager.addDiagnostic(document, line, result.reason || 'Verification failed');
                }
            }
        }
        catch (error) {
            decorationProvider.clearSpinner(editor, line);
            vscode.window.showErrorMessage(`Error: ${error}`);
        }
    });
}
async function verifyFile(document) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Verifying all functions...',
        cancellable: false
    }, async () => {
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
                }
                else {
                    decorationProvider.showFailure(editor, line);
                    diagnosticsManager.addDiagnostic(document, line, result.reason || 'Verification failed');
                }
            }
            vscode.window.showInformationMessage(`Verification complete: ${summary.passed}/${summary.total} passed`);
        }
        catch (error) {
            vscode.window.showErrorMessage(`Error: ${error}`);
        }
    });
}
function findFunctionNameAtLine(document, line) {
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
function deactivate() {
    if (diagnosticsManager) {
        diagnosticsManager.dispose();
    }
    if (decorationProvider) {
        decorationProvider.dispose();
    }
}
//# sourceMappingURL=extension.js.map