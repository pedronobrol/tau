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
exports.DecorationProvider = void 0;
const vscode = __importStar(require("vscode"));
const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
class DecorationProvider {
    constructor() {
        this.spinnerIntervals = new Map();
        this.currentFrame = 0;
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
    showSuccess(editor, line, hash) {
        this.clearLine(editor, line);
        const lineText = editor.document.lineAt(line);
        const endPosition = lineText.range.end;
        const hashDisplay = hash && hash.length > 0 ? hash.substring(0, 8) : 'unknown';
        const decoration = {
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
    showFailure(editor, line, hash) {
        this.clearLine(editor, line);
        const lineText = editor.document.lineAt(line);
        const endPosition = lineText.range.end;
        const hashDisplay = hash && hash.length > 0 ? `  #${hash.substring(0, 8)}` : '';
        const decoration = {
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
    showSpinner(editor, line) {
        this.clearLine(editor, line);
        const key = `${editor.document.uri.toString()}:${line}`;
        // Start spinner animation
        const interval = setInterval(() => {
            this.currentFrame = (this.currentFrame + 1) % SPINNER_FRAMES.length;
            const lineText = editor.document.lineAt(line);
            const endPosition = lineText.range.end;
            const decoration = {
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
    clearSpinner(editor, line) {
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
    clearLine(editor, line) {
        this.clearSpinner(editor, line);
        editor.setDecorations(this.successDecorationType, []);
        editor.setDecorations(this.failureDecorationType, []);
    }
    /**
     * Clear all decorations in the editor
     */
    clearAll(editor) {
        // Clear all spinners
        const keysToDelete = [];
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
    updateDecorations(_editor) {
        // This would be called when switching files
        // In a full implementation, you'd store decoration state and reapply it
    }
    /**
     * Dispose all decorations
     */
    dispose() {
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
exports.DecorationProvider = DecorationProvider;
//# sourceMappingURL=decorationProvider.js.map