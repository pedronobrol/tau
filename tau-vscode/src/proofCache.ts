import * as crypto from 'crypto';

/**
 * Proof result stored in local cache
 */
export interface CachedProof {
    hash: string;
    functionName: string;
    verified: boolean;
    reason?: string;
    timestamp: number;
}

/**
 * Function information for hash computation
 */
export interface FunctionInfo {
    name: string;
    source: string;
    requires: string;
    ensures: string;
    invariants: string[];
    variant: string;
}

/**
 * Local proof cache manager for VS Code extension
 * Stores verification results in memory, keyed by function hash
 */
export class ProofCacheManager {
    private cache: Map<string, CachedProof> = new Map();

    /**
     * Compute SHA-256 hash of function and specifications
     * This must match the Python implementation in tau/proofs/hasher.py
     * Uses the simple fallback algorithm: hash(name + source + specs)
     */
    public computeFunctionHash(funcInfo: FunctionInfo): string {
        // Match Python's str() representation for lists
        const invariantsStr = `[${(funcInfo.invariants || []).map(inv => `'${inv}'`).join(', ')}]`;
        const variantStr = funcInfo.variant || '';

        // Combine all parts in the exact same order as Python's compute_function_hash_simple
        const combined =
            funcInfo.name +
            funcInfo.source +
            (funcInfo.requires || '') +
            (funcInfo.ensures || '') +
            invariantsStr +
            variantStr;

        // Compute SHA-256 hash
        return crypto.createHash('sha256').update(combined, 'utf-8').digest('hex');
    }

    /**
     * Compute SHA-256 hash of ONLY function body (no specs)
     * Used to detect when same function has different specifications
     */
    public computeBodyHash(funcInfo: FunctionInfo): string {
        // Hash only: name + source (NO specs)
        const combined = funcInfo.name + funcInfo.source;

        // Compute SHA-256 hash
        return crypto.createHash('sha256').update(combined, 'utf-8').digest('hex');
    }

    /**
     * Store a proof result in the cache
     */
    public store(funcInfo: FunctionInfo, verified: boolean, reason?: string): string {
        const hash = this.computeFunctionHash(funcInfo);

        this.cache.set(hash, {
            hash,
            functionName: funcInfo.name,
            verified,
            reason,
            timestamp: Date.now()
        });

        console.log(`[ProofCache] Stored proof for ${funcInfo.name} - hash: ${hash.substring(0, 8)}, verified: ${verified}`);
        return hash;
    }

    /**
     * Look up a proof result by function info
     */
    public lookup(funcInfo: FunctionInfo): CachedProof | null {
        const hash = this.computeFunctionHash(funcInfo);
        const cached = this.cache.get(hash);

        if (cached) {
            console.log(`[ProofCache] Cache HIT for ${funcInfo.name} - hash: ${hash.substring(0, 8)}`);
        } else {
            console.log(`[ProofCache] Cache MISS for ${funcInfo.name} - hash: ${hash.substring(0, 8)}`);
        }

        return cached || null;
    }

    /**
     * Check if a proof exists for the given function
     */
    public has(funcInfo: FunctionInfo): boolean {
        const hash = this.computeFunctionHash(funcInfo);
        return this.cache.has(hash);
    }

    /**
     * Clear all cached proofs
     */
    public clear(): void {
        this.cache.clear();
        console.log('[ProofCache] Cache cleared');
    }

    /**
     * Get cache statistics
     */
    public getStats(): { totalEntries: number; verified: number; failed: number } {
        const entries = Array.from(this.cache.values());
        return {
            totalEntries: entries.length,
            verified: entries.filter(e => e.verified).length,
            failed: entries.filter(e => !e.verified).length
        };
    }

    /**
     * Remove entries older than the specified age (in milliseconds)
     */
    public cleanOld(maxAge: number): number {
        const now = Date.now();
        let removed = 0;

        for (const [hash, proof] of this.cache.entries()) {
            if (now - proof.timestamp > maxAge) {
                this.cache.delete(hash);
                removed++;
            }
        }

        if (removed > 0) {
            console.log(`[ProofCache] Cleaned ${removed} old entries`);
        }

        return removed;
    }
}
