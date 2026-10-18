"""What a spreadsheet file says, independent of which program wrote it.

Two saves of the same workbook by different programs (Excel, an older LibreOffice, the LibreOffice in the VM)
differ in their XML: style tables are renumbered, shared formulas are expanded, strings move in or out of the
shared-string table.  The pilot caught this: re-saving an untouched workbook made the byte hash and the
metadata-free zip hash differ, so a plain save was labelled one-way (pilot-0121), and no undo of a save could
ever match (pilot-0210, every candidate rejected on the file alone).

`cell_signature(path)` reads the workbook the way a user sees it and hashes that:
  * sheets in order, with their names and hidden state;
  * every cell that holds a value or non-default formatting: its value (numbers to 12 significant digits,
    strings resolved from the shared-string table), whether it is a formula, and its resolved format
    (bold, italic, underline, strike-through, number format, fill, horizontal alignment);
  * hidden columns and rows, and merged ranges.
Excel's built-in short date (14) and short date-time (22) follow the machine's locale, so they are named by
meaning, not by an en-US pattern; the VM's own short-date code (_LOCALE_SHORTDATE), which LibreOffice writes for
14, is named the same way.  Text cells carry no number format (it does not change how text is shown).  Formula cells compare by their stored result plus a formula flag, not by formula text, because writers store
the same formula differently (Excel's shared formulas are written out cell by cell by LibreOffice).

Standard library only: this file's source is also sent into the VM inside the digest script (snapshot.py).
"""
import hashlib
import json
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

_BUILTIN_FMT = {0: "general", 1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00", 9: "0%", 10: "0.00%", 11: "0.00e+00",
                12: "# ?/?", 13: "# ??/??", 14: "builtin:shortdate", 15: "d-mmm-yy", 16: "d-mmm", 17: "mmm-yy",
                18: "h:mm am/pm", 19: "h:mm:ss am/pm", 20: "h:mm", 21: "h:mm:ss", 22: "builtin:shortdatetime",
                37: "#,##0 ;(#,##0)", 38: "#,##0 ;[red](#,##0)", 39: "#,##0.00;(#,##0.00)",
                40: "#,##0.00;[red](#,##0.00)", 45: "mm:ss", 46: "[h]:mm:ss", 47: "mmss.0", 48: "##0.0e+0", 49: "@"}
_MAX_COL = 16384
# The VM's own short-date pattern.  LibreOffice writes Excel's locale-following short date (built-in 14) out as
# this explicit code, so the same dates read as a format change after a plain re-save (recheck pilot-0231,
# 19 Oct 2026: 4,002 date cells, every value equal).  Shown identically on this machine, so named by meaning.
_LOCALE_SHORTDATE = {"dd/mm/yyyy"}
_TEXT_TYPES = ("s", "inlineStr", "str")   # a number format does not change how text is shown
_DEFAULT_FMT = (False, False, False, False, "general", None, None)


def _l(tag):
    return tag.rsplit("}", 1)[-1]


def _kids(el, name):
    return [c for c in el if _l(c.tag) == name]


def _kid(el, name):
    for c in el:
        if _l(c.tag) == name:
            return c
    return None


def _attr(el, name):
    for k, v in el.attrib.items():
        if _l(k) == name:
            return v
    return None


def _on(el):
    """<b/>, <b val="1"/>, <b val="true"/> are on; <b val="0"/> is off; absent is off."""
    if el is None:
        return False
    v = _attr(el, "val")
    return v is None or v.lower() not in ("0", "false", "none")


def _fmt_code(code):
    return code.lower().replace("\\", "").replace('"', "")


def _color(el):
    if el is None:
        return None
    rgb = _attr(el, "rgb")
    if rgb:
        return rgb.upper()[-6:]
    for k in ("theme", "indexed"):
        v = _attr(el, k)
        if v is not None:
            return f"{k}{v}"
    return None


def _num(text):
    try:
        return format(float(text), ".12g")
    except (TypeError, ValueError):
        return text


def _col_index(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n


def _styles(z):
    try:
        root = ET.fromstring(z.read("xl/styles.xml"))
    except KeyError:
        return []
    fmts = dict(_BUILTIN_FMT)
    nf = _kid(root, "numFmts")
    for f in (_kids(nf, "numFmt") if nf is not None else []):
        code = _fmt_code(f.get("formatCode", ""))
        fmts[int(f.get("numFmtId"))] = "builtin:shortdate" if code in _LOCALE_SHORTDATE else code
    fonts = []
    fe = _kid(root, "fonts")
    for f in (_kids(fe, "font") if fe is not None else []):
        u = _kid(f, "u")
        fonts.append((_on(_kid(f, "b")), _on(_kid(f, "i")), u is not None and (_attr(u, "val") or "single") != "none",
                      _on(_kid(f, "strike"))))
    fills = []
    fl = _kid(root, "fills")
    for f in (_kids(fl, "fill") if fl is not None else []):
        p = _kid(f, "patternFill")
        if p is None or (p.get("patternType") or "none") == "none":
            fills.append(None)
        else:
            fills.append((p.get("patternType"), _color(_kid(p, "fgColor"))))
    out = []
    xfs = _kid(root, "cellXfs")
    for xf in (_kids(xfs, "xf") if xfs is not None else []):
        font = fonts[int(xf.get("fontId", 0))] if fonts and int(xf.get("fontId", 0)) < len(fonts) else (False,) * 4
        fill_id = int(xf.get("fillId", 0))
        fill = fills[fill_id] if fill_id < len(fills) else None
        al = _kid(xf, "alignment")
        halign = al.get("horizontal") if al is not None else None
        if halign == "general":
            halign = None
        out.append(font + (fmts.get(int(xf.get("numFmtId", 0)), "general"), fill, halign))
    return out


def _shared_strings(z):
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(t.text or "" for t in si.iter() if _l(t.tag) == "t") for si in _kids(root, "si")]


def _sheet_paths(z):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    sheets = _kid(wb, "sheets")
    out = []
    for s in (_kids(sheets, "sheet") if sheets is not None else []):
        t = target.get(_attr(s, "id"), "")
        path = t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join("xl", t))
        out.append((s.get("name"), s.get("state") or "visible", path))
    return out


def _ranges(indices):
    out = []
    for i in sorted(indices):
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def workbook_view(path):
    """The user-visible content of an .xlsx/.xlsm as plain data (sheets, cells, hidden columns/rows, merges)."""
    with zipfile.ZipFile(path) as z:
        styles = _styles(z)
        strings = _shared_strings(z)
        view = []
        for name, state, sheet_path in _sheet_paths(z):
            root = ET.fromstring(z.read(sheet_path))
            hidden_cols = set()
            cols = _kid(root, "cols")
            for c in (_kids(cols, "col") if cols is not None else []):
                if _on_attr(c.get("hidden")):
                    hidden_cols.update(range(int(c.get("min")), min(int(c.get("max")), _MAX_COL) + 1))
            hidden_rows, cells = [], {}
            data = _kid(root, "sheetData")
            for row in (_kids(data, "row") if data is not None else []):
                if _on_attr(row.get("hidden")):
                    hidden_rows.append(int(row.get("r")))
                for c in _kids(row, "c"):
                    t = c.get("t") or "n"
                    v, f, is_ = _kid(c, "v"), _kid(c, "f"), _kid(c, "is")
                    if t == "s" and v is not None:
                        value = strings[int(v.text)] if int(v.text) < len(strings) else ""
                    elif t == "inlineStr" and is_ is not None:
                        value = "".join(x.text or "" for x in is_.iter() if _l(x.tag) == "t")
                    elif t in ("str", "e"):
                        value = v.text if v is not None else ""
                    elif t == "b":
                        value = "TRUE" if v is not None and v.text == "1" else "FALSE"
                    else:
                        value = _num(v.text) if v is not None and v.text is not None else ""
                    s = int(c.get("s", 0))
                    fmt = styles[s] if s < len(styles) else _DEFAULT_FMT
                    if value == "" and f is None and fmt == _DEFAULT_FMT:
                        continue
                    numfmt = "general" if t in _TEXT_TYPES else fmt[4]
                    cells[c.get("r")] = [value, f is not None, list(fmt[:4]), numfmt, fmt[5], fmt[6]]
            merges = sorted(m.get("ref") for m in root.iter() if _l(m.tag) == "mergeCell")
            view.append({"name": name, "state": state, "cells": cells, "hidden_cols": _ranges(hidden_cols),
                         "hidden_rows": hidden_rows, "merges": merges})
        return view


def _on_attr(v):
    return v is not None and v.lower() in ("1", "true")


def cell_signature(path):
    try:
        view = workbook_view(path)
    except Exception:
        return None
    return hashlib.sha256(json.dumps(view, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
