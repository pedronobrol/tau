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
exports.DiagnosticsManager = void 0;
const vscode = __importStar(require("vscode"));
class DiagnosticsManager {
    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('tau');
    }
    /**
     * Add a diagnostic for a verification failure
     */
    addDiagnostic(document, line, message) {
        const existingDiagnostics = this.diagnosticCollection.get(document.uri) || [];
        const diagnostics = [...existingDiagnostics];
        const diagnostic = new vscode.Diagnostic(new vscode.Range(line, 0, line, Number.MAX_VALUE), message, vscode.DiagnosticSeverity.Error);
        diagnostic.source = 'TAU';
        diagnostics.push(diagnostic);
        this.diagnosticCollection.set(document.uri, diagnostics);
    }
    /**
     * Clear diagnostics for a document
     */
    clear(document) {
        this.diagnosticCollection.delete(document.uri);
    }
    /**
     * Clear all diagnostics
     */
    clearAll() {
        this.diagnosticCollection.clear();
    }
    /**
     * Dispose the diagnostic collection
     */
    dispose() {
        this.diagnosticCollection.dispose();
    }
}
exports.DiagnosticsManager = DiagnosticsManager;
//# sourceMappingURL=diagnosticsManager.js.map