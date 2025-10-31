import * as vscode from 'vscode';

const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export class DecorationProvider {
    private successDecorationType: vscode.TextEditorDecorationType;
    private failureDecorationType: vscode.TextEditorDecorationType;
    private spinnerDecorationType: vscode.TextEditorDecorationType;
    private spinnerIntervals: Map<string, NodeJS.Timeout> = new Map();
    private currentFrame: number = 0;

    constructor() {
        // Success decoration (✓ with green color)
        this.successDecorationType = vscode.window.createTextEditorDecorationType({
            after: {
                margin: '0 0 0 1em',
                color: new vscode.ThemeColor('testing.iconPassed')
            }
        });

        // Failure decoration (✗ with red color)
        this.failureDecorationType = vscode.window.createTextEditorDecorationType({
            after: {
                margin: '0 0 0 1em',
                color: new vscode.ThemeColor('testing.iconFailed')
            }
        });

        // Spinner decoration
        this.spinnerDecorationType = vscode.window.createTextEditorDecorationType({
            after: {
                margin: '0 0 0 1em',
                color: new vscode.ThemeColor('foreground')
            }
        });
    }

    /**
     * Show success decoration with hash
     */
    public showSuccess(editor: vscode.TextEditor, line: number, hash: string): void {
        this.clearLine(editor, line);

        const lineText = editor.document.lineAt(line);
        const endPosition = lineText.range.end;

        const hashDisplay = hash && hash.length > 0 ? hash.substring(0, 8) : 'unknown';
        const decoration: vscode.DecorationOptions = {
            range: new vscode.Range(endPosition, endPosition),
            renderOptions: {
                after: {
                    contentText: `  ✔  Proof passed  #${hashDisplay}`
                }
            }
        };

        editor.setDecorations(this.successDecorationType, [decoration]);
    }

    /**
     * Show failure decoration with hash
     */
    public showFailure(editor: vscode.TextEditor, line: number, hash?: string): void {
        this.clearLine(editor, line);

        const lineText = editor.document.lineAt(line);
        const endPosition = lineText.range.end;

        const hashDisplay = hash && hash.length > 0 ? `  #${hash.substring(0, 8)}` : '';
        const decoration: vscode.DecorationOptions = {
            range: new vscode.Range(endPosition, endPosition),
            renderOptions: {
                after: {
                    contentText: `  ✗  Proof failed${hashDisplay}`
                }
            }
        };

        editor.setDecorations(this.failureDecorationType, [decoration]);
    }

    /**
     * Show animated spinner
     */
    public showSpinner(editor: vscode.TextEditor, line: number): void {
        this.clearLine(editor, line);

        const key = `${editor.document.uri.toString()}:${line}`;

        // Start spinner animation
        const interval = setInterval(() => {
            this.currentFrame = (this.currentFrame + 1) % SPINNER_FRAMES.length;

            const lineText = editor.document.lineAt(line);
            const endPosition = lineText.range.end;

            const decoration: vscode.DecorationOptions = {
                range: new vscode.Range(endPosition, endPosition),
                renderOptions: {
                    after: {
                        contentText: ` ${SPINNER_FRAMES[this.currentFrame]}`
                    }
                }
            };

            editor.setDecorations(this.spinnerDecorationType, [decoration]);
        }, 80);

        this.spinnerIntervals.set(key, interval);
    }

    /**
     * Clear spinner for a specific line
     */
    public clearSpinner(editor: vscode.TextEditor, line: number): void {
        const key = `${editor.document.uri.toString()}:${line}`;
        const interval = this.spinnerIntervals.get(key);

        if (interval) {
            clearInterval(interval);
            this.spinnerIntervals.delete(key);
        }

        editor.setDecorations(this.spinnerDecorationType, []);
    }

    /**
     * Clear all decorations for a line
     */
    public clearLine(editor: vscode.TextEditor, line: number): void {
        this.clearSpinner(editor, line);
        editor.setDecorations(this.successDecorationType, []);
        editor.setDecorations(this.failureDecorationType, []);
    }

    /**
     * Clear all decorations in the editor
     */
    public clearAll(editor: vscode.TextEditor): void {
        // Clear all spinners
        const keysToDelete: string[] = [];
        for (const key of this.spinnerIntervals.keys()) {
            if (key.startsWith(editor.document.uri.toString())) {
                const interval = this.spinnerIntervals.get(key);
                if (interval) {
                    clearInterval(interval);
                }
                keysToDelete.push(key);
            }
        }
        keysToDelete.forEach(key => this.spinnerIntervals.delete(key));

        // Clear all decoration types
        editor.setDecorations(this.successDecorationType, []);
        editor.setDecorations(this.failureDecorationType, []);
        editor.setDecorations(this.spinnerDecorationType, []);
    }

    /**
     * Update all decorations for an editor
     */
    public updateDecorations(_editor: vscode.TextEditor): void {
        // This would be called when switching files
        // In a full implementation, you'd store decoration state and reapply it
    }

    /**
     * Dispose all decorations
     */
    public dispose(): void {
        // Clear all spinner intervals
        for (const interval of this.spinnerIntervals.values()) {
            clearInterval(interval);
        }
        this.spinnerIntervals.clear();

        // Dispose decoration types
        this.successDecorationType.dispose();
        this.failureDecorationType.dispose();
        this.spinnerDecorationType.dispose();
    }
}
