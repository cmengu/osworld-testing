"""Offline checks of the cell-level workbook signature (rig/xlsxsig.py) and of the digest script that carries it.

Builds small workbooks by hand: the same sheet written two ways (shared strings vs inline strings, style tables
in a different order, an extra unused style) must compare equal; a changed value, a bold, a hidden column, a
renamed sheet must not.  Then runs the VM digest script on a scratch home directory and checks it reports the
same signature.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from rig.mask import file_sig                      # noqa: E402
from rig.snapshot import DIGEST_SCRIPT             # noqa: E402
from rig.xlsxsig import cell_signature, workbook_view   # noqa: E402

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' \
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
RELS = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="{target}"/></Relationships>')


def styles(fonts, xfs, numfmts=""):
    f = "".join(fonts)
    x = "".join(xfs)
    return (f'<styleSheet {NS}>{numfmts}<fonts count="{len(fonts)}">{f}</fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            f'<cellXfs count="{len(xfs)}">{x}</cellXfs></styleSheet>')


# date column: Excel's locale short date (built-in 14), the code LibreOffice writes for it on the VM, or a
# genuinely different pattern a user picked
DATE_FMTS = {"builtin14": ("", 14), "vm_short": ('<numFmts count="1"><numFmt numFmtId="164" formatCode="DD/MM/YYYY"/></numFmts>', 164),
             "iso": ('<numFmts count="1"><numFmt numFmtId="164" formatCode="YYYY-MM-DD"/></numFmts>', 164)}


def build(path, *, sheet_name="Data", writer="excel", bold_b1=True, value_a2="42", hide_c=False, date="builtin14",
          header_dated=False):
    plain = '<font><sz val="11"/><name val="Calibri"/></font>'
    bold = '<font><b/><sz val="11"/><name val="Calibri"/></font>'
    cols = '<cols><col min="3" max="3" width="9" hidden="1" customWidth="1"/></cols>' if hide_c else ""
    if writer == "excel":       # shared strings, plain font first, bold xf at index 1, workbook rels with ../ path
        nf, fid = DATE_FMTS[date]
        st = styles([plain, bold], ['<xf numFmtId="0" fontId="0" fillId="0"/>', f'<xf numFmtId="0" fontId="{1 if bold_b1 else 0}" fillId="0"/>',
                                    f'<xf numFmtId="{fid}" fontId="0" fillId="0" applyNumberFormat="1"/>'], nf)
        shared = f'<sst {NS}><si><t>Name</t></si><si><t>Total</t></si></sst>'
        a1 = f'<c r="A1"{" s=\"2\"" if header_dated else ""} t="s"><v>0</v></c>'
        a3 = '<c r="A3" s="2"><v>44076</v></c>'
        b1 = '<c r="B1" s="1" t="s"><v>1</v></c>'
        target, rid = "worksheets/sheet1.xml", "rId1"
        a2 = f'<c r="A2"><v>{value_a2}</v></c>'
        b2 = '<c r="B2"><f t="shared" ref="B2:B2" si="0">A2*2</f><v>84</v></c>'
    else:                       # LibreOffice-like: inline strings, bold font first, extra unused style, absolute target
        nf, fid = DATE_FMTS["vm_short" if date == "builtin14" else date]   # LibreOffice spells 14 out
        st = styles([bold, plain, plain], ['<xf numFmtId="0" fontId="1" fillId="0"/>', '<xf numFmtId="0" fontId="2" fillId="0"/>',
                                           f'<xf numFmtId="0" fontId="{0 if bold_b1 else 1}" fillId="0"><alignment horizontal="general"/></xf>',
                                           f'<xf numFmtId="{fid}" fontId="1" fillId="0"/>'], nf)
        shared = None
        a1 = f'<c r="A1"{" s=\"3\"" if header_dated else ""} t="inlineStr"><is><t>Name</t></is></c>'
        a3 = '<c r="A3" s="3"><v>44076</v></c>'
        b1 = '<c r="B1" s="2" t="inlineStr"><is><r><t>To</t></r><r><t>tal</t></r></is></c>'
        target, rid = "/xl/worksheets/sheet1.xml", "rIdX"
        a2 = f'<c r="A2" s="1"><v>{value_a2}.0</v></c>'
        b2 = '<c r="B2"><f>A2*2</f><v>84.00000000000001</v></c><c r="D2" s="1"/>'
    sheet = f'<worksheet {NS}>{cols}<sheetData><row r="1">{a1}{b1}</row><row r="2">{a2}{b2}</row><row r="3">{a3}</row></sheetData></worksheet>'
    wb = f'<workbook {NS}><sheets><sheet name="{sheet_name}" sheetId="1" r:id="{rid}"/></sheets></workbook>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", RELS.format(rid=rid, target=target))
        z.writestr("xl/styles.xml", st)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        if shared:
            z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("docProps/app.xml", f"<Properties><Application>{writer}</Application></Properties>")


tmp = pathlib.Path(tempfile.mkdtemp())
ref = tmp / "excel.xlsx"
build(ref)
k = cell_signature(ref)
assert k, "reference workbook must be readable"
print(json.dumps(workbook_view(ref)))

cases = {
    "libreoffice": (dict(writer="lo"), True),
    "value": (dict(value_a2="43"), False),
    "bold": (dict(bold_b1=False), False),
    "hidden_col": (dict(hide_c=True), False),
    "sheet_name": (dict(sheet_name="Data2"), False),
    "lo_value": (dict(writer="lo", value_a2="43"), False),
    "lo_bold": (dict(writer="lo", bold_b1=False), False),
    "lo_date": (dict(writer="lo", date="vm_short"), True),             # 14 written out as the VM's short date
    "iso_date": (dict(date="iso"), False),                              # a different date style is a change
    "lo_iso_date": (dict(writer="lo", date="iso"), False),
    "text_datefmt": (dict(header_dated=True), True),                    # a date format on a text cell shows nothing
    "lo_text_datefmt": (dict(writer="lo", header_dated=True), True),
}
for name, (kw, should_match) in cases.items():
    p = tmp / f"{name}.xlsx"
    build(p, **kw)
    got = cell_signature(p) == k
    assert got == should_match, (name, workbook_view(p))
    print(f"  {name:12s} {'same' if got else 'different'} (expected {'same' if should_match else 'different'})")

# file_sig prefers the cell signature over bytes
assert file_sig({"s": 1, "h": "a", "c": "x", "k": "K"}) == file_sig({"s": 2, "h": "b", "c": "y", "k": "K"})
assert file_sig({"s": 1, "h": "a", "c": "x"}) != file_sig({"s": 1, "h": "a", "c": "y"})

# The VM digest script, run on a scratch home, reports the same signature and keeps the view.
home = tmp / "home"
home.mkdir()
build(home / "book.xlsx")
body = DIGEST_SCRIPT.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
script = tmp / "digest.py"
script.write_text(body)
out = subprocess.run([sys.executable, "-I", str(script)], env={**os.environ, "HOME": str(home)},
                     capture_output=True, text=True, check=True).stdout
rows = {r["p"]: r for r in json.loads(out)}
row = rows[str(home / "book.xlsx")]
assert row.get("k") == k and row.get("v"), row.keys()
print("ALL XLSXSIG CHECKS PASSED")
