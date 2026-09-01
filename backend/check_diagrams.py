"""Analyze JSON structure of all archify diagrams."""
import json
import os
import sys


def _analyze_diagrams() -> int:
    diagrams_dir = os.path.join(os.path.dirname(__file__), "..", "design-docs", "diagrams")
    diagrams = [
        ("current-architecture", "architecture"),
        ("target-architecture", "architecture"),
        ("multi-stack-dataflow", "dataflow"),
        ("agent-tool-workflow", "workflow"),
        ("validate-preview-workflow", "workflow"),
        ("adb-capture-sequence", "sequence"),
        ("codegen-lifecycle", "lifecycle"),
    ]
    errors = 0

    for name, dtype in diagrams:
        json_path = os.path.join(diagrams_dir, f"{name}.{dtype}.json")
        if not os.path.exists(json_path):
            sys.stderr.write(f"SKIP {name}\n")
            continue
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            sys.stderr.write(f"ERROR {name}: {exc}\n")
            errors += 1
            continue
        meta = data.get("meta", {})
        schema_ver = data.get("schema_version", "N/A")
        viewBox = meta.get("viewBox", meta.get("viewbox", "N/A"))

        if dtype == "architecture":
            comps = len(data.get("components", []))
            conns = len(data.get("connections", []))
            cards = len(data.get("cards", []))
            sys.stderr.write(f"{name:40s} v{schema_ver} comps={comps} conns={conns} cards={cards} viewBox={viewBox}\n")
        elif dtype == "dataflow":
            stages = len(data.get("stages", []))
            nodes = len(data.get("nodes", []))
            flows = len(data.get("flows", []))
            sys.stderr.write(f"{name:40s} v{schema_ver} stages={stages} nodes={nodes} flows={flows} viewBox={viewBox}\n")
        elif dtype == "workflow":
            lanes = len(data.get("lanes", []))
            nodes = len(data.get("nodes", []))
            edges = len(data.get("edges", []))
            sys.stderr.write(f"{name:40s} v{schema_ver} lanes={lanes} nodes={nodes} edges={edges} viewBox={viewBox}\n")
        elif dtype == "sequence":
            parts = len(data.get("participants", []))
            msgs = len(data.get("messages", []))
            segs = len(data.get("segments", []))
            sys.stderr.write(f"{name:40s} v{schema_ver} parts={parts} msgs={msgs} segs={segs} viewBox={viewBox}\n")
        elif dtype == "lifecycle":
            lanes = len(data.get("lanes", []))
            states = len(data.get("states", []))
            trans = len(data.get("transitions", []))
            sys.stderr.write(f"{name:40s} v{schema_ver} lanes={lanes} states={states} trans={trans} viewBox={viewBox}\n")
        else:
            sys.stderr.write(f"WARN {name}: unknown diagram type '{dtype}'\n")

    return errors


if __name__ == "__main__":
    sys.exit(_analyze_diagrams())
