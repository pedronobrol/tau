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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const completionProvider_1 = require("./completionProvider");
const codeLensProvider_1 = require("./codeLensProvider");
const decorationProvider_1 = require("./decorationProvider");
const tauClient_1 = require("./tauClient");
const diagnosticsManager_1 = require("./diagnosticsManager");
const proofCache_1 = require("./proofCache");
let decorationProvider;
let diagnosticsManager;
let tauClient;
let completionProvider;
let proofCache;
let reactiveUpdateTimeout;
function activate(context) {
    console.log('TAU Formal Verification extension activated');
    // Get configuration
    const config = vscode.workspace.getConfiguration('tau');
    const serverUrl = config.get('serverUrl', 'http://localhost:8000');
    // Initialize services
    tauClient = new tauClient_1.TauClient(serverUrl);
    decorationProvider = new decorationProvider_1.DecorationProvider();
    diagnosticsManager = new diagnosticsManager_1.DiagnosticsManager();
    proofCache = new proofCache_1.ProofCacheManager();
    // Initialize completion provider
    completionProvider = new completionProvider_1.CompletionProvider(tauClient);
    context.subscriptions.push(vscode.languages.registerInlineCompletionItemProvider({ language: 'python' }, completionProvider));
    // Check if server is running
    tauClient.healthCheck().then(isRunning => {
        if (!isRunning) {
            vscode.window.showWarningMessage('TAU server is not running. Start it with: python3 tau/server.py', 'Start Server').then((choice) => {
                if (choice === 'Start Server') {
                    const terminal = vscode.window.createTerminal('TAU Server');
                    terminal.sendText('cd ' + vscode.workspace.workspaceFolders?.[0].uri.fsPath);
                    terminal.sendText('python3 tau/server.py');
                    terminal.show();
                }
            });
        }
        else {
            vscode.window.showInformationMessage('TAU server is running');
        }
    });
    // Register CodeLens provider for verification triggers
    const codeLensProvider = new codeLensProvider_1.CodeLensProvider();
    context.subscriptions.push(vscode.languages.registerCodeLensProvider({ language: 'python' }, codeLensProvider));
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('tau.generateSpecs', async (_document, line) => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }
        // If line is provided (clicked from CodeLens), use it. Otherwise find current cursor line
        const targetLine = line !== undefined ? line : editor.selection.active.line;
        // Show loading state in CodeLens
        codeLensProvider.setGenerating(editor.document, targetLine, true);
        try {
            await completionProvider.generateSpecsAtCursor(editor);
        }
        finally {
            // Hide loading state
            codeLensProvider.setGenerating(editor.document, targetLine, false);
        }
    }));
    context.subscriptions.push(vscode.commands.registerCommand('tau.verify', async (document, line) => {
        await verifyFunction(document, line, codeLensProvider);
    }));
    context.subscriptions.push(vscode.commands.registerCommand('tau.verifyFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }
        await verifyFile(editor.document, codeLensProvider);
    }));
    context.subscriptions.push(vscode.commands.registerCommand('tau.viewCachedSpecs', async (document, line, cachedInfo) => {
        await viewCachedSpecs(document, line, cachedInfo, codeLensProvider);
    }));
    context.subscriptions.push(vscode.commands.registerCommand('tau.clearCache', async () => {
        proofCache.clear();
        codeLensProvider.clearVerificationStatus(vscode.window.activeTextEditor?.document);
        vscode.window.showInformationMessage('TAU local cache cleared');
    }));
    context.subscriptions.push(vscode.commands.registerCommand('tau.showProofDetails', async (document, line) => {
        await showProofDetailsPanel(document, line, codeLensProvider, context);
    }));
    // Auto-verify on save if enabled
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('tau');
        const autoVerify = config.get('autoVerifyOnSave', false);
        if (autoVerify && document.languageId === 'python') {
            await verifyFile(document, codeLensProvider);
        }
    }));
    // Reactively update verification status when document content changes
    context.subscriptions.push(vscode.workspace.onDidChangeTextDocument((event) => {
        // Proper debounce: clear previous timeout and create new one
        if (reactiveUpdateTimeout) {
            clearTimeout(reactiveUpdateTimeout);
        }
        reactiveUpdateTimeout = setTimeout(() => {
            reactivelyUpdateVerificationStatus(event.document, codeLensProvider);
        }, 500); // Wait 500ms after last edit
    }));
    // Auto-check cached proofs when file is opened
    context.subscriptions.push(vscode.workspace.onDidOpenTextDocument(async (document) => {
        if (document.languageId === 'python') {
            await autoCheckCachedProofs(document, codeLensProvider);
        }
    }));
    // Also check cached proofs for currently open documents
    if (vscode.window.activeTextEditor?.document.languageId === 'python') {
        autoCheckCachedProofs(vscode.window.activeTextEditor.document, codeLensProvider);
    }
}
/**
 * Reactively update verification status based on function hash changes
 * When a function is edited, check if the new hash matches a cached proof
 */
function reactivelyUpdateVerificationStatus(document, codeLensProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document || document.languageId !== 'python') {
        return;
    }
    // Get display mode setting
    const config = vscode.workspace.getConfiguration('tau');
    const displayMode = config.get('statusDisplayMode', 'codelens');
    // Find all @safe decorators and check their current hash
    const text = document.getText();
    const lines = text.split('\n');
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line === '@safe' || line === '@safe_auto') {
            const isAutoMode = line === '@safe_auto';
            // Extract function info
            const funcInfo = extractFunctionInfo(document, i);
            if (!funcInfo) {
                continue;
            }
            // Compute hash to check what we're looking for
            const currentHash = proofCache.computeFunctionHash(funcInfo);
            console.log(`[Reactive] Checking ${funcInfo.name} (${isAutoMode ? '@safe_auto' : '@safe'}) - computed hash: ${currentHash.substring(0, 8)}`);
            console.log(`[Reactive]   Specs: requires="${funcInfo.requires}", ensures="${funcInfo.ensures}"`);
            // Check local cache for this function's current hash
            const cachedProof = proofCache.lookup(funcInfo);
            if (cachedProof) {
                // Found in local cache - show status immediately!
                console.log(`[Reactive] Cache HIT for ${funcInfo.name} at line ${i} - hash: ${cachedProof.hash.substring(0, 8)}`);
                if (cachedProof.verified) {
                    if (displayMode === 'inline') {
                        decorationProvider.showSuccess(editor, i, cachedProof.hash);
                    }
                    else {
                        codeLensProvider.setVerificationStatus(document, i, true, cachedProof.hash);
                    }
                }
                else {
                    if (displayMode === 'inline') {
                        decorationProvider.showFailure(editor, i, cachedProof.hash);
                    }
                    else {
                        codeLensProvider.setVerificationStatus(document, i, false, cachedProof.hash, cachedProof.reason);
                    }
                }
            }
            else {
                // Not in exact cache
                console.log(`[Reactive] Exact cache MISS for ${funcInfo.name} at line ${i}`);
                // For @safe_auto: automatically trigger verification
                if (isAutoMode) {
                    console.log(`[Reactive] Auto-triggering verification for @safe_auto function ${funcInfo.name}`);
                    // Auto-verify (don't await, let it run async)
                    verifyFunction(document, i, codeLensProvider).catch(err => {
                        console.error(`Auto-verification failed for ${funcInfo.name}:`, err);
                    });
                }
                else {
                    // For @safe: check if body matches any cached proof
                    checkCachedSpecsByBody(document, i, funcInfo, codeLensProvider).catch(err => {
                        console.error(`Error checking cached specs by body:`, err);
                    });
                }
                // Clear verification status (no exact match yet)
                codeLensProvider.clearVerificationStatusAtLine(document, i);
                if (displayMode === 'inline') {
                    decorationProvider.clearAll(editor);
                }
            }
        }
    }
}
/**
 * Check if cached specs are available for the same function body (ignoring specs)
 * Shows "💡 Cached specs available" CodeLens if verified proofs found
 */
async function checkCachedSpecsByBody(document, line, funcInfo, codeLensProvider) {
    try {
        const result = await tauClient.getProofsByBody(funcInfo.name, funcInfo.source);
        if (result && result.found && result.proofs.length > 0) {
            // Filter for verified proofs only
            const verifiedProofs = result.proofs.filter(p => p.verified);
            if (verifiedProofs.length > 0) {
                // Use the most recent verified proof
                const mostRecent = verifiedProofs[0];
                console.log(`[Reactive] Found ${verifiedProofs.length} cached specs for ${funcInfo.name}`);
                // Show "💡 Cached specs available" CodeLens
                codeLensProvider.setCachedSpecsAvailable(document, line, {
                    count: verifiedProofs.length,
                    specs: mostRecent.specs,
                    hash: mostRecent.hash,
                    verified: true
                });
            }
            else {
                // No verified proofs - clear cached specs indicator
                codeLensProvider.clearCachedSpecs(document, line);
            }
        }
        else {
            // No proofs found - clear cached specs indicator
            codeLensProvider.clearCachedSpecs(document, line);
        }
    }
    catch (error) {
        console.error(`Error checking cached specs by body:`, error);
        // Don't throw - just clear indicator
        codeLensProvider.clearCachedSpecs(document, line);
    }
}
/**
 * Auto-check cached proofs for all @safe functions in a document
 */
async function autoCheckCachedProofs(document, codeLensProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }
    // Get display mode setting
    const config = vscode.workspace.getConfiguration('tau');
    const displayMode = config.get('statusDisplayMode', 'codelens');
    // Find all @safe decorators in the document
    const text = document.getText();
    const lines = text.split('\n');
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line === '@safe' || line === '@safe_auto') {
            // Extract function info
            const funcInfo = extractFunctionInfo(document, i);
            if (!funcInfo) {
                continue;
            }
            // Check local cache first
            const localCached = proofCache.lookup(funcInfo);
            if (localCached) {
                console.log(`[Auto-load] Local cache HIT for ${funcInfo.name} - hash: ${localCached.hash.substring(0, 8)}`);
                // Show cached status
                if (localCached.verified) {
                    if (displayMode === 'inline') {
                        decorationProvider.showSuccess(editor, i, localCached.hash);
                    }
                    else {
                        codeLensProvider.setVerificationStatus(document, i, true, localCached.hash);
                    }
                }
                else {
                    if (displayMode === 'inline') {
                        decorationProvider.showFailure(editor, i, localCached.hash);
                    }
                    else {
                        codeLensProvider.setVerificationStatus(document, i, false, localCached.hash, localCached.reason);
                    }
                }
                continue; // Done with this function
            }
            // Check server cache if not in local cache
            try {
                const proofCheck = await tauClient.checkProof(funcInfo.name, funcInfo.source, funcInfo.requires, funcInfo.ensures, funcInfo.invariants, funcInfo.variant);
                if (proofCheck && proofCheck.found) {
                    console.log(`[Auto-load] Server cache HIT for ${funcInfo.name} - hash: ${proofCheck.hash}`);
                    // Store in local cache
                    proofCache.store(funcInfo, proofCheck.verified === true, proofCheck.reason);
                    // Show cached status
                    if (proofCheck.verified) {
                        if (displayMode === 'inline') {
                            decorationProvider.showSuccess(editor, i, proofCheck.hash || '');
                        }
                        else {
                            codeLensProvider.setVerificationStatus(document, i, true, proofCheck.hash);
                        }
                    }
                    else {
                        if (displayMode === 'inline') {
                            decorationProvider.showFailure(editor, i, proofCheck.hash);
                        }
                        else {
                            codeLensProvider.setVerificationStatus(document, i, false, proofCheck.hash, proofCheck.reason);
                        }
                    }
                }
            }
            catch (error) {
                console.error(`Error checking cached proof for ${funcInfo.name}:`, error);
                // Continue to next function
            }
        }
    }
}
async function verifyFunction(document, line, codeLensProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }
    // Extract function information
    const funcInfo = extractFunctionInfo(document, line);
    if (!funcInfo) {
        vscode.window.showErrorMessage('Could not find function at this line');
        return;
    }
    // Get display mode setting
    const config = vscode.workspace.getConfiguration('tau');
    const displayMode = config.get('statusDisplayMode', 'codelens');
    // Check local cache first (fastest)
    const localCached = proofCache.lookup(funcInfo);
    if (localCached) {
        console.log(`[Local Cache] HIT for ${funcInfo.name} - hash: ${localCached.hash.substring(0, 8)}`);
        if (localCached.verified) {
            if (displayMode === 'inline') {
                decorationProvider.showSuccess(editor, line, localCached.hash);
            }
            else {
                codeLensProvider.setVerificationStatus(document, line, true, localCached.hash);
            }
        }
        else {
            if (displayMode === 'inline') {
                decorationProvider.showFailure(editor, line, localCached.hash);
            }
            else {
                codeLensProvider.setVerificationStatus(document, line, false, localCached.hash, localCached.reason);
            }
            if (localCached.reason) {
                diagnosticsManager.addDiagnostic(document, line, localCached.reason);
            }
        }
        return; // Done - used local cache!
    }
    // Check server cache (if not in local cache)
    try {
        let proofCheck = await tauClient.checkProof(funcInfo.name, funcInfo.source, funcInfo.requires, funcInfo.ensures, funcInfo.invariants, funcInfo.variant);
        // For @safe_auto functions with empty specs, try finding by body hash if exact match fails
        if (!proofCheck?.found && !funcInfo.requires && !funcInfo.ensures) {
            console.log(`[Server Cache] Exact match MISS for @safe_auto ${funcInfo.name}, trying body-hash lookup...`);
            const bodyProofs = await tauClient.findProofsByBody(funcInfo.name, funcInfo.source);
            if (bodyProofs && bodyProofs.found && bodyProofs.proofs && bodyProofs.proofs.length > 0) {
                // Use the first (most recent) proof found
                const bodyProof = bodyProofs.proofs[0];
                console.log(`[Server Cache] Body-hash HIT for ${funcInfo.name} - hash: ${bodyProof.hash}`);
                // Convert body proof to proofCheck format
                proofCheck = {
                    found: true,
                    hash: bodyProof.hash,
                    verified: bodyProof.verified,
                    created_at: bodyProof.timestamp,
                    reason: bodyProof.reason,
                    duration: undefined, // Duration not included in CachedProofInfo yet
                    specs: bodyProof.specs
                };
            }
        }
        if (proofCheck && proofCheck.found) {
            // Found server cached proof - show it immediately and store in local cache!
            console.log(`[Server Cache] HIT for ${funcInfo.name} - hash: ${proofCheck.hash}`);
            // Store in local cache for faster future lookups
            proofCache.store(funcInfo, proofCheck.verified === true, proofCheck.reason);
            if (proofCheck.verified) {
                if (displayMode === 'inline') {
                    decorationProvider.showSuccess(editor, line, proofCheck.hash || '');
                }
                else {
                    codeLensProvider.setVerificationStatus(document, line, true, proofCheck.hash, undefined, {
                        functionName: funcInfo.name,
                        duration: proofCheck.duration, // Use original verification duration
                        usedLlm: false,
                        bugType: undefined,
                        specs: proofCheck.specs || {
                            requires: funcInfo.requires || '',
                            ensures: funcInfo.ensures || '',
                            invariants: funcInfo.invariants || [],
                            variant: funcInfo.variant
                        }
                    });
                }
            }
            else {
                if (displayMode === 'inline') {
                    decorationProvider.showFailure(editor, line, proofCheck.hash);
                }
                else {
                    codeLensProvider.setVerificationStatus(document, line, false, proofCheck.hash, proofCheck.reason, {
                        functionName: funcInfo.name,
                        duration: proofCheck.duration, // Use original verification duration
                        usedLlm: false,
                        bugType: undefined,
                        specs: proofCheck.specs || {
                            requires: funcInfo.requires || '',
                            ensures: funcInfo.ensures || '',
                            invariants: funcInfo.invariants || [],
                            variant: funcInfo.variant
                        }
                    });
                }
                if (proofCheck.reason) {
                    diagnosticsManager.addDiagnostic(document, line, proofCheck.reason);
                }
            }
            return; // Done - used server cached proof!
        }
        console.log(`Cache MISS for ${funcInfo.name} - running verification...`);
    }
    catch (error) {
        console.error('Error checking proof cache:', error);
        // Continue to verification even if cache check fails
    }
    // No cached proof - show verifying state and run verification
    codeLensProvider.setVerifying(document, line, true);
    try {
        const result = await tauClient.verifyFunctionStream(document.uri.fsPath, funcInfo.name, (_progressUpdate) => {
            // Silent - no progress notification
        });
        // Store result in local cache
        if (result) {
            proofCache.store(funcInfo, result.verified, result.reason);
        }
        // Update status based on display mode
        if (result && result.verified) {
            if (displayMode === 'inline') {
                decorationProvider.showSuccess(editor, line, result.hash || '');
            }
            else {
                codeLensProvider.setVerificationStatus(document, line, true, result.hash, undefined, {
                    functionName: funcInfo.name,
                    duration: result.duration,
                    usedLlm: result.used_llm,
                    bugType: result.bug_type,
                    specs: {
                        requires: funcInfo.requires || '',
                        ensures: funcInfo.ensures || '',
                        invariants: funcInfo.invariants || [],
                        variant: funcInfo.variant
                    }
                });
            }
        }
        else {
            const reason = result?.reason || 'Verification failed';
            const hash = result?.hash;
            if (displayMode === 'inline') {
                decorationProvider.showFailure(editor, line, hash);
            }
            else {
                codeLensProvider.setVerificationStatus(document, line, false, hash, reason, {
                    functionName: funcInfo.name,
                    duration: result?.duration,
                    usedLlm: result?.used_llm,
                    bugType: result?.bug_type,
                    specs: {
                        requires: funcInfo.requires || '',
                        ensures: funcInfo.ensures || '',
                        invariants: funcInfo.invariants || [],
                        variant: funcInfo.variant
                    }
                });
            }
            // Add diagnostics
            if (result) {
                diagnosticsManager.addDiagnostic(document, line, reason);
            }
        }
    }
    catch (error) {
        const reason = `Error: ${error}`;
        if (displayMode === 'inline') {
            decorationProvider.showFailure(editor, line);
        }
        else {
            codeLensProvider.setVerificationStatus(document, line, false, undefined, reason);
        }
    }
    finally {
        // Clear verifying state
        codeLensProvider.setVerifying(document, line, false);
    }
}
async function verifyFile(document, codeLensProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }
    // Get display mode setting
    const config = vscode.workspace.getConfiguration('tau');
    const displayMode = config.get('statusDisplayMode', 'codelens');
    // Verify without progress notification - feedback in CodeLens/inline
    try {
        const summary = await tauClient.verifyFile(document.uri.fsPath);
        if (!summary) {
            return;
        }
        // Clear existing diagnostics
        diagnosticsManager.clear(document);
        // Update status and diagnostics based on display mode
        for (const result of summary.results) {
            const line = result.line;
            // Extract function info to store in cache
            const funcInfo = extractFunctionInfo(document, line);
            if (funcInfo) {
                proofCache.store(funcInfo, result.verified, result.reason);
            }
            if (result.verified) {
                if (displayMode === 'inline') {
                    decorationProvider.showSuccess(editor, line, result.hash || '');
                }
                else {
                    codeLensProvider.setVerificationStatus(document, line, true, result.hash);
                }
            }
            else {
                const reason = result.reason || 'Verification failed';
                if (displayMode === 'inline') {
                    decorationProvider.showFailure(editor, line, result.hash);
                }
                else {
                    codeLensProvider.setVerificationStatus(document, line, false, result.hash, reason);
                }
                diagnosticsManager.addDiagnostic(document, line, reason);
            }
        }
    }
    catch (error) {
        // Silent - errors shown in CodeLens/inline and diagnostics
    }
}
function findFunctionNameAtLine(document, line) {
    // Search forward from @safe to find the function definition (skipping decorators)
    for (let i = line; i < Math.min(document.lineCount, line + 20); i++) {
        const lineText = document.lineAt(i).text;
        const match = lineText.match(/def\s+(\w+)\s*\(/);
        if (match) {
            return match[1];
        }
    }
    return null;
}
/**
 * Extract function source and specifications from document
 */
function extractFunctionInfo(document, line) {
    const functionName = findFunctionNameAtLine(document, line);
    if (!functionName) {
        return null;
    }
    // Find the function definition line
    let defLine = -1;
    for (let i = line; i < Math.min(document.lineCount, line + 20); i++) {
        const lineText = document.lineAt(i).text;
        if (lineText.match(/def\s+\w+\s*\(/)) {
            defLine = i;
            break;
        }
    }
    if (defLine === -1) {
        return null;
    }
    // Extract function source (def line + body)
    let endLine = defLine + 1;
    const baseIndent = document.lineAt(defLine).text.search(/\S/);
    while (endLine < document.lineCount) {
        const lineText = document.lineAt(endLine).text;
        const trimmed = lineText.trim();
        // Skip empty lines and comments
        if (trimmed === '' || trimmed.startsWith('#')) {
            endLine++;
            continue;
        }
        // Check if we've left the function body
        const indent = lineText.search(/\S/);
        if (indent !== -1 && indent <= baseIndent) {
            break;
        }
        endLine++;
    }
    const functionSource = document.getText(new vscode.Range(defLine, 0, endLine, 0));
    // Extract specifications from comments or decorators between @safe and def
    let requires = '';
    let ensures = '';
    const invariants = [];
    let variant = '';
    for (let i = line + 1; i < defLine; i++) {
        const lineText = document.lineAt(i).text.trim();
        // Comment-style: # @requires: ...
        if (lineText.startsWith('# @requires:')) {
            requires = lineText.substring('# @requires:'.length).trim();
        }
        else if (lineText.startsWith('# @ensures:')) {
            ensures = lineText.substring('# @ensures:'.length).trim();
        }
        else if (lineText.startsWith('# @invariant:')) {
            invariants.push(lineText.substring('# @invariant:'.length).trim());
        }
        else if (lineText.startsWith('# @variant:')) {
            variant = lineText.substring('# @variant:'.length).trim();
        }
        // Decorator-style: @requires("...") or @requires('...')
        else if (lineText.startsWith('@requires(')) {
            const match = lineText.match(/@requires\(["'](.+?)["']\)/);
            if (match) {
                requires = match[1];
            }
        }
        else if (lineText.startsWith('@ensures(')) {
            const match = lineText.match(/@ensures\(["'](.+?)["']\)/);
            if (match) {
                ensures = match[1];
            }
        }
        else if (lineText.startsWith('@invariant(')) {
            const match = lineText.match(/@invariant\(["'](.+?)["']\)/);
            if (match) {
                invariants.push(match[1]);
            }
        }
        else if (lineText.startsWith('@variant(')) {
            const match = lineText.match(/@variant\(["'](.+?)["']\)/);
            if (match) {
                variant = match[1];
            }
        }
    }
    return {
        name: functionName,
        source: functionSource,
        requires: requires,
        ensures: ensures,
        invariants: invariants,
        variant: variant
    };
}
/**
 * Show cached specs and allow user to replace current specs
 */
async function viewCachedSpecs(document, line, cachedInfo, codeLensProvider) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }
    // Extract current function info
    const currentFuncInfo = extractFunctionInfo(document, line);
    if (!currentFuncInfo) {
        vscode.window.showErrorMessage('Could not extract function info');
        return;
    }
    // Format specs for display
    const cachedSpecs = cachedInfo.specs;
    const currentSpecs = {
        requires: currentFuncInfo.requires,
        ensures: currentFuncInfo.ensures,
        invariants: currentFuncInfo.invariants,
        variant: currentFuncInfo.variant
    };
    // Create comparison message
    const items = [
        {
            label: '$(check) Use cached specs',
            description: `Verified proof #${cachedInfo.hash.substring(0, 8)}`,
            detail: formatSpecs(cachedSpecs),
            action: 'use'
        },
        {
            label: '$(x) Keep current specs',
            description: 'Continue editing',
            detail: formatSpecs(currentSpecs),
            action: 'keep'
        }
    ];
    const choice = await vscode.window.showQuickPick(items, {
        title: `Cached specs available for ${currentFuncInfo.name} (${cachedInfo.count} found)`,
        placeHolder: 'Choose which specs to use'
    });
    if (choice?.action === 'use') {
        // Replace current specs with cached specs
        await replaceFunctionSpecs(document, line, cachedSpecs);
        // Clear cached specs indicator (since we just applied them)
        codeLensProvider.clearCachedSpecs(document, line);
        vscode.window.showInformationMessage('Applied cached specs');
    }
}
/**
 * Format specs for display in QuickPick
 */
function formatSpecs(specs) {
    const parts = [];
    if (specs.requires) {
        parts.push(`@requires: ${specs.requires}`);
    }
    if (specs.ensures) {
        parts.push(`@ensures: ${specs.ensures}`);
    }
    if (specs.invariants && specs.invariants.length > 0) {
        specs.invariants.forEach((inv) => {
            parts.push(`@invariant: ${inv}`);
        });
    }
    if (specs.variant) {
        parts.push(`@variant: ${specs.variant}`);
    }
    return parts.length > 0 ? parts.join(' | ') : '(no specs)';
}
/**
 * Replace function specifications in the document
 */
async function replaceFunctionSpecs(document, safeLine, newSpecs) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
        return;
    }
    // Find the function definition line
    let defLine = -1;
    for (let i = safeLine; i < Math.min(document.lineCount, safeLine + 20); i++) {
        const lineText = document.lineAt(i).text;
        if (lineText.match(/def\s+\w+\s*\(/)) {
            defLine = i;
            break;
        }
    }
    if (defLine === -1) {
        vscode.window.showErrorMessage('Could not find function definition');
        return;
    }
    // Find existing spec lines (between @safe and def)
    const specStartLine = safeLine + 1;
    const specEndLine = defLine;
    // Detect existing style by checking what's already there
    let useDecoratorStyle = false;
    for (let i = specStartLine; i < specEndLine; i++) {
        const lineText = document.lineAt(i).text.trim();
        if (lineText.startsWith('@requires(') || lineText.startsWith('@ensures(') ||
            lineText.startsWith('@invariant(') || lineText.startsWith('@variant(')) {
            useDecoratorStyle = true;
            break;
        }
    }
    // Build new spec lines in the detected style
    const indent = document.lineAt(safeLine).text.match(/^(\s*)/)?.[1] || '';
    const newSpecLines = [];
    if (useDecoratorStyle) {
        // Decorator style: @requires("...")
        if (newSpecs.requires) {
            newSpecLines.push(`${indent}@requires("${newSpecs.requires}")`);
        }
        if (newSpecs.ensures) {
            newSpecLines.push(`${indent}@ensures("${newSpecs.ensures}")`);
        }
        if (newSpecs.invariants && newSpecs.invariants.length > 0) {
            newSpecs.invariants.forEach(inv => {
                newSpecLines.push(`${indent}@invariant("${inv}")`);
            });
        }
        if (newSpecs.variant) {
            newSpecLines.push(`${indent}@variant("${newSpecs.variant}")`);
        }
    }
    else {
        // Comment style: # @requires: ...
        if (newSpecs.requires) {
            newSpecLines.push(`${indent}# @requires: ${newSpecs.requires}`);
        }
        if (newSpecs.ensures) {
            newSpecLines.push(`${indent}# @ensures: ${newSpecs.ensures}`);
        }
        if (newSpecs.invariants && newSpecs.invariants.length > 0) {
            newSpecs.invariants.forEach(inv => {
                newSpecLines.push(`${indent}# @invariant: ${inv}`);
            });
        }
        if (newSpecs.variant) {
            newSpecLines.push(`${indent}# @variant: ${newSpecs.variant}`);
        }
    }
    // Replace the spec section
    await editor.edit(editBuilder => {
        const range = new vscode.Range(new vscode.Position(specStartLine, 0), new vscode.Position(specEndLine, 0));
        editBuilder.replace(range, newSpecLines.join('\n') + '\n');
    });
}
/**
 * Show proof details in a webview panel
 */
async function showProofDetailsPanel(document, line, codeLensProvider, context) {
    const status = codeLensProvider.getVerificationStatus(document, line);
    if (!status) {
        vscode.window.showWarningMessage('No proof information available');
        return;
    }
    // Extract function info
    const funcInfo = extractFunctionInfo(document, line);
    // Create and show a new webview panel
    const panel = vscode.window.createWebviewPanel('tauProofDetails', `Proof Details: ${status.functionName || funcInfo?.name || 'Function'}`, vscode.ViewColumn.Beside, {
        enableScripts: true,
        retainContextWhenHidden: true
    });
    // Set the webview HTML content
    panel.webview.html = getProofDetailsHTML(status, funcInfo, document, line);
}
/**
 * Generate HTML for proof details webview
 */
function getProofDetailsHTML(status, funcInfo, document, line) {
    const verified = status.verified;
    const statusColor = verified ? '#4caf50' : '#f44336';
    const statusIcon = verified ? '✓' : '✗';
    const statusText = verified ? 'PASSED' : 'FAILED';
    const hash = status.hash || 'N/A';
    const shortHash = hash.substring(0, 16);
    // Format duration: show ms for very fast operations, otherwise seconds
    let duration = 'N/A';
    if (status.duration !== undefined && status.duration !== null) {
        if (status.duration < 0.01) {
            duration = `${(status.duration * 1000).toFixed(0)}ms`;
        }
        else {
            duration = `${(status.duration).toFixed(2)}s`;
        }
    }
    const timestampDate = status.timestamp ? new Date(status.timestamp) : null;
    const timestampStr = timestampDate ? timestampDate.toLocaleString() : 'N/A';
    const timestampTime = timestampDate ? timestampDate.toLocaleTimeString() : 'N/A';
    // Build specs section
    let specsHTML = '';
    if (status.specs) {
        specsHTML = `
            <div class="section">
                <div class="section-title">Specifications</div>
                ${status.specs.requires ? `
                <div class="spec-item">
                    <div class="spec-label">Preconditions (@requires)</div>
                    <div class="spec-value"><code>${escapeHtml(status.specs.requires)}</code></div>
                </div>
                ` : ''}
                ${status.specs.ensures ? `
                <div class="spec-item">
                    <div class="spec-label">Postconditions (@ensures)</div>
                    <div class="spec-value"><code>${escapeHtml(status.specs.ensures)}</code></div>
                </div>
                ` : ''}
                ${status.specs.invariants && status.specs.invariants.length > 0 ? `
                <div class="spec-item">
                    <div class="spec-label">Loop Invariants</div>
                    <div class="spec-value">
                        ${status.specs.invariants.map((inv) => `<code>${escapeHtml(inv)}</code>`).join('<br>')}
                    </div>
                </div>
                ` : ''}
                ${status.specs.variant ? `
                <div class="spec-item">
                    <div class="spec-label">Termination Variant</div>
                    <div class="spec-value"><code>${escapeHtml(status.specs.variant)}</code></div>
                </div>
                ` : ''}
            </div>
        `;
    }
    // Build function code section
    let codeHTML = '';
    if (funcInfo && funcInfo.source) {
        codeHTML = `
            <div class="section">
                <div class="section-title">Function Source</div>
                <pre class="code-block"><code class="language-python">${escapeHtml(funcInfo.source)}</code></pre>
            </div>
        `;
    }
    // Build reason section for failures
    let reasonHTML = '';
    if (!verified && status.reason) {
        reasonHTML = `
            <div class="section failure-reason">
                <div class="section-title">Failure Reason</div>
                <div class="reason-content">${escapeHtml(status.reason)}</div>
                ${status.bugType ? `<div class="bug-type">⚠ Bug Type: ${escapeHtml(status.bugType)}</div>` : ''}
            </div>
        `;
    }
    return `<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Proof Details</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                padding: 0;
                color: var(--vscode-foreground);
                background-color: var(--vscode-editor-background);
                line-height: 1.6;
            }
            .container {
                max-width: 100%;
                margin: 0;
                padding: 12px;
            }
            .header {
                background: var(--vscode-editor-background);
                border: 1px solid var(--vscode-panel-border);
                border-left: 2px solid ${statusColor};
                border-radius: 4px;
                padding: 12px;
                margin-bottom: 12px;
            }
            .status-row {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }
            .status-badge {
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background-color: ${statusColor}10;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                font-weight: 600;
                color: ${statusColor};
                flex-shrink: 0;
            }
            .status-info h1 {
                font-size: 14px;
                font-weight: 600;
                color: var(--vscode-foreground);
                margin-bottom: 2px;
                font-family: 'Courier New', Courier, monospace;
            }
            .status-text {
                font-size: 10px;
                color: var(--vscode-descriptionForeground);
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .metadata-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 6px;
                margin-top: 10px;
            }
            .metadata-card {
                background-color: var(--vscode-sideBar-background);
                padding: 6px 8px;
                border-radius: 3px;
                border: 1px solid var(--vscode-panel-border);
            }
            .metadata-label {
                font-size: 9px;
                text-transform: uppercase;
                letter-spacing: 0.3px;
                color: var(--vscode-descriptionForeground);
                margin-bottom: 2px;
            }
            .metadata-value {
                font-size: 11px;
                font-weight: 500;
                color: var(--vscode-foreground);
            }
            .hash-value {
                font-family: 'Courier New', Courier, monospace;
                font-size: 10px;
                color: var(--vscode-textLink-foreground);
                word-break: break-all;
            }
            .section {
                background-color: var(--vscode-editor-background);
                border: 1px solid var(--vscode-panel-border);
                border-radius: 4px;
                padding: 12px;
                margin-bottom: 12px;
            }
            .section-title {
                font-size: 12px;
                font-weight: 600;
                color: var(--vscode-foreground);
                margin-bottom: 10px;
                padding-bottom: 6px;
                border-bottom: 1px solid var(--vscode-panel-border);
            }
            .spec-item {
                margin-bottom: 10px;
            }
            .spec-item:last-child {
                margin-bottom: 0;
            }
            .spec-label {
                font-size: 11px;
                font-weight: 600;
                color: var(--vscode-descriptionForeground);
                margin-bottom: 4px;
            }
            .spec-value {
                padding: 8px 10px;
                background-color: transparent;
                border-radius: 3px;
                border: 1px solid var(--vscode-panel-border);
                border-left: 2px solid var(--vscode-textLink-foreground);
                font-family: 'Courier New', Courier, monospace;
                font-size: 11px;
                line-height: 1.5;
                overflow-x: auto;
            }
            .spec-value code {
                color: var(--vscode-foreground);
                background-color: transparent !important;
            }
            .code-block {
                background-color: transparent !important;
                border-radius: 3px;
                padding: 12px;
                overflow-x: auto;
                font-size: 11px !important;
                line-height: 1.6;
                border: 1px solid var(--vscode-panel-border);
            }
            .code-block code {
                color: var(--vscode-foreground);
                background-color: transparent !important;
                font-family: 'Courier New', Courier, monospace;
            }
            pre {
                margin: 0 !important;
                white-space: pre;
                background-color: transparent !important;
            }
            pre[class*="language-"] {
                background-color: transparent !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            code[class*="language-"] {
                background-color: transparent !important;
                font-size: 11px !important;
            }
            .failure-reason {
                border-color: var(--vscode-inputValidation-errorBorder);
                background: var(--vscode-editor-background);
            }
            .failure-reason .section-title {
                color: var(--vscode-errorForeground);
            }
            .reason-content {
                padding: 10px 12px;
                background-color: var(--vscode-inputValidation-errorBackground);
                border-radius: 3px;
                border-left: 2px solid var(--vscode-inputValidation-errorBorder);
                color: var(--vscode-inputValidation-errorForeground);
                font-family: 'Courier New', Courier, monospace;
                font-size: 11px;
                line-height: 1.5;
                white-space: pre-wrap;
            }
            .bug-type {
                margin-top: 8px;
                padding: 4px 8px;
                background-color: var(--vscode-inputValidation-errorBackground);
                border: 1px solid var(--vscode-inputValidation-errorBorder);
                color: var(--vscode-errorForeground);
                border-radius: 3px;
                display: inline-block;
                font-size: 10px;
                font-weight: 500;
            }
            .badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background-color: var(--vscode-badge-background);
                color: var(--vscode-badge-foreground);
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="status-row">
                    <div class="status-badge">${statusIcon}</div>
                    <div class="status-info">
                        <h1>${escapeHtml(status.functionName || funcInfo?.name || 'Unknown Function')}</h1>
                        <div class="status-text">${statusText}</div>
                    </div>
                </div>

                <div class="metadata-grid">
                    <div class="metadata-card">
                        <div class="metadata-label">Duration</div>
                        <div class="metadata-value">${duration}</div>
                    </div>
                    <div class="metadata-card">
                        <div class="metadata-label">Timestamp</div>
                        <div class="metadata-value">${timestampTime}</div>
                    </div>
                    <div class="metadata-card">
                        <div class="metadata-label">Line Number</div>
                        <div class="metadata-value">${line + 1}</div>
                    </div>
                    ${status.usedLlm ? `
                    <div class="metadata-card">
                        <div class="metadata-label">Verification</div>
                        <div class="metadata-value">
                            <span class="badge">🤖 LLM Assisted</span>
                        </div>
                    </div>
                    ` : ''}
                    <div class="metadata-card" style="grid-column: 1 / -1;">
                        <div class="metadata-label">Proof Hash</div>
                        <div class="hash-value">${shortHash}</div>
                    </div>
                </div>
            </div>

            ${reasonHTML}
            ${specsHTML}
            ${codeHTML}
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    </body>
    </html>`;
}
/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}
function deactivate() {
    if (diagnosticsManager) {
        diagnosticsManager.dispose();
    }
    if (decorationProvider) {
        decorationProvider.dispose();
    }
}
//# sourceMappingURL=extension.js.map