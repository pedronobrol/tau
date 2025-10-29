import * as vscode from 'vscode';

export class CodeLensProvider implements vscode.CodeLensProvider {
    private _onDidChangeCodeLenses: vscode.EventEmitter<void> = new vscode.EventEmitter<void>();
    public readonly onDidChangeCodeLenses: vscode.Event<void> = this._onDidChangeCodeLenses.event;
    private generatingLines: Set<string> = new Set(); // Track which lines are generating (format: "filepath:line")

    public provideCodeLenses(
        document: vscode.TextDocument,
        _token: vscode.CancellationToken
    ): vscode.CodeLens[] | Thenable<vscode.CodeLens[]> {
        const codeLenses: vscode.CodeLens[] = [];

        // Find all @safe decorators
        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i);
            const text = line.text.trim();

            if (text.startsWith('@safe')) {
                const range = line.range;
                const hasSpecs = this.hasSpecsBelow(document, i);
                const lineKey = `${document.uri.fsPath}:${i}`;
                const isGenerating = this.generatingLines.has(lineKey);

                // Add verification CodeLens
                const verifyCommand: vscode.Command = {
                    title: '▶ Verify',
                    command: 'tau.verify',
                    arguments: [document, i]
                };
                codeLenses.push(new vscode.CodeLens(range, verifyCommand));

                // Add spec generation/regeneration CodeLens with loading state
                if (isGenerating) {
                    // Show loading spinner
                    const loadingCommand: vscode.Command = {
                        title: '⏳ Generating...',
                        command: '', // No command while loading
                        arguments: []
                    };
                    codeLenses.push(new vscode.CodeLens(range, loadingCommand));
                } else if (hasSpecs) {
                    const regenCommand: vscode.Command = {
                        title: '🔄 Regenerate Specs',
                        command: 'tau.generateSpecs',
                        arguments: [document, i]
                    };
                    codeLenses.push(new vscode.CodeLens(range, regenCommand));
                } else {
                    const genCommand: vscode.Command = {
                        title: '✨ Generate Specs',
                        command: 'tau.generateSpecs',
                        arguments: [document, i]
                    };
                    codeLenses.push(new vscode.CodeLens(range, genCommand));
                }
            }
        }

        return codeLenses;
    }

    public resolveCodeLens(
        codeLens: vscode.CodeLens,
        _token: vscode.CancellationToken
    ): vscode.CodeLens | Thenable<vscode.CodeLens> {
        return codeLens;
    }

    public refresh(): void {
        this._onDidChangeCodeLenses.fire();
    }

    private hasSpecsBelow(document: vscode.TextDocument, safeLine: number): boolean {
        // Check if @requires or @ensures exist below @safe
        for (let i = safeLine + 1; i < Math.min(document.lineCount, safeLine + 10); i++) {
            const line = document.lineAt(i).text.trim();
            if (line.startsWith('def ')) {
                break;  // Reached function definition
            }
            if (line.startsWith('@requires') || line.startsWith('@ensures')) {
                return true;
            }
        }
        return false;
    }

    public setGenerating(document: vscode.TextDocument, line: number, isGenerating: boolean): void {
        const lineKey = `${document.uri.fsPath}:${line}`;
        if (isGenerating) {
            this.generatingLines.add(lineKey);
        } else {
            this.generatingLines.delete(lineKey);
        }
        this.refresh();
    }
}
