"use strict";
/**
 * TAU API Client
 * Communicates with the TAU FastAPI server
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TauClient = void 0;
class TauClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    /**
     * Check if TAU server is running
     */
    async healthCheck() {
        try {
            const response = await fetch(`${this.baseUrl}/`);
            const data = await response.json();
            return data.status === 'ok';
        }
        catch (error) {
            return false;
        }
    }
    /**
     * Generate specifications for a function
     */
    async generateSpecs(functionSource, context = '', includeInvariants = true) {
        try {
            const response = await fetch(`${this.baseUrl}/api/generate-specs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    function_source: functionSource,
                    context: context,
                    include_invariants: includeInvariants
                })
            });
            const data = await response.json();
            if (data.success && data.specs) {
                return data.specs;
            }
            return null;
        }
        catch (error) {
            console.error('Error generating specs:', error);
            return null;
        }
    }
    /**
     * Verify a single function
     */
    async verifyFunction(filePath, functionName, autoGenerateInvariants = true) {
        try {
            const response = await fetch(`${this.baseUrl}/api/verify-function`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path: filePath,
                    function_name: functionName,
                    auto_generate_invariants: autoGenerateInvariants
                })
            });
            const data = await response.json();
            if (data.success && data.result) {
                return data.result;
            }
            return null;
        }
        catch (error) {
            console.error('Error verifying function:', error);
            return null;
        }
    }
    /**
     * Verify all functions in a file
     */
    async verifyFile(filePath) {
        try {
            const response = await fetch(`${this.baseUrl}/api/verify-file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: filePath })
            });
            const data = await response.json();
            if (data.success && data.result) {
                return data.result;
            }
            return null;
        }
        catch (error) {
            console.error('Error verifying file:', error);
            return null;
        }
    }
    /**
     * Verify function with WebSocket streaming for real-time progress
     */
    async verifyFunctionStream(filePath, functionName, onProgress) {
        return new Promise((resolve, reject) => {
            const wsUrl = this.baseUrl.replace('http', 'ws') + '/ws/verify';
            const ws = new WebSocket(wsUrl);
            ws.onopen = () => {
                ws.send(JSON.stringify({
                    action: 'verify_function',
                    file_path: filePath,
                    function_name: functionName
                }));
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'progress') {
                    onProgress({
                        stage: data.stage,
                        message: data.message,
                        progress: data.progress,
                        llm_round: data.llm_round,
                        llm_max_rounds: data.llm_max_rounds
                    });
                }
                else if (data.type === 'result') {
                    ws.close();
                    resolve({
                        name: functionName,
                        line: 0, // Will be filled by caller
                        verified: data.verified,
                        reason: data.reason,
                        used_llm: false,
                        duration: 0,
                        hash: data.hash
                    });
                }
                else if (data.type === 'error') {
                    ws.close();
                    reject(new Error(data.message));
                }
            };
            ws.onerror = (error) => {
                reject(error);
            };
            ws.onclose = () => {
                // Connection closed
            };
        });
    }
    /**
     * Validate specification syntax
     */
    async validateSpecs(requires, ensures, functionSource) {
        try {
            const response = await fetch(`${this.baseUrl}/api/validate-specs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    requires: requires,
                    ensures: ensures,
                    function_source: functionSource
                })
            });
            return await response.json();
        }
        catch (error) {
            console.error('Error validating specs:', error);
            return null;
        }
    }
    /**
     * Check if a proof certificate exists for a function
     */
    async checkProof(functionName, functionSource, requires = '', ensures = '', invariants = [], variant = '') {
        try {
            const response = await fetch(`${this.baseUrl}/api/proofs/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    function_name: functionName,
                    function_source: functionSource,
                    requires: requires,
                    ensures: ensures,
                    invariants: invariants,
                    variant: variant
                })
            });
            return await response.json();
        }
        catch (error) {
            console.error('Error checking proof:', error);
            return null;
        }
    }
    /**
     * Get all cached proofs for the same function body (ignoring specs).
     * Used to detect when specs change but implementation stays the same.
     */
    async getProofsByBody(functionName, functionSource) {
        try {
            const response = await fetch(`${this.baseUrl}/api/proofs/by-body`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    function_name: functionName,
                    function_source: functionSource
                    // Note: NOT including specs - we want to find by body only
                })
            });
            if (!response.ok) {
                return null;
            }
            return await response.json();
        }
        catch (error) {
            console.error('Error getting proofs by body:', error);
            return null;
        }
    }
    /**
     * Alias for getProofsByBody for backward compatibility
     */
    async findProofsByBody(functionName, functionSource) {
        return this.getProofsByBody(functionName, functionSource);
    }
    /**
     * Store a proof certificate after verification
     */
    async storeProof(functionName, functionSource, verified, requires = '', ensures = '', invariants = [], variant = '', whymlCode, leanCode, why3Output, reason, duration) {
        try {
            const response = await fetch(`${this.baseUrl}/api/proofs/store`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    function_name: functionName,
                    function_source: functionSource,
                    verified: verified,
                    requires: requires,
                    ensures: ensures,
                    invariants: invariants,
                    variant: variant,
                    whyml_code: whymlCode,
                    lean_code: leanCode,
                    why3_output: why3Output,
                    reason: reason,
                    duration: duration
                })
            });
            return await response.json();
        }
        catch (error) {
            console.error('Error storing proof:', error);
            return null;
        }
    }
    /**
     * Get proof cache statistics
     */
    async getProofStats() {
        try {
            const response = await fetch(`${this.baseUrl}/api/proofs/stats`);
            return await response.json();
        }
        catch (error) {
            console.error('Error getting proof stats:', error);
            return null;
        }
    }
}
exports.TauClient = TauClient;
//# sourceMappingURL=tauClient.js.map