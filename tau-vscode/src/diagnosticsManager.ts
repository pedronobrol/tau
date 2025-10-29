import * as vscode from 'vscode';

export class DiagnosticsManager {
    private diagnosticCollection: vscode.DiagnosticCollection;

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('tau');
    }

    /**
     * Add a diagnostic for a verification failure
     */
    public addDiagnostic(document: vscode.TextDocument, line: number, message: string): void {
        const existingDiagnostics = this.diagnosticCollection.get(document.uri) || [];
        const diagnostics = [...existingDiagnostics];

        const diagnostic = new vscode.Diagnostic(
            new vscode.Range(line, 0, line, Number.MAX_VALUE),
            message,
            vscode.DiagnosticSeverity.Error
        );

        diagnostic.source = 'TAU';

        diagnostics.push(diagnostic);
        this.diagnosticCollection.set(document.uri, diagnostics);
    }

    /**
     * Clear diagnostics for a document
     */
    public clear(document: vscode.TextDocument): void {
        this.diagnosticCollection.delete(document.uri);
    }

    /**
     * Clear all diagnostics
     */
    public clearAll(): void {
        this.diagnosticCollection.clear();
    }

    /**
     * Dispose the diagnostic collection
     */
    public dispose(): void {
        this.diagnosticCollection.dispose();
    }
}
