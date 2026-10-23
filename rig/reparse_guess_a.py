"""Re-read guess A's verdict from the stored raw answer where the JSON did not parse (teacher.irreversible_field,
23 Oct 2026).  Rewrites results.jsonl in place; run it only when no collector is appending to that file.

    OSWorld/.venv/bin/python -I rig/reparse_guess_a.py rig/out/pilot150_a [more out dirs]
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from rig.teacher import _json_block, irreversible_field  # noqa: E402

for out in sys.argv[1:]:
    path = pathlib.Path(out) / "results.jsonl"
    lines = path.read_text().splitlines()
    changed = []
    new_lines = []
    for line in lines:
        r = json.loads(line)
        g = r.get("guessed_label_verbatim") or {}
        if r.get("status") in ("ok", "broken_action") and g.get("reversible") is None and g.get("raw"):
            parsed = _json_block(g["raw"])
            if not (isinstance(parsed, dict) and "irreversible" in parsed):
                parsed = irreversible_field(g["raw"])
            if isinstance(parsed, dict) and "irreversible" in parsed:
                g["reversible"] = not bool(parsed["irreversible"])
                g["reason"] = parsed.get("irreversibility_reason") or parsed.get("long_term_impact")
                g["parsed"] = parsed
                g["reparsed"] = "2026-10-23 rig/reparse_guess_a.py"
                r["guessed_label_verbatim"] = g
                changed.append((r["row_id"], g["reversible"]))
        new_lines.append(json.dumps(r, ensure_ascii=False))
    if changed:
        path.write_text("\n".join(new_lines) + "\n")
    print(f"{out}: {len(changed)} guess A verdicts recovered", changed)
