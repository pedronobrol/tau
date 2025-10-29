import * as vscode from 'vscode';
import { TauClient, GeneratedSpecs } from './tauClient';

const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export class CompletionProvider implements vscode.InlineCompletionItemProvider {
    private client: TauClient;
    private currentSpinnerInterval: NodeJS.Timeout | null = null;

    constructor(client: TauClient) {
        this.client = client;
    }

    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[] | vscode.InlineCompletionList | null> {
        const line = document.lineAt(position.line);
        const textBeforeCursor = line.text.substring(0, position.character);

        // Check if user just typed "@safe"
        if (!textBeforeCursor.trim().endsWith('@safe')) {
            return null;
        }

        // Check if there's a function definition below
        const functionLine = this.findFunctionBelow(document, position.line);
        if (!functionLine) {
            return null;
        }

        // Show ghost text hint
        const hint = "\n# Press Tab to generate @requires and @ensures specifications";
        const completionItem = new vscode.InlineCompletionItem(hint);
        completionItem.range = new vscode.Range(position, position);

        return [completionItem];
    }

    /**
     * Generate specifications for the function at cursor
     */
    async generateSpecsAtCursor(editor: vscode.TextEditor): Promise<void> {
        const document = editor.document;
        const position = editor.selection.active;

        // Find the @safe decorator line
        const safeLine = this.findSafeDecoratorAbove(document, position.line);
        if (safeLine === null) {
            vscode.window.showErrorMessage('No @safe decorator found above cursor');
            return;
        }

        // Find the function definition
        const functionLine = this.findFunctionBelow(document, safeLine);
        if (!functionLine) {
            vscode.window.showErrorMessage('No function definition found below @safe');
            return;
        }

        // Extract function source
        const functionSource = this.extractFunction(document, functionLine);
        if (!functionSource) {
            vscode.window.showErrorMessage('Could not extract function source');
            return;
        }

        // Show progress with spinner
        const insertPosition = new vscode.Position(safeLine + 1, 0);
        await this.showGeneratingSpinner(editor, insertPosition, async () => {
            // Generate specs using Claude
            const specs = await this.client.generateSpecs(functionSource);

            if (!specs) {
                vscode.window.showErrorMessage('Failed to generate specifications. Is TAU server running?');
                return;
            }

            // Format specifications
            const specsText = this.formatSpecs(specs);

            // Insert specifications
            await editor.edit(editBuilder => {
                editBuilder.insert(insertPosition, specsText);
            });

            vscode.window.showInformationMessage('✓ Specifications generated successfully!');
        });
    }

    /**
     * Show animated spinner while generating
     */
    private async showGeneratingSpinner(
        editor: vscode.TextEditor,
        position: vscode.Position,
        action: () => Promise<void>
    ): Promise<void> {
        const document = editor.document;
        let frameIndex = 0;

        // Insert placeholder lines
        await editor.edit(editBuilder => {
            const indent = this.getIndentation(document, position.line);
            editBuilder.insert(position, `${indent}@requires("...") ${SPINNER_FRAMES[0]}\n${indent}@ensures("...") ${SPINNER_FRAMES[0]}\n`);
        });

        // Start spinner animation
        const spinnerLines = [position.line, position.line + 1];
        this.currentSpinnerInterval = setInterval(async () => {
            frameIndex = (frameIndex + 1) % SPINNER_FRAMES.length;
            const frame = SPINNER_FRAMES[frameIndex];

            await editor.edit(editBuilder => {
                for (const line of spinnerLines) {
                    const lineText = document.lineAt(line).text;
                    const spinnerPos = lineText.lastIndexOf('⠋') >= 0 ? lineText.lastIndexOf('⠋') :
                                      lineText.lastIndexOf('⠙') >= 0 ? lineText.lastIndexOf('⠙') :
                                      lineText.lastIndexOf('⠹') >= 0 ? lineText.lastIndexOf('⠹') :
                                      lineText.lastIndexOf('⠸') >= 0 ? lineText.lastIndexOf('⠸') :
                                      lineText.lastIndexOf('⠼') >= 0 ? lineText.lastIndexOf('⠼') :
                                      lineText.lastIndexOf('⠴') >= 0 ? lineText.lastIndexOf('⠴') :
                                      lineText.lastIndexOf('⠦') >= 0 ? lineText.lastIndexOf('⠦') :
                                      lineText.lastIndexOf('⠧') >= 0 ? lineText.lastIndexOf('⠧') :
                                      lineText.lastIndexOf('⠇') >= 0 ? lineText.lastIndexOf('⠇') :
                                      lineText.lastIndexOf('⠏') >= 0 ? lineText.lastIndexOf('⠏') : -1;

                    if (spinnerPos >= 0) {
                        const range = new vscode.Range(
                            new vscode.Position(line, spinnerPos),
                            new vscode.Position(line, spinnerPos + 1)
                        );
                        editBuilder.replace(range, frame);
                    }
                }
            });
        }, 80); // 80ms per frame

        // Execute action
        try {
            await action();
        } finally {
            // Stop spinner
            if (this.currentSpinnerInterval) {
                clearInterval(this.currentSpinnerInterval);
                this.currentSpinnerInterval = null;
            }

            // Remove placeholder lines
            await editor.edit(editBuilder => {
                const range = new vscode.Range(
                    position,
                    new vscode.Position(position.line + 2, 0)
                );
                editBuilder.delete(range);
            });
        }
    }

    /**
     * Format generated specs as Python decorators
     */
    private formatSpecs(specs: GeneratedSpecs): string {
        const indent = '';  // Decorators should be at same level as @safe
        let result = '';

        // Add @requires
        if (specs.requires && specs.requires.length > 0) {
            for (const req of specs.requires) {
                result += `${indent}@requires("${req}")\n`;
            }
        }

        // Add @ensures
        if (specs.ensures && specs.ensures.length > 0) {
            for (const ens of specs.ensures) {
                result += `${indent}@ensures("${ens}")\n`;
            }
        }

        // Add suggested invariants as comments (user can uncomment if needed)
        if (specs.suggested_invariants && specs.suggested_invariants.length > 0) {
            result += `${indent}# Suggested loop invariants:\n`;
            for (const inv of specs.suggested_invariants) {
                result += `${indent}# @invariant("${inv}")\n`;
            }
        }

        // Add suggested variant as comment
        if (specs.suggested_variant) {
            result += `${indent}# @variant("${specs.suggested_variant}")\n`;
        }

        return result;
    }

    private findSafeDecoratorAbove(document: vscode.TextDocument, startLine: number): number | null {
        for (let i = startLine; i >= Math.max(0, startLine - 10); i--) {
            const line = document.lineAt(i).text;
            if (line.trim().startsWith('@safe')) {
                return i;
            }
        }
        return null;
    }

    private findFunctionBelow(document: vscode.TextDocument, startLine: number): number | null {
        for (let i = startLine + 1; i < Math.min(document.lineCount, startLine + 10); i++) {
            const line = document.lineAt(i).text;
            if (line.trim().startsWith('def ')) {
                return i;
            }
        }
        return null;
    }

    private extractFunction(document: vscode.TextDocument, startLine: number): string | null {
        let result = '';
        let currentLine = startLine;
        let inFunction = false;
        let baseIndent = -1;

        while (currentLine < document.lineCount) {
            const line = document.lineAt(currentLine).text;

            if (line.trim().startsWith('def ')) {
                inFunction = true;
                baseIndent = line.search(/\S/);
                result += line + '\n';
            } else if (inFunction) {
                if (line.trim() === '') {
                    result += line + '\n';
                } else {
                    const indent = line.search(/\S/);
                    if (indent <= baseIndent && line.trim() !== '') {
                        break;  // End of function
                    }
                    result += line + '\n';
                }
            }

            currentLine++;
        }

        return result.trim() || null;
    }

    private getIndentation(document: vscode.TextDocument, line: number): string {
        const lineText = document.lineAt(line).text;
        const match = lineText.match(/^(\s*)/);
        return match ? match[1] : '';
    }
}
