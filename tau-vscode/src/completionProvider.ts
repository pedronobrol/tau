import * as vscode from 'vscode';
import { TauClient, GeneratedSpecs } from './tauClient';

export class CompletionProvider implements vscode.InlineCompletionItemProvider {
    private client: TauClient;

    constructor(client: TauClient) {
        this.client = client;
    }

    async provideInlineCompletionItems(
        _document: vscode.TextDocument,
        _position: vscode.Position,
        _context: vscode.InlineCompletionContext,
        _token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[] | vscode.InlineCompletionList | null> {
        // Disabled - inline completions can't execute async operations
        // Use Cmd+Shift+G instead to generate specs
        return null;
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

        // Find existing specs to delete (if regenerating)
        const existingSpecsRange = this.findExistingSpecs(document, safeLine, functionLine);

        // Generate specs (no progress notification - feedback in CodeLens only)
        const insertPosition = new vscode.Position(safeLine + 1, 0);

        // Generate specs using Claude
        const specs = await this.client.generateSpecs(functionSource);

        if (!specs) {
            return;
        }

        // Format specifications
        const specsText = this.formatSpecs(specs);

        // Delete old specs and insert new ones
        await editor.edit(editBuilder => {
            // Delete existing specs if they exist
            if (existingSpecsRange) {
                editBuilder.delete(existingSpecsRange);
            }
            // Insert new specifications
            editBuilder.insert(insertPosition, specsText);
        });
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

        // Don't show invariants/variants - TAU auto-generates them during verification!

        return result;
    }

    /**
     * Find existing @requires/@ensures specs between @safe and function definition
     * Returns a range to delete, or null if no specs exist
     */
    private findExistingSpecs(document: vscode.TextDocument, safeLine: number, functionLine: number): vscode.Range | null {
        let firstSpecLine: number | null = null;
        let lastSpecLine: number | null = null;

        // Look for @requires and @ensures between @safe and function definition
        for (let i = safeLine + 1; i < functionLine; i++) {
            const line = document.lineAt(i).text.trim();
            if (line.startsWith('@requires') || line.startsWith('@ensures')) {
                if (firstSpecLine === null) {
                    firstSpecLine = i;
                }
                lastSpecLine = i;
            }
        }

        // If we found specs, return a range that includes all lines from first to last spec
        if (firstSpecLine !== null && lastSpecLine !== null) {
            return new vscode.Range(
                new vscode.Position(firstSpecLine, 0),
                new vscode.Position(lastSpecLine + 1, 0)  // +1 to include the newline
            );
        }

        return null;
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
}
