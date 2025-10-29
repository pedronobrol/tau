"""
Data models for TAU API
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class VerificationStage(str, Enum):
    """Stages of verification process"""
    PARSING = "parsing"
    TRANSPILING = "transpiling"
    GENERATING_SPECS = "generating_specs"
    LLM_ROUND = "llm_round"
    PROVING = "proving"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GeneratedSpecs:
    """LLM-generated specifications"""
    requires: List[str]
    ensures: List[str]
    reasoning: str
    confidence: float  # 0.0-1.0
    suggested_invariants: List[str] = field(default_factory=list)
    suggested_variant: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requires": self.requires,
            "ensures": self.ensures,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "suggested_invariants": self.suggested_invariants,
            "suggested_variant": self.suggested_variant
        }


@dataclass
class VerificationProgress:
    """Streaming progress updates"""
    stage: VerificationStage
    message: str
    progress: float  # 0.0-1.0
    function_name: Optional[str] = None
    llm_round: Optional[int] = None
    llm_max_rounds: Optional[int] = None
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "message": self.message,
            "progress": self.progress,
            "function_name": self.function_name,
            "llm_round": self.llm_round,
            "llm_max_rounds": self.llm_max_rounds,
            "duration_seconds": self.duration_seconds
        }


@dataclass
class ValidationResult:
    """Spec validation result"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class FunctionInfo:
    """Information about a Python function"""
    name: str
    source: str
    line_number: int
    signature: str
    has_loop: bool
    parameters: List[tuple]  # [(name, type), ...]
    return_type: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "line_number": self.line_number,
            "signature": self.signature,
            "has_loop": self.has_loop,
            "parameters": self.parameters,
            "return_type": self.return_type
        }
