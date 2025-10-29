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
exports.CodeLensProvider = void 0;
const vscode = __importStar(require("vscode"));
class CodeLensProvider {
    constructor() {
        this._onDidChangeCodeLenses = new vscode.EventEmitter();
        this.onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;
        this.generatingLines = new Set(); // Track which lines are generating (format: "filepath:line")
        this.verifyingLines = new Set(); // Track which lines are verifying (format: "filepath:line")
        this.verificationStatus = new Map(); // Store verification results (format: "filepath:line")
    }
    provideCodeLenses(document, _token) {
        const codeLenses = [];
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
                    const loadingCommand = {
                        title: '$(sync~spin)  Generating specs...',
                        command: '', // No command while loading
                        arguments: []
                    };
                    codeLenses.push(new vscode.CodeLens(range, loadingCommand));
                }
                // If verifying, only show loading indicator
                else if (isVerifying) {
                    const loadingCommand = {
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
                            // Passed: only show hash with check icon, no buttons
                            const statusCommand = {
                                title: `$(pass)  #${status.hash?.substring(0, 8) || ''}`,
                                command: '', // Status is not clickable
                                arguments: []
                            };
                            codeLenses.push(new vscode.CodeLens(range, statusCommand));
                        }
                        else {
                            // Failed: show simple x with hash (hover shows reason)
                            const reason = status.reason || 'Verification failed';
                            const statusCommand = {
                                title: `$(x)  Failed`,
                                command: '', // Status is not clickable
                                arguments: [],
                                tooltip: reason
                            };
                            codeLenses.push(new vscode.CodeLens(range, statusCommand));
                            // Only show regenerate specs button when failed
                            const regenCommand = {
                                title: '$(refresh)  Regenerate Specs',
                                command: 'tau.generateSpecs',
                                arguments: [document, i]
                            };
                            codeLenses.push(new vscode.CodeLens(range, regenCommand));
                        }
                    }
                    else {
                        // No verification yet: show both verify and specs buttons
                        const verifyCommand = {
                            title: '$(play)  Verify',
                            command: 'tau.verify',
                            arguments: [document, i]
                        };
                        codeLenses.push(new vscode.CodeLens(range, verifyCommand));
                        // Spec generation button
                        if (hasSpecs) {
                            const regenCommand = {
                                title: '$(refresh)  Specs',
                                command: 'tau.generateSpecs',
                                arguments: [document, i]
                            };
                            codeLenses.push(new vscode.CodeLens(range, regenCommand));
                        }
                        else {
                            const genCommand = {
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
    resolveCodeLens(codeLens, _token) {
        return codeLens;
    }
    refresh() {
        this._onDidChangeCodeLenses.fire();
    }
    hasSpecsBelow(document, safeLine) {
        // Check if @requires or @ensures exist below @safe
        for (let i = safeLine + 1; i < Math.min(document.lineCount, safeLine + 10); i++) {
            const line = document.lineAt(i).text.trim();
            if (line.startsWith('def ')) {
                break; // Reached function definition
            }
            if (line.startsWith('@requires') || line.startsWith('@ensures')) {
                return true;
            }
        }
        return false;
    }
    setGenerating(document, line, isGenerating) {
        const lineKey = `${document.uri.fsPath}:${line}`;
        if (isGenerating) {
            this.generatingLines.add(lineKey);
        }
        else {
            this.generatingLines.delete(lineKey);
        }
        this.refresh();
    }
    setVerifying(document, line, isVerifying) {
        const lineKey = `${document.uri.fsPath}:${line}`;
        if (isVerifying) {
            this.verifyingLines.add(lineKey);
        }
        else {
            this.verifyingLines.delete(lineKey);
        }
        this.refresh();
    }
    setVerificationStatus(document, line, verified, hash, reason) {
        const lineKey = `${document.uri.fsPath}:${line}`;
        this.verificationStatus.set(lineKey, { verified, hash, reason });
        this.refresh();
    }
    clearVerificationStatus(document) {
        // Clear all verification status for this document
        const docUri = document.uri.fsPath;
        const keysToDelete = [];
        for (const key of this.verificationStatus.keys()) {
            if (key.startsWith(docUri)) {
                keysToDelete.push(key);
            }
        }
        keysToDelete.forEach(key => this.verificationStatus.delete(key));
        this.refresh();
    }
}
exports.CodeLensProvider = CodeLensProvider;
//# sourceMappingURL=codeLensProvider.js.map