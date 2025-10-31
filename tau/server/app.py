#!/usr/bin/env python3
"""
TAU FastAPI Server
Provides REST API for specification generation and verification
"""
import os
import json
import asyncio
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tau.server.client import TauClient
from tau.server.models import GeneratedSpecs, VerificationProgress, ValidationResult
from tau.proofs import ProofCertificateManager, compute_function_hash


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateSpecsRequest(BaseModel):
    function_source: str
    context: Optional[str] = ""
    include_invariants: bool = True


class GenerateSpecsResponse(BaseModel):
    success: bool
    specs: Optional[dict] = None
    error: Optional[str] = None


class VerifyFunctionRequest(BaseModel):
    file_path: str
    function_name: str
    auto_generate_invariants: bool = True


class VerifyFileRequest(BaseModel):
    file_path: str


class VerificationResponse(BaseModel):
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None


class ValidateSpecsRequest(BaseModel):
    requires: str
    ensures: str
    function_source: str


class ValidateSpecsResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class HealthResponse(BaseModel):
    status: str
    version: str
    anthropic_available: bool


class CheckProofRequest(BaseModel):
    function_name: str
    function_source: str
    requires: Optional[str] = ""
    ensures: Optional[str] = ""
    invariants: Optional[List[str]] = []
    variant: Optional[str] = ""


class CheckProofResponse(BaseModel):
    found: bool
    hash: Optional[str] = None
    verified: Optional[bool] = None
    created_at: Optional[str] = None
    reason: Optional[str] = None
    duration: Optional[float] = None
    specs: Optional[dict] = None


class StoreProofRequest(BaseModel):
    function_name: str
    function_source: str
    requires: Optional[str] = ""
    ensures: Optional[str] = ""
    invariants: Optional[List[str]] = []
    variant: Optional[str] = ""
    verified: bool
    whyml_code: Optional[str] = None
    lean_code: Optional[str] = None
    why3_output: Optional[str] = None
    reason: Optional[str] = None
    duration: Optional[float] = None


class StoreProofResponse(BaseModel):
    success: bool
    hash: str
    error: Optional[str] = None


class ProofStatsResponse(BaseModel):
    total_entries: int
    cache_hits: int
    cache_misses: int
    cache_size_bytes: int
    last_cleanup: str


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="TAU API",
    description="Formal verification API for Python with Claude AI",
    version="0.1.0"
)

# Enable CORS for VS Code extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global TAU client instance
tau_client: Optional[TauClient] = None
proof_manager: Optional[ProofCertificateManager] = None


def get_tau_client() -> TauClient:
    """Get or create TAU client instance"""
    global tau_client
    if tau_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        tau_client = TauClient(api_key=api_key)
    return tau_client


def get_proof_manager() -> ProofCertificateManager:
    """Get or create proof certificate manager instance"""
    global proof_manager
    if proof_manager is None:
        proof_manager = ProofCertificateManager()
    return proof_manager


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    return {
        "status": "ok",
        "version": "0.1.0",
        "anthropic_available": bool(api_key)
    }


@app.post("/api/generate-specs", response_model=GenerateSpecsResponse)
async def generate_specs(request: GenerateSpecsRequest):
    """
    Generate formal specifications for a Python function using Claude.

    Example:
        POST /api/generate-specs
        {
            "function_source": "def count_to(n: int) -> int:\\n    ...",
            "context": "# Module context",
            "include_invariants": true
        }
    """
    try:
        client = get_tau_client()
        specs = client.generate_specs(
            function_source=request.function_source,
            context=request.context,
            include_invariants=request.include_invariants
        )

        if specs is None:
            return {
                "success": False,
                "error": "Spec generation failed. Check ANTHROPIC_API_KEY is set."
            }

        return {
            "success": True,
            "specs": specs.to_dict()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/verify-function", response_model=VerificationResponse)
async def verify_function(request: VerifyFunctionRequest):
    """
    Verify a single function in a file.

    Example:
        POST /api/verify-function
        {
            "file_path": "/path/to/file.py",
            "function_name": "count_to",
            "auto_generate_invariants": true
        }
    """
    try:
        client = get_tau_client()

        # Check file exists
        if not Path(request.file_path).exists():
            raise HTTPException(status_code=404, detail="File not found")

        result = client.verify_function(
            file_path=request.file_path,
            function_name=request.function_name,
            auto_generate_invariants=request.auto_generate_invariants
        )

        if result is None:
            return {
                "success": False,
                "error": f"Function '{request.function_name}' not found"
            }

        # Automatically store proof after verification
        print(f"[ProofStore DEBUG] result={result}, has_hash={result.hash if result else 'N/A'}")
        if result and result.hash:
            try:
                manager = get_proof_manager()

                # Read proof artifacts if available
                whyml_code = None
                lean_code = None

                print(f"[ProofStore DEBUG] whyml_file={result.whyml_file}, lean_file={result.lean_file}")

                if result.whyml_file and Path(result.whyml_file).exists():
                    whyml_code = Path(result.whyml_file).read_text()
                    print(f"[ProofStore DEBUG] Loaded whyml_code: {len(whyml_code)} chars")

                if result.lean_file and Path(result.lean_file).exists():
                    lean_code = Path(result.lean_file).read_text()
                    print(f"[ProofStore DEBUG] Loaded lean_code: {len(lean_code)} chars")

                # Prepare function info for storage
                print(f"[ProofStore DEBUG] python_source length: {len(result.python_source) if result.python_source else 0}")
                func_info = {
                    "name": result.name,
                    "source": result.python_source,
                    "requires": result.specification.get("requires", ""),
                    "ensures": result.specification.get("ensures", ""),
                    "invariants": result.specification.get("invariants", []),
                    "variant": result.specification.get("variant", "")
                }

                print(f"[ProofStore DEBUG] About to call store_proof for {result.name}")
                # Store proof certificate
                stored_hash = manager.store_proof(
                    func_info=func_info,
                    verified=result.verified,
                    whyml_code=whyml_code,
                    lean_code=lean_code,
                    why3_output=None,
                    reason=result.reason,
                    duration=result.duration
                )

                print(f"[ProofStore] Stored proof for {result.name} - hash: {stored_hash[:8]}, verified: {result.verified}")
            except Exception as e:
                import traceback
                print(f"[ProofStore] Failed to store proof: {e}")
                print(f"[ProofStore] Traceback: {traceback.format_exc()}")

        # Convert result to dict
        result_dict = {
            "name": result.name,
            "line": result.lineno,
            "verified": result.verified,
            "reason": result.reason,
            "used_llm": result.used_llm,
            "bug_type": result.bug_type,
            "duration": result.duration,
            "specification": result.specification,
            "hash": result.hash or ""
        }

        return {
            "success": True,
            "result": result_dict
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/verify-file", response_model=VerificationResponse)
async def verify_file(request: VerifyFileRequest):
    """
    Verify all @safe functions in a file.

    Example:
        POST /api/verify-file
        {
            "file_path": "/path/to/file.py"
        }
    """
    try:
        client = get_tau_client()

        # Check file exists
        if not Path(request.file_path).exists():
            raise HTTPException(status_code=404, detail="File not found")

        summary = client.verify_file(file_path=request.file_path)

        # Convert results to dict
        results = []
        for result in summary.results:
            results.append({
                "name": result.name,
                "line": result.lineno,
                "verified": result.verified,
                "reason": result.reason,
                "used_llm": result.used_llm,
                "bug_type": result.bug_type,
                "duration": result.duration,
                "hash": result.hash or ""
            })

        return {
            "success": True,
            "result": {
                "total": summary.total,
                "passed": summary.passed,
                "failed": summary.failed,
                "results": results
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/validate-specs", response_model=ValidateSpecsResponse)
async def validate_specs(request: ValidateSpecsRequest):
    """
    Validate WhyML specification syntax.

    Example:
        POST /api/validate-specs
        {
            "requires": "n >= 0",
            "ensures": "result = n",
            "function_source": "def count_to(n: int) -> int: ..."
        }
    """
    try:
        client = get_tau_client()
        result = client.validate_specs(
            requires=request.requires,
            ensures=request.ensures,
            function_source=request.function_source
        )

        return {
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings
        }

    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": []
        }


@app.post("/api/proofs/check", response_model=CheckProofResponse)
async def check_proof(request: CheckProofRequest):
    """
    Check if a proof certificate exists for a function.

    Example:
        POST /api/proofs/check
        {
            "function_name": "count_to",
            "function_source": "def count_to(n: int) -> int: ...",
            "requires": "n >= 0",
            "ensures": "result = n"
        }
    """
    try:
        manager = get_proof_manager()

        func_info = {
            "name": request.function_name,
            "source": request.function_source,
            "requires": request.requires,
            "ensures": request.ensures,
            "invariants": request.invariants or [],
            "variant": request.variant
        }

        certificate = manager.lookup_proof(func_info)

        if certificate:
            return {
                "found": True,
                "hash": certificate["hash"],
                "verified": certificate["verified"],
                "created_at": certificate["timestamp"],
                "reason": certificate.get("reason"),
                "duration": certificate.get("duration"),
                "specs": certificate.get("specs")
            }
        else:
            return {"found": False}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proofs/by-body")
async def find_proofs_by_body(request: CheckProofRequest):
    """
    Find all cached proofs for the same function body (ignoring specs).

    Used to detect when specs change but implementation stays the same.
    Returns list of proofs with different specifications for the same body.

    Example:
        POST /api/proofs/by-body
        {
            "function_name": "count_to",
            "function_source": "def count_to(n: int) -> int: ..."
        }

    Response:
        {
            "found": true,
            "proofs": [
                {
                    "hash": "abc123...",
                    "verified": true,
                    "specs": {
                        "requires": "n >= 0",
                        "ensures": "result = n"
                    },
                    "timestamp": "2025-10-30T..."
                }
            ]
        }
    """
    try:
        manager = get_proof_manager()

        func_info = {
            "name": request.function_name,
            "source": request.function_source,
            # Note: NOT including specs - we want to find by body only
        }

        proofs = manager.find_proofs_by_body(func_info)

        return {
            "found": len(proofs) > 0,
            "count": len(proofs),
            "proofs": [
                {
                    "hash": proof["hash"],
                    "body_hash": proof["body_hash"],
                    "function_name": proof["function_name"],
                    "verified": proof["verified"],
                    "specs": proof["specs"],
                    "timestamp": proof["timestamp"],
                    "reason": proof.get("reason")
                }
                for proof in proofs
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proofs/store", response_model=StoreProofResponse)
async def store_proof(request: StoreProofRequest):
    """
    Store a proof certificate after verification.

    Example:
        POST /api/proofs/store
        {
            "function_name": "count_to",
            "function_source": "def count_to(n: int) -> int: ...",
            "requires": "n >= 0",
            "ensures": "result = n",
            "verified": true,
            "whyml_code": "...",
            "lean_code": "...",
            "why3_output": "..."
        }
    """
    try:
        manager = get_proof_manager()

        func_info = {
            "name": request.function_name,
            "source": request.function_source,
            "requires": request.requires,
            "ensures": request.ensures,
            "invariants": request.invariants or [],
            "variant": request.variant
        }

        func_hash = manager.store_proof(
            func_info=func_info,
            verified=request.verified,
            whyml_code=request.whyml_code,
            lean_code=request.lean_code,
            why3_output=request.why3_output,
            reason=request.reason,
            duration=request.duration
        )

        return {
            "success": True,
            "hash": func_hash
        }

    except Exception as e:
        return {
            "success": False,
            "hash": "",
            "error": str(e)
        }


@app.get("/api/proofs/stats", response_model=ProofStatsResponse)
async def get_proof_stats():
    """
    Get proof certificate cache statistics.

    Example:
        GET /api/proofs/stats
    """
    try:
        manager = get_proof_manager()
        stats = manager.get_stats()

        return {
            "total_entries": stats["total_entries"],
            "cache_hits": stats["cache_hits"],
            "cache_misses": stats["cache_misses"],
            "cache_size_bytes": stats["cache_size_bytes"],
            "last_cleanup": stats["last_cleanup"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/proofs/clear")
async def clear_proofs():
    """
    Clear all proof certificates (dangerous!).

    Example:
        DELETE /api/proofs/clear
    """
    try:
        manager = get_proof_manager()
        manager.clear_all()

        return {"success": True, "message": "All proofs cleared"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/proofs/list")
async def list_proofs(verified_only: bool = False):
    """
    List all proof certificates.

    Example:
        GET /api/proofs/list?verified_only=true
    """
    try:
        manager = get_proof_manager()
        proofs = manager.list_proofs(verified_only=verified_only)

        return {"success": True, "proofs": proofs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket for Streaming Progress
# ============================================================================

@app.websocket("/ws/verify")
async def websocket_verify(websocket: WebSocket):
    """
    WebSocket endpoint for real-time verification progress.

    Send:
        {
            "action": "verify_function",
            "file_path": "/path/to/file.py",
            "function_name": "count_to"
        }

    Receive:
        {
            "type": "progress",
            "stage": "parsing",
            "message": "Parsing file...",
            "progress": 0.1
        }
        ...
        {
            "type": "result",
            "verified": true,
            "reason": "Proof succeeded"
        }
    """
    await websocket.accept()

    try:
        # Receive request
        data = await websocket.receive_text()
        request = json.loads(data)

        action = request.get("action")
        file_path = request.get("file_path")
        function_name = request.get("function_name")

        if action == "verify_function":
            client = get_tau_client()

            # Progress callback
            async def progress_callback(progress: VerificationProgress):
                await websocket.send_json({
                    "type": "progress",
                    "stage": progress.stage.value,
                    "message": progress.message,
                    "progress": progress.progress,
                    "llm_round": progress.llm_round,
                    "llm_max_rounds": progress.llm_max_rounds
                })

            # Verify with streaming
            result = client.verify_function_stream(
                file_path=file_path,
                function_name=function_name,
                callback=lambda p: asyncio.create_task(progress_callback(p))
            )

            # Automatically store proof after verification
            print(f"[ProofStore DEBUG] result={result}, has_hash={result.hash if result else 'N/A'}")
            if result and result.hash:
                try:
                    manager = get_proof_manager()

                    # Read proof artifacts if available
                    whyml_code = None
                    lean_code = None

                    print(f"[ProofStore DEBUG] whyml_file={result.whyml_file}, lean_file={result.lean_file}")

                    if result.whyml_file and Path(result.whyml_file).exists():
                        whyml_code = Path(result.whyml_file).read_text()
                        print(f"[ProofStore DEBUG] Loaded whyml_code: {len(whyml_code)} chars")

                    if result.lean_file and Path(result.lean_file).exists():
                        lean_code = Path(result.lean_file).read_text()
                        print(f"[ProofStore DEBUG] Loaded lean_code: {len(lean_code)} chars")

                    # Prepare function info for storage
                    print(f"[ProofStore DEBUG] python_source length: {len(result.python_source) if result.python_source else 0}")
                    func_info = {
                        "name": result.name,
                        "source": result.python_source,
                        "requires": result.specification.get("requires", ""),
                        "ensures": result.specification.get("ensures", ""),
                        "invariants": result.specification.get("invariants", []),
                        "variant": result.specification.get("variant", "")
                    }

                    print(f"[ProofStore DEBUG] About to call store_proof for {result.name}")
                    # Store proof certificate
                    stored_hash = manager.store_proof(
                        func_info=func_info,
                        verified=result.verified,
                        whyml_code=whyml_code,
                        lean_code=lean_code,
                        why3_output=None,  # Not captured in current flow
                        reason=result.reason,
                        duration=result.duration
                    )

                    print(f"[ProofStore] Stored proof for {result.name} - hash: {stored_hash[:8]}, verified: {result.verified}")
                except Exception as e:
                    import traceback
                    print(f"[ProofStore] Failed to store proof: {e}")
                    print(f"[ProofStore] Traceback: {traceback.format_exc()}")

            # Send final result
            await websocket.send_json({
                "type": "result",
                "verified": result.verified if result else False,
                "reason": result.reason if result else "Verification failed",
                "hash": result.hash or "" if result else ""
            })

        elif action == "verify_file":
            client = get_tau_client()

            async def progress_callback(progress: VerificationProgress):
                await websocket.send_json({
                    "type": "progress",
                    "stage": progress.stage.value,
                    "message": progress.message,
                    "progress": progress.progress
                })

            summary = client.verify_file(
                file_path=file_path,
                callback=lambda p: asyncio.create_task(progress_callback(p))
            )

            # Send results
            results = []
            for result in summary.results:
                results.append({
                    "name": result.name,
                    "line": result.lineno,
                    "verified": result.verified,
                    "reason": result.reason,
                    "hash": result.hash or ""
                })

            await websocket.send_json({
                "type": "result",
                "total": summary.total,
                "passed": summary.passed,
                "failed": summary.failed,
                "results": results
            })

        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown action: {action}"
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("TAU API Server")
    print("=" * 60)
    print("Starting server on http://localhost:8000")
    print("API docs: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws/verify")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
