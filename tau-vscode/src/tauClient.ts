/**
 * TAU API Client
 * Communicates with the TAU FastAPI server
 */

export interface GeneratedSpecs {
    requires: string[];
    ensures: string[];
    reasoning: string;
    confidence: number;
    suggested_invariants: string[];
    suggested_variant?: string;
}

export interface VerificationResult {
    name: string;
    line: number;
    verified: boolean;
    reason: string;
    used_llm: boolean;
    bug_type?: string;
    duration: number;
    hash?: string;
}

export interface VerificationProgress {
    stage: string;
    message: string;
    progress: number;
    llm_round?: number;
    llm_max_rounds?: number;
}

export interface CachedProofInfo {
    hash: string;
    body_hash: string;
    function_name: string;
    verified: boolean;
    specs: {
        requires: string;
        ensures: string;
        invariants: string[];
        variant: string;
    };
    timestamp: string;
    reason?: string;
}

export class TauClient {
    private baseUrl: string;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    /**
     * Check if TAU server is running
     */
    async healthCheck(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/`);
            const data = await response.json() as any;
            return data.status === 'ok';
        } catch (error) {
            return false;
        }
    }

    /**
     * Generate specifications for a function
     */
    async generateSpecs(
        functionSource: string,
        context: string = '',
        includeInvariants: boolean = true
    ): Promise<GeneratedSpecs | null> {
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

            const data = await response.json() as any;
            if (data.success && data.specs) {
                return data.specs;
            }
            return null;
        } catch (error) {
            console.error('Error generating specs:', error);
            return null;
        }
    }

    /**
     * Verify a single function
     */
    async verifyFunction(
        filePath: string,
        functionName: string,
        autoGenerateInvariants: boolean = true
    ): Promise<VerificationResult | null> {
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

            const data = await response.json() as any;
            if (data.success && data.result) {
                return data.result;
            }
            return null;
        } catch (error) {
            console.error('Error verifying function:', error);
            return null;
        }
    }

    /**
     * Verify all functions in a file
     */
    async verifyFile(filePath: string): Promise<{ total: number, passed: number, failed: number, results: VerificationResult[] } | null> {
        try {
            const response = await fetch(`${this.baseUrl}/api/verify-file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: filePath })
            });

            const data = await response.json() as any;
            if (data.success && data.result) {
                return data.result;
            }
            return null;
        } catch (error) {
            console.error('Error verifying file:', error);
            return null;
        }
    }

    /**
     * Verify function with WebSocket streaming for real-time progress
     */
    async verifyFunctionStream(
        filePath: string,
        functionName: string,
        onProgress: (progress: VerificationProgress) => void
    ): Promise<VerificationResult | null> {
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
                } else if (data.type === 'result') {
                    ws.close();
                    resolve({
                        name: functionName,
                        line: 0,  // Will be filled by caller
                        verified: data.verified,
                        reason: data.reason,
                        used_llm: false,
                        duration: 0,
                        hash: data.hash
                    });
                } else if (data.type === 'error') {
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
    async validateSpecs(
        requires: string,
        ensures: string,
        functionSource: string
    ): Promise<{ valid: boolean, errors: string[], warnings: string[] } | null> {
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

            return await response.json() as any;
        } catch (error) {
            console.error('Error validating specs:', error);
            return null;
        }
    }

    /**
     * Check if a proof certificate exists for a function
     */
    async checkProof(
        functionName: string,
        functionSource: string,
        requires: string = '',
        ensures: string = '',
        invariants: string[] = [],
        variant: string = ''
    ): Promise<{ found: boolean, hash?: string, verified?: boolean, created_at?: string, reason?: string, duration?: number, specs?: { requires: string, ensures: string, invariants: string[], variant: string } } | null> {
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

            return await response.json() as any;
        } catch (error) {
            console.error('Error checking proof:', error);
            return null;
        }
    }

    /**
     * Get all cached proofs for the same function body (ignoring specs).
     * Used to detect when specs change but implementation stays the same.
     */
    async getProofsByBody(
        functionName: string,
        functionSource: string
    ): Promise<{ found: boolean, count: number, proofs: CachedProofInfo[] } | null> {
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

            return await response.json() as any;
        } catch (error) {
            console.error('Error getting proofs by body:', error);
            return null;
        }
    }

    /**
     * Alias for getProofsByBody for backward compatibility
     */
    async findProofsByBody(
        functionName: string,
        functionSource: string
    ): Promise<{ found: boolean, count: number, proofs: CachedProofInfo[] } | null> {
        return this.getProofsByBody(functionName, functionSource);
    }

    /**
     * Store a proof certificate after verification
     */
    async storeProof(
        functionName: string,
        functionSource: string,
        verified: boolean,
        requires: string = '',
        ensures: string = '',
        invariants: string[] = [],
        variant: string = '',
        whymlCode?: string,
        leanCode?: string,
        why3Output?: string,
        reason?: string,
        duration?: number
    ): Promise<{ success: boolean, hash: string, error?: string } | null> {
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

            return await response.json() as any;
        } catch (error) {
            console.error('Error storing proof:', error);
            return null;
        }
    }

    /**
     * Get proof cache statistics
     */
    async getProofStats(): Promise<{ total_entries: number, cache_hits: number, cache_misses: number, cache_size_bytes: number, last_cleanup: string } | null> {
        try {
            const response = await fetch(`${this.baseUrl}/api/proofs/stats`);
            return await response.json() as any;
        } catch (error) {
            console.error('Error getting proof stats:', error);
            return null;
        }
    }
}
