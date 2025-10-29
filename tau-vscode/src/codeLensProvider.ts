import * as vscode from 'vscode';

export class CodeLensProvider implements vscode.CodeLensProvider {
    private _onDidChangeCodeLenses: vscode.EventEmitter<void> = new vscode.EventEmitter<void>();
    public readonly onDidChangeCodeLenses: vscode.Event<void> = this._onDidChangeCodeLenses.event;

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

                // Add verification CodeLens
                const verifyCommand: vscode.Command = {
                    title: '▶ Verify',
                    command: 'tau.verify',
                    arguments: [document, i]
                };
                codeLenses.push(new vscode.CodeLens(range, verifyCommand));

                // Add spec generation/regeneration CodeLens
                if (hasSpecs) {
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
}
