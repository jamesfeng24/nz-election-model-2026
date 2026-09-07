"""Check local provenance file integrity without fetching or transforming data.

Run: python3 scripts/validate/source_files.py
The TypeScript SourceRegistrySchema remains the complete metadata validator.
This complementary offline check verifies file existence, containment and bytes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath


def verify_source_files(root: Path, registry: dict) -> None:
    """Fail on missing or changed raw bytes; never create or modify files."""
    if registry.get("schemaVersion") != 1 or not isinstance(registry.get("sources"), list):
        raise ValueError("Expected a version-1 source registry")
    raw_root = (root / "data" / "raw").resolve()
    seen = set()
    for source in registry["sources"]:
        source_id = source["id"]
        if source_id in seen:
            raise ValueError(f"Duplicate source id: {source_id}")
        seen.add(source_id)
        raw_path = source["rawPath"]
        relative = PurePosixPath(raw_path)
        if ("\\" in raw_path or relative.is_absolute() or ".." in relative.parts
                or relative.parts[:2] != ("data", "raw") or len(relative.parts) < 3):
            raise ValueError(f"Unsafe raw path for {source_id}")
        path = (root / raw_path).resolve()
        if not path.is_relative_to(raw_root):
            raise ValueError(f"Raw path escapes raw directory for {source_id}")
        if not path.is_file():
            raise ValueError(f"Missing raw file for {source_id}: {raw_path}; use its documented retrieval recipe")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != source["sha256"]:
            raise ValueError(f"Checksum mismatch for {source_id}")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    registry = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))
    verify_source_files(root, registry)
    print(f"Source file integrity passed ({len(registry['sources'])} registered resources).")


if __name__ == "__main__":
    main()
