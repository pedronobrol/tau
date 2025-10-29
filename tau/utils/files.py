"""
File I/O utilities
"""

import os
import uuid
from typing import Optional, Tuple

OUTPUT_DIR = "./why_out"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_artifacts(whyml_source: str,
                  lean_source: str,
                  base_name: Optional[str] = None) -> Tuple[str, str]:
    """
    Save WhyML and Lean files to disk.

    Args:
        whyml_source: WhyML source code
        lean_source: Lean source code
        base_name: Optional base filename

    Returns:
        (why_file_path, lean_file_path)
    """
    base = base_name or f"bundle_{uuid.uuid4().hex[:8]}"
    why_path = os.path.join(OUTPUT_DIR, f"{base}.why")
    lean_path = os.path.join(OUTPUT_DIR, f"{base}.lean")

    with open(why_path, "w", encoding="utf-8") as f:
        f.write(whyml_source)

    with open(lean_path, "w", encoding="utf-8") as f:
        f.write(lean_source)

    return why_path, lean_path
