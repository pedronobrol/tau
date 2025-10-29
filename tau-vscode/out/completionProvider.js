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
exports.CompletionProvider = void 0;
const vscode = __importStar(require("vscode"));
class CompletionProvider {
    constructor(client) {
        this.client = client;
    }
    async provideInlineCompletionItems(_document, _position, _context, _token) {
        // Disabled - inline completions can't execute async operations
        // Use Cmd+Shift+G instead to generate specs
        return null;
    }
    /**
     * Generate specifications for the function at cursor
     */
    async generateSpecsAtCursor(editor) {
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
        // Show progress notification
        const insertPosition = new vscode.Position(safeLine + 1, 0);
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Generating specifications with Claude...',
            cancellable: false
        }, async () => {
            // Generate specs using Claude
            const specs = await this.client.generateSpecs(functionSource);
            if (!specs) {
                vscode.window.showErrorMessage('Failed to generate specifications. Is TAU server running?');
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
            vscode.window.showInformationMessage('✓ Specifications generated successfully!');
        });
    }
    /**
     * Format generated specs as Python decorators
     */
    formatSpecs(specs) {
        const indent = ''; // Decorators should be at same level as @safe
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
    findExistingSpecs(document, safeLine, functionLine) {
        let firstSpecLine = null;
        let lastSpecLine = null;
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
            return new vscode.Range(new vscode.Position(firstSpecLine, 0), new vscode.Position(lastSpecLine + 1, 0) // +1 to include the newline
            );
        }
        return null;
    }
    findSafeDecoratorAbove(document, startLine) {
        for (let i = startLine; i >= Math.max(0, startLine - 10); i--) {
            const line = document.lineAt(i).text;
            if (line.trim().startsWith('@safe')) {
                return i;
            }
        }
        return null;
    }
    findFunctionBelow(document, startLine) {
        for (let i = startLine + 1; i < Math.min(document.lineCount, startLine + 10); i++) {
            const line = document.lineAt(i).text;
            if (line.trim().startsWith('def ')) {
                return i;
            }
        }
        return null;
    }
    extractFunction(document, startLine) {
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
            }
            else if (inFunction) {
                if (line.trim() === '') {
                    result += line + '\n';
                }
                else {
                    const indent = line.search(/\S/);
                    if (indent <= baseIndent && line.trim() !== '') {
                        break; // End of function
                    }
                    result += line + '\n';
                }
            }
            currentLine++;
        }
        return result.trim() || null;
    }
}
exports.CompletionProvider = CompletionProvider;
//# sourceMappingURL=completionProvider.js.map