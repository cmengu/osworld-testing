"""What a text document or a slide deck says, independent of which program wrote it (24 Oct 2026).

Re-saving a .docx or .pptx in LibreOffice rewrites every XML part, so the byte hash and the metadata-free zip
hash both change although nothing a user can see has: with those alone a plain save is one-way and no undo of a
save can match, as happened to Calc rows before rig/xlsxsig.py (pilot-0121, pilot-0210).  This module does for
Writer and Impress files what xlsxsig does for workbooks.

`doc_signature(path)` hashes the user-visible content:
  * .docx: body paragraphs in order (style id, alignment, text split into runs by bold/italic/underline/
    strike-through), tables as rows of cells of paragraphs, headers and footers, and the hashes of embedded
    images;
  * .pptx: slides in order (hidden flag), each shape's placeholder type, position and size in 1/100 mm, its
    paragraphs (text with bold/italic/underline), pictures by image hash, tables by cell text, and the slide's
    speaker notes;
  * .odt / .odp: the same from content.xml (paragraphs and headings with spans flattened, tables, frames by
    position and text, presentation notes).
Fonts, colours, sizes, themes and styles.xml are left out on purpose: a re-save renames or renumbers them,
and the rows of this dataset change text, slides and files, not typography.

Standard library only: this file's source is also sent into the VM inside the digest script (snapshot.py).
"""
import hashlib
import json
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
EMU_PER_HMM = 360          # EMUs per 1/100 mm; LibreOffice keeps positions in 1/100 mm, so this rounding is exact
DOC_EXT = (".docx", ".odt", ".pptx", ".odp")


def _l(tag):
    return tag.rsplit("}", 1)[-1]


def _on(el, attr=W + "val"):
    if el is None:
        return False
    v = el.get(attr)
    return v is None or v.lower() in ("1", "true", "on")


def _rels(z, part):
    """Relationship id -> target path (absolute inside the zip) for a part."""
    d, f = posixpath.split(part)
    rel = posixpath.join(d, "_rels", f + ".rels")
    out = {}
    if rel not in z.namelist():
        return out
    for r in ET.fromstring(z.read(rel)):
        if _l(r.tag) != "Relationship" or r.get("TargetMode") == "External":
            continue
        t = r.get("Target") or ""
        out[r.get("Id")] = posixpath.normpath(posixpath.join(d, t)) if not t.startswith("/") else t.lstrip("/")
    return out


def _blob(z, path):
    try:
        return hashlib.sha256(z.read(path)).hexdigest()[:16]
    except KeyError:
        return None


# ------------------------------------------------------------------ .docx
def _docx_runs(p):
    segs = []
    for node in p.iter():
        if _l(node.tag) != "r":
            continue
        rpr = node.find(W + "rPr")
        u = rpr.find(W + "u") if rpr is not None else None
        fmt = (_on(rpr.find(W + "b")) if rpr is not None else False,
               _on(rpr.find(W + "i")) if rpr is not None else False,
               u is not None and (u.get(W + "val") or "single") != "none",
               _on(rpr.find(W + "strike")) if rpr is not None else False)
        text = ""
        for c in node:
            t = _l(c.tag)
            if t == "t":
                text += c.text or ""
            elif t == "tab":
                text += "\t"
            elif t in ("br", "cr"):
                text += "\n"
        if not text:
            continue
        if segs and segs[-1][1] == fmt:
            segs[-1][0] += text
        else:
            segs.append([text, fmt])
    return [[s, list(f)] for s, f in segs]


def _docx_para(p):
    ppr = p.find(W + "pPr")
    style = jc = None
    numbered = False
    if ppr is not None:
        ps = ppr.find(W + "pStyle")
        style = ps.get(W + "val") if ps is not None else None
        j = ppr.find(W + "jc")
        jc = j.get(W + "val") if j is not None else None
        numbered = ppr.find(W + "numPr") is not None
    return ["p", style, jc, numbered, _docx_runs(p)]


def _docx_blocks(parent):
    out = []
    for el in parent:
        t = _l(el.tag)
        if t == "p":
            out.append(_docx_para(el))
        elif t == "tbl":
            rows = []
            for tr in el:
                if _l(tr.tag) != "tr":
                    continue
                rows.append([_docx_blocks(tc) for tc in tr if _l(tc.tag) == "tc"])
            out.append(["tbl", rows])
        elif t == "sdt":                       # content control: its content is what shows
            c = el.find(W + "sdtContent")
            if c is not None:
                out.extend(_docx_blocks(c))
    return out


def docx_view(z):
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    view = {"body": _docx_blocks(body) if body is not None else []}
    extras = {}
    for name in sorted(z.namelist()):
        if re.match(r"word/(header|footer)\d*\.xml$", name):
            extras[name] = _docx_blocks(ET.fromstring(z.read(name)))
    if extras:
        view["headers_footers"] = extras
    media = sorted(h for h in (_blob(z, n) for n in z.namelist() if n.startswith("word/media/")) if h)
    if media:
        view["images"] = media
    return view


# ------------------------------------------------------------------ .pptx
def _a_text(txbody):
    """Paragraphs of a DrawingML text body: [[text, [b, i, u]], ...] per paragraph."""
    paras = []
    if txbody is None:
        return paras
    for p in txbody:
        if _l(p.tag) != "p":
            continue
        segs = []
        for c in p:
            t = _l(c.tag)
            if t in ("r", "fld"):
                rpr = c.find(A + "rPr")
                fmt = (rpr is not None and rpr.get("b") == "1", rpr is not None and rpr.get("i") == "1",
                       rpr is not None and (rpr.get("u") or "none") != "none")
                tt = c.find(A + "t")
                text = tt.text or "" if tt is not None else ""
                if not text:
                    continue
                if segs and segs[-1][1] == fmt:
                    segs[-1][0] += text
                else:
                    segs.append([text, fmt])
            elif t == "br":
                if segs:
                    segs[-1][0] += "\n"
                else:
                    segs.append(["\n", (False, False, False)])
        paras.append([[s, list(f)] for s, f in segs])
    return paras


def _xfrm(sppr):
    if sppr is None:
        return None
    x = sppr.find(A + "xfrm")
    if x is None:
        return None
    off, ext = x.find(A + "off"), x.find(A + "ext")
    def hmm(v):
        return None if v is None else round(int(v) / EMU_PER_HMM)
    return [hmm(off.get("x")) if off is not None else None, hmm(off.get("y")) if off is not None else None,
            hmm(ext.get("cx")) if ext is not None else None, hmm(ext.get("cy")) if ext is not None else None]


def _pptx_shapes(tree, z, rels):
    out = []
    for el in tree:
        t = _l(el.tag)
        if t == "sp":
            ph = None
            nv = el.find(P + "nvSpPr")
            if nv is not None:
                pp = nv.find(P + "nvPr")
                phe = pp.find(P + "ph") if pp is not None else None
                if phe is not None:
                    ph = (phe.get("type") or "body") + ("#" + phe.get("idx") if phe.get("idx") else "")
            out.append(["sp", ph, _xfrm(el.find(P + "spPr")), _a_text(el.find(P + "txBody"))])
        elif t == "pic":
            blip = next((b for b in el.iter() if _l(b.tag) == "blip"), None)
            rid = blip.get(R + "embed") if blip is not None else None
            out.append(["pic", _xfrm(el.find(P + "spPr")), _blob(z, rels.get(rid, "")) if rid else None])
        elif t == "graphicFrame":
            tbl = next((x for x in el.iter() if _l(x.tag) == "tbl"), None)
            cells = None
            if tbl is not None:
                cells = [[_a_text(tc.find(A + "txBody")) for tc in tr if _l(tc.tag) == "tc"]
                         for tr in tbl if _l(tr.tag) == "tr"]
            out.append(["frame", _xfrm(el.find(P + "xfrm")) if el.find(P + "xfrm") is not None else None, cells])
        elif t == "grpSp":
            out.append(["grp", _pptx_shapes(el, z, rels)])
        elif t == "cxnSp":
            out.append(["cxn", _xfrm(el.find(P + "spPr"))])
    return out


def pptx_view(z):
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    prels = _rels(z, "ppt/presentation.xml")
    slides = []
    lst = next((x for x in pres.iter() if _l(x.tag) == "sldIdLst"), None)
    for sid in (lst if lst is not None else []):
        path = prels.get(sid.get(R + "id"))
        if not path or path not in z.namelist():
            continue
        root = ET.fromstring(z.read(path))
        rels = _rels(z, path)
        tree = next((x for x in root.iter() if _l(x.tag) == "spTree"), None)
        entry = {"shapes": _pptx_shapes(tree, z, rels) if tree is not None else [], "hidden": root.get("show") == "0"}
        notes = next((p for p in rels.values() if "/notesSlides/" in p), None)
        if notes and notes in z.namelist():
            nroot = ET.fromstring(z.read(notes))
            texts = []
            for sp in nroot.iter():
                if _l(sp.tag) == "sp":
                    nv = sp.find(P + "nvSpPr")
                    pp = nv.find(P + "nvPr") if nv is not None else None
                    phe = pp.find(P + "ph") if pp is not None else None
                    if phe is not None and phe.get("type") == "body":
                        texts.extend(_a_text(sp.find(P + "txBody")))
            if any(seg for para in texts for seg in para):
                entry["notes"] = texts
        slides.append(entry)
    return {"slides": slides}


# ------------------------------------------------------------------ .odt / .odp
_ODF_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_ODF_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
_ODF_DRAW = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
_ODF_SVG = "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
_ODF_PRES = "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0"
_ODF_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
_UNIT_HMM = {"cm": 1000, "mm": 100, "in": 2540, "pt": 2540 / 72, "pc": 2540 / 6}


def _odf_len(v):
    if not v:
        return None
    m = re.match(r"\s*(-?[\d.]+)\s*([a-z]*)", v)
    if not m:
        return None
    return round(float(m.group(1)) * _UNIT_HMM.get(m.group(2), 100))


def _odf_text(el):
    """Text of a text:p or text:h with spans flattened, tabs, breaks and repeated spaces expanded."""
    out = [el.text or ""]
    for c in el:
        t = _l(c.tag)
        if t == "tab":
            out.append("\t")
        elif t == "line-break":
            out.append("\n")
        elif t == "s":
            out.append(" " * int(c.get("{%s}c" % _ODF_TEXT, "1")))
        elif t in ("note", "annotation", "tracked-changes"):
            pass
        else:
            out.append(_odf_text(c))
        out.append(c.tail or "")
    return "".join(out)


def _odf_blocks(parent):
    out = []
    for el in parent:
        t = _l(el.tag)
        if t in ("p", "h"):
            out.append(["p", t, el.get("{%s}style-name" % _ODF_TEXT), _odf_text(el)])
        elif t == "list":
            out.append(["list", _odf_blocks_deep(el)])
        elif t == "table":
            rows = []
            for tr in el.iter("{%s}table-row" % _ODF_TABLE):
                rows.append([_odf_blocks(tc) for tc in tr if _l(tc.tag) == "table-cell"])
            out.append(["tbl", rows])
        elif t == "frame":
            inner = _odf_blocks(el)
            img = next((i.get("{http://www.w3.org/1999/xlink}href") for i in el.iter("{%s}image" % _ODF_DRAW)), None)
            out.append(["frame", [_odf_len(el.get("{%s}%s" % (_ODF_SVG, k))) for k in ("x", "y", "width", "height")], inner, img])
        elif t in ("text-box", "section", "custom-shape", "g"):
            out.extend(_odf_blocks(el))
    return out


def _odf_blocks_deep(el):
    out = []
    for item in el.iter("{%s}list-item" % _ODF_TEXT):
        out.append(_odf_blocks(item))
    return out


def odf_view(z, kind):
    root = ET.fromstring(z.read("content.xml"))
    body = root.find("{%s}body" % _ODF_OFFICE)
    if body is None:
        return {}
    media = sorted(h for h in (_blob(z, n) for n in z.namelist() if n.startswith("Pictures/")) if h)
    if kind == "odt":
        text = body.find("{%s}text" % _ODF_OFFICE)
        view = {"body": _odf_blocks(text) if text is not None else []}
    else:
        pres = body.find("{%s}presentation" % _ODF_OFFICE)
        pages = []
        for page in (pres if pres is not None else []):
            if _l(page.tag) != "page":
                continue
            notes = page.find("{%s}notes" % _ODF_PRES)
            entry = {"shapes": _odf_blocks([c for c in page if _l(c.tag) != "notes"])}
            if notes is not None:
                ntext = [b for b in _odf_blocks(notes) if b[0] != "frame" or b[2]]
                if ntext:
                    entry["notes"] = ntext
            pages.append(entry)
        view = {"slides": pages}
    if media:
        view["images"] = media
    return view


# ------------------------------------------------------------------ entry points
def doc_view(path):
    low = path.lower()
    with zipfile.ZipFile(path) as z:
        if low.endswith(".docx"):
            return docx_view(z)
        if low.endswith(".pptx"):
            return pptx_view(z)
        if low.endswith(".odt"):
            return odf_view(z, "odt")
        if low.endswith(".odp"):
            return odf_view(z, "odp")
    raise ValueError(path)


def doc_signature(path):
    try:
        view = doc_view(path)
    except Exception:
        return None
    return hashlib.sha256(json.dumps(view, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
