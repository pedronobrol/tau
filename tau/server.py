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

from tau.api import TauAPI
from tau.api_models import GeneratedSpecs, VerificationProgress, ValidationResult


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

# Global TAU API instance
tau_api: Optional[TauAPI] = None


def get_tau_api() -> TauAPI:
    """Get or create TAU API instance"""
    global tau_api
    if tau_api is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        tau_api = TauAPI(api_key=api_key)
    return tau_api


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
        api = get_tau_api()
        specs = api.generate_specs(
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
        api = get_tau_api()

        # Check file exists
        if not Path(request.file_path).exists():
            raise HTTPException(status_code=404, detail="File not found")

        result = api.verify_function(
            file_path=request.file_path,
            function_name=request.function_name,
            auto_generate_invariants=request.auto_generate_invariants
        )

        if result is None:
            return {
                "success": False,
                "error": f"Function '{request.function_name}' not found"
            }

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
            "hash": result.specification.get("whyml_hash", "") if isinstance(result.specification, dict) else ""
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
        api = get_tau_api()

        # Check file exists
        if not Path(request.file_path).exists():
            raise HTTPException(status_code=404, detail="File not found")

        summary = api.verify_file(file_path=request.file_path)

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
                "hash": result.specification.get("whyml_hash", "") if isinstance(result.specification, dict) else ""
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
        api = get_tau_api()
        result = api.validate_specs(
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
            api = get_tau_api()

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
            result = api.verify_function_stream(
                file_path=file_path,
                function_name=function_name,
                callback=lambda p: asyncio.create_task(progress_callback(p))
            )

            # Send final result
            await websocket.send_json({
                "type": "result",
                "verified": result.verified if result else False,
                "reason": result.reason if result else "Verification failed",
                "hash": result.specification.get("whyml_hash", "") if result and isinstance(result.specification, dict) else ""
            })

        elif action == "verify_file":
            api = get_tau_api()

            async def progress_callback(progress: VerificationProgress):
                await websocket.send_json({
                    "type": "progress",
                    "stage": progress.stage.value,
                    "message": progress.message,
                    "progress": progress.progress
                })

            summary = api.verify_file(
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
                    "hash": result.specification.get("whyml_hash", "") if isinstance(result.specification, dict) else ""
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
