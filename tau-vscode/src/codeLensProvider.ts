import * as vscode from 'vscode';

interface VerificationStatus {
    verified: boolean;
    hash?: string;
    reason?: string; // Failure reason
}

export class CodeLensProvider implements vscode.CodeLensProvider {
    private _onDidChangeCodeLenses: vscode.EventEmitter<void> = new vscode.EventEmitter<void>();
    public readonly onDidChangeCodeLenses: vscode.Event<void> = this._onDidChangeCodeLenses.event;
    private generatingLines: Set<string> = new Set(); // Track which lines are generating (format: "filepath:line")
    private verifyingLines: Set<string> = new Set(); // Track which lines are verifying (format: "filepath:line")
    private verificationStatus: Map<string, VerificationStatus> = new Map(); // Store verification results (format: "filepath:line")

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
                const isVerifying = this.verifyingLines.has(lineKey);
                const status = this.verificationStatus.get(lineKey);

                // If generating specs, only show loading indicator
                if (isGenerating) {
                    const loadingCommand: vscode.Command = {
                        title: '$(sync~spin)  Generating specs...',
                        command: '', // No command while loading
                        arguments: []
                    };
                    codeLenses.push(new vscode.CodeLens(range, loadingCommand));
                }
                // If verifying, only show loading indicator
                else if (isVerifying) {
                    const loadingCommand: vscode.Command = {
                        title: '$(sync~spin)  Verifying code...',
                        command: '', // No command while loading
                        arguments: []
                    };
                    codeLenses.push(new vscode.CodeLens(range, loadingCommand));
                }
                // Show status and buttons based on verification result
                else {
                    if (status) {
                        if (status.verified) {
                            // Passed: only show hash with green check icon, no buttons
                            const statusCommand: vscode.Command = {
                                title: `$(testing-passed-icon)  #${status.hash?.substring(0, 8) || ''}`,
                                command: '', // Status is not clickable
                                arguments: []
                            };
                            codeLenses.push(new vscode.CodeLens(range, statusCommand));
                        } else {
                            // Failed: show red error icon (hover shows reason)
                            const reason = status.reason || 'Verification failed';
                            const statusCommand: vscode.Command = {
                                title: `$(testing-failed-icon)  #${status.hash?.substring(0, 8) || 'failed'}`,
                                command: '', // Status is not clickable
                                arguments: [],
                                tooltip: reason
                            };
                            codeLenses.push(new vscode.CodeLens(range, statusCommand));

                            // Only show regenerate specs button when failed
                            const regenCommand: vscode.Command = {
                                title: '$(refresh)  Regenerate Specs',
                                command: 'tau.generateSpecs',
                                arguments: [document, i]
                            };
                            codeLenses.push(new vscode.CodeLens(range, regenCommand));
                        }
                    } else {
                        // No verification yet: show both verify and specs buttons
                        const verifyCommand: vscode.Command = {
                            title: '$(play)  Verify',
                            command: 'tau.verify',
                            arguments: [document, i]
                        };
                        codeLenses.push(new vscode.CodeLens(range, verifyCommand));

                        // Spec generation button
                        if (hasSpecs) {
                            const regenCommand: vscode.Command = {
                                title: '$(refresh)  Specs',
                                command: 'tau.generateSpecs',
                                arguments: [document, i]
                            };
                            codeLenses.push(new vscode.CodeLens(range, regenCommand));
                        } else {
                            const genCommand: vscode.Command = {
                                title: '$(sparkle)  Specs',
                                command: 'tau.generateSpecs',
                                arguments: [document, i]
                            };
                            codeLenses.push(new vscode.CodeLens(range, genCommand));
                        }
                    }
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

    public setVerifying(document: vscode.TextDocument, line: number, isVerifying: boolean): void {
        const lineKey = `${document.uri.fsPath}:${line}`;
        if (isVerifying) {
            this.verifyingLines.add(lineKey);
        } else {
            this.verifyingLines.delete(lineKey);
        }
        this.refresh();
    }

    public setVerificationStatus(document: vscode.TextDocument, line: number, verified: boolean, hash?: string, reason?: string): void {
        const lineKey = `${document.uri.fsPath}:${line}`;
        this.verificationStatus.set(lineKey, { verified, hash, reason });
        this.refresh();
    }

    public clearVerificationStatus(document: vscode.TextDocument): void {
        // Clear all verification status for this document
        const docUri = document.uri.fsPath;
        const keysToDelete: string[] = [];
        for (const key of this.verificationStatus.keys()) {
            if (key.startsWith(docUri)) {
                keysToDelete.push(key);
            }
        }
        keysToDelete.forEach(key => this.verificationStatus.delete(key));
        this.refresh();
    }
}
