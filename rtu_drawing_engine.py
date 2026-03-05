import streamlit as st
import pdfplumber
import json
import re
import io
import math
import tempfile
import os
import anthropic
import ezdxf
from ezdxf.enums import TextEntityAlignment
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="RTU Drawing Template Engine",
    layout="wide",
    page_icon="⚡"
)

st.markdown("""
<style>
  .main { background: #0f1117; }
  .block-container { padding-top: 1.5rem; }
  .stTextInput input, .stTextArea textarea, .stSelectbox select {
      background: #1e2130; color: #e2e8f0; border: 1px solid #2d3748;
  }
  .field-card {
      background: #1a2035; border: 1px solid #2d3748; border-radius: 8px;
      padding: 16px; margin-bottom: 12px;
  }
  .section-head {
      background: #1e4e79; color: white; padding: 8px 14px;
      border-radius: 6px; font-weight: 700; font-size: 13px;
      letter-spacing: 1px; margin: 16px 0 8px 0;
  }
  .chat-user   { background:#1e3a5f; border-radius:8px; padding:10px 14px; margin:6px 0; }
  .chat-ai     { background:#1a2e1a; border-radius:8px; padding:10px 14px; margin:6px 0; }
  .extracted-badge {
      background:#2a6b3a; color:white; font-size:11px;
      padding:2px 8px; border-radius:12px; margin-left:8px;
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "fields" not in st.session_state:
    st.session_state.fields = {}
if "bom_items" not in st.session_state:
    st.session_state.bom_items = []
if "di_channels" not in st.session_state:
    st.session_state.di_channels = []
if "do_channels" not in st.session_state:
    st.session_state.do_channels = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_extracted" not in st.session_state:
    st.session_state.pdf_extracted = False
if "drawing_list" not in st.session_state:
    st.session_state.drawing_list = []

# ─────────────────────────────────────────────
# PDF EXTRACTION
# ─────────────────────────────────────────────
def extract_from_pdf(uploaded_file):
    """Extract all structured data from RTU drawing PDF."""
    full_text = ""
    pages_text = []
    with pdfplumber.open(uploaded_file) as pdf:
        for i, page in enumerate(pdf.pages):
            t = page.extract_text() or ""
            pages_text.append({"page": i+1, "text": t})
            full_text += f"\n--- PAGE {i+1} ---\n{t}"

    # Use Claude to intelligently extract all fields
    client = anthropic.Anthropic()
    prompt = f"""You are an expert at reading electrical engineering drawings.
Extract ALL structured data from this RTU panel drawing text.
Return ONLY valid JSON with this exact structure:

{{
  "project_info": {{
    "client": "",
    "project": "",
    "manufacturer": "",
    "dwg_no": "",
    "panel_tag": "",
    "panel_no": "",
    "qty": "",
    "rev": "",
    "scale": "",
    "designed_by": "",
    "checked_by": "",
    "approved_by": "",
    "date": "",
    "released_for": ""
  }},
  "drawing_list": [
    {{"sl_no": "01", "description": "TITLE SHEET", "sheet_no": "1", "rev": "0"}}
  ],
  "panel_spec": {{
    "enclosure_dimension": "",
    "construction": "",
    "wiring_control": "",
    "wiring_ac_power": "",
    "wiring_dc_power": "",
    "wiring_earthing": ""
  }},
  "bom": [
    {{"sl_no": "1", "panel_tag": "", "description": "", "qty": "", "make": ""}}
  ],
  "di_channels": [
    {{"channel": "IN01", "terminal": "TBX1.01", "label": "SPARE", "connector": "C01"}}
  ],
  "do_channels": [
    {{"channel": "OUT01", "terminal": "TBX3.01", "label": "SPARE", "connector": "D01"}}
  ],
  "cabinet": {{
    "type": "",
    "class_of_protection": "",
    "cable_entry": "",
    "material_thickness": ""
  }}
}}

Drawing text:
{full_text[:6000]}
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    # Strip markdown code fences if present
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


# ─────────────────────────────────────────────
# AI CHAT — FIELD UPDATER
# ─────────────────────────────────────────────
def process_chat_command(user_msg, current_fields):
    """Use Claude to interpret natural language and return updated fields."""
    client = anthropic.Anthropic()
    prompt = f"""You are an assistant that updates RTU electrical drawing fields.
The user will give instructions in plain English.
Current drawing data (JSON):
{json.dumps(current_fields, indent=2)}

User instruction: "{user_msg}"

Update ONLY the fields the user mentioned. Return the complete updated JSON.
Return ONLY valid JSON, no explanation, no markdown.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    raw = re.sub(r"```json|```", "", raw).strip()
    updated = json.loads(raw)
    # Summarise what changed
    changes = []
    def diff(a, b, path=""):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in b:
                diff(a.get(k), b[k], f"{path}.{k}" if path else k)
        elif isinstance(a, list) and isinstance(b, list):
            pass  # list changes summarised simply
        else:
            if str(a) != str(b) and b:
                changes.append(f"**{path}**: `{a}` → `{b}`")
    diff(current_fields, updated)
    summary = "\n".join(changes[:10]) if changes else "Fields updated as requested."
    return updated, summary


# ─────────────────────────────────────────────
# DXF EXPORT ENGINE
# ─────────────────────────────────────────────
def draw_title_block_dxf(msp, fields, sheet_no, sheet_title, total_sheets, W=420, H=297):
    """Draw A3 border + standard title block in DXF modelspace."""
    pi = fields.get("project_info", {})

    # Outer border
    msp.add_lwpolyline(
        [(5,5),(W-5,5),(W-5,H-5),(5,H-5)],
        close=True, dxfattribs={"color":7, "lineweight":50}
    )
    # Inner border
    msp.add_lwpolyline(
        [(10,10),(W-10,10),(W-10,H-10),(10,H-10)],
        close=True, dxfattribs={"color":7, "lineweight":25}
    )

    # Title block box (bottom right)
    tb_x, tb_y, tb_w, tb_h = W-130, 10, 120, 60
    msp.add_lwpolyline(
        [(tb_x,tb_y),(tb_x+tb_w,tb_y),(tb_x+tb_w,tb_y+tb_h),(tb_x,tb_y+tb_h)],
        close=True, dxfattribs={"color":7}
    )
    # Dividers
    for dy in [10, 20, 30, 40, 50]:
        msp.add_line((tb_x, tb_y+dy), (tb_x+tb_w, tb_y+dy), dxfattribs={"color":7})
    msp.add_line((tb_x+40, tb_y+40), (tb_x+40, tb_y+60), dxfattribs={"color":7})
    msp.add_line((tb_x+40, tb_y+20), (tb_x+40, tb_y+40), dxfattribs={"color":7})

    # Title block text
    def tb_txt(x, y, txt, h=2.5, bold=False):
        t = msp.add_text(txt, dxfattribs={"height": h, "color":7})
        t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_LEFT)

    tb_txt(tb_x+2, tb_y+55, f"CLIENT:  {pi.get('client','')}", 2.8)
    tb_txt(tb_x+2, tb_y+45, f"MANUFACTURER:  {pi.get('manufacturer','')}", 2.2)
    tb_txt(tb_x+2, tb_y+35, f"PROJECT:  {pi.get('project','')}", 2.5)
    tb_txt(tb_x+2, tb_y+25, f"TITLE:  {sheet_title}", 2.5)
    tb_txt(tb_x+2, tb_y+15, f"DWG NO:  {pi.get('dwg_no','')}", 2.2)
    tb_txt(tb_x+2, tb_y+5,  f"SHEET: {sheet_no:02d}  N.SHEET: {total_sheets:02d}  REV: {pi.get('rev','0')}", 2.2)
    tb_txt(tb_x+42, tb_y+45, f"PANEL NO: {pi.get('panel_no','')}", 2.2)
    tb_txt(tb_x+42, tb_y+35, f"PANEL TAG: {pi.get('panel_tag','')}", 2.2)
    tb_txt(tb_x+42, tb_y+25, f"DATE: {pi.get('date','')}", 2.2)
    tb_txt(tb_x+42, tb_y+15, f"DESIGNED: {pi.get('designed_by','')}  CHK: {pi.get('checked_by','')}", 2.0)
    tb_txt(tb_x+42, tb_y+5,  f"APPROVED: {pi.get('approved_by','')}", 2.0)


def generate_dxf(all_fields):
    """Generate multi-sheet DXF (one layout per sheet)."""
    doc = ezdxf.new("R2010")
    doc.units = 4  # mm
    pi = all_fields.get("project_info", {})
    dl = all_fields.get("drawing_list", [])
    bom = all_fields.get("bom", [])
    spec = all_fields.get("panel_spec", {})
    di = all_fields.get("di_channels", [])
    do_ch = all_fields.get("do_channels", [])
    total = len(dl) if dl else 13
    W, H = 420, 297  # A3 mm

    def new_layout(name):
        try:
            ly = doc.layouts.new(name)
        except:
            ly = doc.layouts.get(name)
        return ly.get_modelspace() if name == "Model" else ly

    msp = doc.modelspace()

    # ── SHEET 1: TITLE ──────────────────────────────────
    draw_title_block_dxf(msp, all_fields, 1, "TITLE SHEET", total, W, H)
    t = msp.add_text("REMOTE TERMINAL UNIT", dxfattribs={"height":18, "color":7})
    t.set_placement((W/2-65, H/2+15), align=TextEntityAlignment.MIDDLE_LEFT)
    t2 = msp.add_text(pi.get("project",""), dxfattribs={"height":12, "color":7})
    t2.set_placement((W/2-40, H/2-10), align=TextEntityAlignment.MIDDLE_LEFT)

    # ── SHEET 2: DRAWING LIST ────────────────────────────
    ly2 = doc.layouts.new("DRAWING LIST")
    ms2 = ly2.get_modelspace()
    draw_title_block_dxf(ms2, all_fields, 2, "DRAWING LIST", total, W, H)
    ms2.add_text("DRAWING LIST", dxfattribs={"height":8, "color":7}).set_placement(
        (W/2-30, H-25), align=TextEntityAlignment.MIDDLE_LEFT)
    # Table headers
    cols = [30,60,80,20,15]
    x_starts = [15, 45, 105, 185, 205]
    headers = ["SL.NO", "DRAWING NUMBER", "DESCRIPTION", "SHEET NO", "REV"]
    y_hdr = H-40
    for i,(h_txt,xs) in enumerate(zip(headers,x_starts)):
        ms2.add_text(h_txt, dxfattribs={"height":2.5,"color":7}).set_placement(
            (xs+1, y_hdr-3), align=TextEntityAlignment.MIDDLE_LEFT)
        ms2.add_lwpolyline([(xs,y_hdr-6),(xs+cols[i],y_hdr-6),
                            (xs+cols[i],y_hdr),(xs,y_hdr)], close=True, dxfattribs={"color":7})
    for idx, row in enumerate(dl[:20]):
        y = y_hdr - 6 - (idx+1)*8
        vals = [row.get("sl_no",""), pi.get("dwg_no",""), row.get("description",""),
                row.get("sheet_no",""), row.get("rev","0")]
        for i,(v,xs) in enumerate(zip(vals,x_starts)):
            ms2.add_text(str(v), dxfattribs={"height":2.5,"color":7}).set_placement(
                (xs+1, y+2), align=TextEntityAlignment.MIDDLE_LEFT)
            ms2.add_lwpolyline([(xs,y),(xs+cols[i],y),(xs+cols[i],y+6),(xs,y+6)],
                close=True, dxfattribs={"color":7})

    # ── SHEET 3: PANEL SPEC ──────────────────────────────
    ly3 = doc.layouts.new("PANEL SPEC")
    ms3 = ly3.get_modelspace()
    draw_title_block_dxf(ms3, all_fields, 3, "PANEL SPECIFICATION", total, W, H)
    ms3.add_text("PANEL SPECIFICATION", dxfattribs={"height":7,"color":7}).set_placement(
        (W/2-35, H-25), align=TextEntityAlignment.MIDDLE_LEFT)
    spec_rows = [
        ("1", "MANUFACTURER", pi.get("manufacturer","")),
        ("2", "ENCLOSURE DIMENSION", spec.get("enclosure_dimension","")),
        ("3", "CONSTRUCTION", spec.get("construction","")),
        ("4a","WIRING - CONTROL SIGNALS", spec.get("wiring_control","")),
        ("4b","WIRING - AC POWER CIRCUITS", spec.get("wiring_ac_power","")),
        ("4c","WIRING - DC POWER CIRCUITS", spec.get("wiring_dc_power","")),
        ("4d","WIRING - EARTHING CIRCUITS", spec.get("wiring_earthing","")),
    ]
    y_s = H-45
    for sl, label, val in spec_rows:
        ms3.add_lwpolyline([(15,y_s),(40,y_s),(40,y_s+8),(15,y_s+8)], close=True, dxfattribs={"color":7})
        ms3.add_lwpolyline([(40,y_s),(120,y_s),(120,y_s+8),(40,y_s+8)], close=True, dxfattribs={"color":7})
        ms3.add_lwpolyline([(120,y_s),(W-140,y_s),(W-140,y_s+8),(120,y_s+8)], close=True, dxfattribs={"color":7})
        ms3.add_text(sl, dxfattribs={"height":2.5,"color":7}).set_placement((17,y_s+3), align=TextEntityAlignment.MIDDLE_LEFT)
        ms3.add_text(label, dxfattribs={"height":2.5,"color":7}).set_placement((42,y_s+3), align=TextEntityAlignment.MIDDLE_LEFT)
        ms3.add_text(val[:60], dxfattribs={"height":2.2,"color":7}).set_placement((122,y_s+3), align=TextEntityAlignment.MIDDLE_LEFT)
        y_s -= 10

    # ── SHEET 4: BOM ─────────────────────────────────────
    ly4 = doc.layouts.new("BOM")
    ms4 = ly4.get_modelspace()
    draw_title_block_dxf(ms4, all_fields, 4, "BILL OF MATERIALS", total, W, H)
    ms4.add_text("BILL OF MATERIALS", dxfattribs={"height":7,"color":7}).set_placement(
        (W/2-32, H-25), align=TextEntityAlignment.MIDDLE_LEFT)
    bom_cols  = [12,30,160,20,30]
    bom_xs    = [15,27,57,217,237]
    bom_hdrs  = ["SL.NO","PANEL TAG","DESCRIPTION","QTY","MAKE"]
    y_b = H-42
    for h_txt,xs,cw in zip(bom_hdrs,bom_xs,bom_cols):
        ms4.add_lwpolyline([(xs,y_b-6),(xs+cw,y_b-6),(xs+cw,y_b),(xs,y_b)],
            close=True, dxfattribs={"color":7})
        ms4.add_text(h_txt, dxfattribs={"height":2.5,"color":7}).set_placement(
            (xs+1,y_b-3), align=TextEntityAlignment.MIDDLE_LEFT)
    for idx, item in enumerate(bom[:18]):
        y_bom = y_b - 6 - (idx+1)*9
        vals = [item.get("sl_no",""), item.get("panel_tag",""),
                item.get("description","")[:65], item.get("qty",""), item.get("make","")]
        for v,xs,cw in zip(vals,bom_xs,bom_cols):
            ms4.add_lwpolyline([(xs,y_bom),(xs+cw,y_bom),(xs+cw,y_bom+7),(xs,y_bom+7)],
                close=True, dxfattribs={"color":7})
            ms4.add_text(str(v), dxfattribs={"height":2.2,"color":7}).set_placement(
                (xs+1,y_bom+2.5), align=TextEntityAlignment.MIDDLE_LEFT)

    # ── SHEET 5: DIGITAL INPUT ───────────────────────────
    if di:
        ly5 = doc.layouts.new("DIGITAL INPUT")
        ms5 = ly5.get_modelspace()
        draw_title_block_dxf(ms5, all_fields, 5, "DIGITAL INPUT", total, W, H)
        ms5.add_text("DIGITAL INPUT", dxfattribs={"height":7,"color":7}).set_placement(
            (W/2-25, H-25), align=TextEntityAlignment.MIDDLE_LEFT)
        # RTU box
        ms5.add_lwpolyline([(80,50),(W-150,50),(W-150,H-30),(80,H-30)],
            close=True, dxfattribs={"color":7,"linetype":"DASHED"})
        ms5.add_text("AXION-2240", dxfattribs={"height":3.5,"color":7}).set_placement(
            (W/2-20, H-33), align=TextEntityAlignment.MIDDLE_LEFT)
        # DI channels
        for idx, ch in enumerate(di[:24]):
            col = idx // 12
            row = idx % 12
            x_tb  = 15 + col*160
            x_rtu = 100 + col*160
            y_ch  = H - 45 - row*16
            # Terminal
            ms5.add_circle((x_tb+5, y_ch), 2.5, dxfattribs={"color":3})
            ms5.add_text(ch.get("terminal",""), dxfattribs={"height":2,"color":7}).set_placement(
                (x_tb+10, y_ch), align=TextEntityAlignment.MIDDLE_LEFT)
            # Wire
            ms5.add_line((x_tb+10, y_ch), (x_rtu-5, y_ch), dxfattribs={"color":1})
            # RTU connector
            ms5.add_text(ch.get("connector",""), dxfattribs={"height":2,"color":7}).set_placement(
                (x_rtu-3, y_ch+2), align=TextEntityAlignment.MIDDLE_LEFT)
            # Input symbol (arrow)
            ms5.add_line((x_rtu+8, y_ch), (x_rtu+18, y_ch), dxfattribs={"color":5})
            # Label
            ms5.add_text(f"{ch.get('channel','')} — {ch.get('label','SPARE')}",
                dxfattribs={"height":2,"color":7}).set_placement(
                (x_rtu+20, y_ch), align=TextEntityAlignment.MIDDLE_LEFT)

    # ── SHEET 6: DIGITAL OUTPUT ──────────────────────────
    if do_ch:
        ly6 = doc.layouts.new("DIGITAL OUTPUT")
        ms6 = ly6.get_modelspace()
        draw_title_block_dxf(ms6, all_fields, 6, "DIGITAL OUTPUT", total, W, H)
        ms6.add_text("DIGITAL OUTPUT", dxfattribs={"height":7,"color":7}).set_placement(
            (W/2-25, H-25), align=TextEntityAlignment.MIDDLE_LEFT)
        ms6.add_lwpolyline([(80,50),(W-150,50),(W-150,H-30),(80,H-30)],
            close=True, dxfattribs={"color":7,"linetype":"DASHED"})
        ms6.add_text("AXION-2240", dxfattribs={"height":3.5,"color":7}).set_placement(
            (W/2-20, H-33), align=TextEntityAlignment.MIDDLE_LEFT)
        for idx, ch in enumerate(do_ch[:16]):
            col = idx // 8
            row = idx % 8
            x_tb  = 15 + col*180
            x_rtu = 100 + col*180
            y_ch  = H - 45 - row*22
            ms6.add_circle((x_tb+5, y_ch), 2.5, dxfattribs={"color":3})
            ms6.add_text(ch.get("terminal",""), dxfattribs={"height":2,"color":7}).set_placement(
                (x_tb+10, y_ch), align=TextEntityAlignment.MIDDLE_LEFT)
            ms6.add_line((x_tb+10, y_ch), (x_rtu-5, y_ch), dxfattribs={"color":1})
            ms6.add_text(ch.get("connector",""), dxfattribs={"height":2,"color":7}).set_placement(
                (x_rtu, y_ch+2), align=TextEntityAlignment.MIDDLE_LEFT)
            # Output relay symbol
            ms6.add_lwpolyline([
                (x_rtu+8, y_ch-3),(x_rtu+18, y_ch-3),
                (x_rtu+18, y_ch+3),(x_rtu+8, y_ch+3)
            ], close=True, dxfattribs={"color":5})
            ms6.add_text(f"{ch.get('channel','')} — {ch.get('label','SPARE')}",
                dxfattribs={"height":2,"color":7}).set_placement(
                (x_rtu+22, y_ch), align=TextEntityAlignment.MIDDLE_LEFT)

    dxf_stream = io.StringIO()
    doc.write(dxf_stream)
    return dxf_stream.getvalue()


# ─────────────────────────────────────────────
# PDF GENERATION ENGINE
# ─────────────────────────────────────────────
def draw_title_block_pdf(c, fields, sheet_no, sheet_title, total_sheets):
    """Draw A3 landscape border + title block on reportlab canvas."""
    pi = fields.get("project_info", {})
    W_mm, H_mm = 420*mm, 297*mm

    # Borders
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.rect(5*mm, 5*mm, W_mm-10*mm, H_mm-10*mm)
    c.setLineWidth(0.5)
    c.rect(10*mm, 10*mm, W_mm-20*mm, H_mm-20*mm)

    # Title block
    tb_x = W_mm - 130*mm
    tb_y = 10*mm
    tb_w = 120*mm
    tb_h = 60*mm
    c.setLineWidth(0.5)
    c.rect(tb_x, tb_y, tb_w, tb_h)

    # Horizontal dividers
    for dy in [10, 20, 30, 40, 50]:
        c.line(tb_x, tb_y+dy*mm, tb_x+tb_w, tb_y+dy*mm)

    # Vertical divider
    c.line(tb_x+40*mm, tb_y+20*mm, tb_x+40*mm, tb_y+60*mm)

    # Title block text
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.black)

    def tbtext(x_mm, y_mm, txt, size=6.5, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x_mm*mm, y_mm*mm, str(txt)[:55])

    tbtext(tb_x/mm+1, tb_y/mm+53, f"CLIENT:")
    c.setFont("Helvetica", 7)
    c.drawString((tb_x/mm+20)*mm, (tb_y/mm+53)*mm, pi.get("client",""))

    tbtext(tb_x/mm+1, tb_y/mm+43, "MANUFACTURER:", 5.5)
    c.setFont("Helvetica", 6)
    c.drawString((tb_x/mm+18)*mm, (tb_y/mm+43)*mm, pi.get("manufacturer","")[:30])

    tbtext(tb_x/mm+1, tb_y/mm+33, "PROJECT:")
    c.setFont("Helvetica", 7)
    c.drawString((tb_x/mm+20)*mm, (tb_y/mm+33)*mm, pi.get("project","")[:30])

    tbtext(tb_x/mm+1, tb_y/mm+23, f"TITLE:")
    c.setFont("Helvetica-Bold", 7)
    c.drawString((tb_x/mm+15)*mm, (tb_y/mm+23)*mm, sheet_title)

    tbtext(tb_x/mm+1, tb_y/mm+8, f"DWG NO: {pi.get('dwg_no','')}", 5.5)
    tbtext(tb_x/mm+1, tb_y/mm+2, f"SHEET: {sheet_no:02d}   N.SHEET: {total_sheets:02d}   REV: {pi.get('rev','0')}", 5)

    # Right side of title block
    tbtext(tb_x/mm+42, tb_y/mm+53, f"PANEL NO: {pi.get('panel_no','')}", 5.5)
    tbtext(tb_x/mm+42, tb_y/mm+43, f"PANEL TAG: {pi.get('panel_tag','')}", 5.5)
    tbtext(tb_x/mm+42, tb_y/mm+33, f"DATE: {pi.get('date','')}", 5.5)

    # Designer row
    c.line(tb_x+40*mm, tb_y+20*mm, tb_x+tb_w, tb_y+20*mm)
    c.line(tb_x+40*mm, tb_y+30*mm, tb_x+tb_w, tb_y+30*mm)
    for label, name, y_off in [
        ("DESIGNED", pi.get("designed_by",""), 25),
        ("CHECKED",  pi.get("checked_by",""),  15),
        ("APPROVED", pi.get("approved_by",""),  5),
    ]:
        tbtext(tb_x/mm+42, tb_y/mm+y_off, f"{label}: {name}", 5)

    # Manufacturer banner (left side vertical)
    c.saveState()
    c.setFont("Helvetica-Bold", 5)
    c.drawString(12*mm, 15*mm, pi.get("manufacturer","") + "  |  " + pi.get("project",""))
    c.restoreState()


def generate_pdf(all_fields):
    """Generate multi-sheet A3 PDF."""
    pi   = all_fields.get("project_info", {})
    dl   = all_fields.get("drawing_list", [])
    bom  = all_fields.get("bom", [])
    spec = all_fields.get("panel_spec", {})
    di   = all_fields.get("di_channels", [])
    do_ch= all_fields.get("do_channels", [])
    total = max(len(dl), 2)
    W_mm, H_mm = 420*mm, 297*mm

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=landscape(A3))

    # ── SHEET 1: TITLE ──────────────────────────────────
    draw_title_block_pdf(c, all_fields, 1, "TITLE SHEET", total)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(W_mm/2, H_mm/2+25*mm, "REMOTE TERMINAL UNIT")
    c.setFont("Helvetica", 18)
    c.drawCentredString(W_mm/2, H_mm/2, pi.get("project",""))
    c.showPage()

    # ── SHEET 2: DRAWING LIST ────────────────────────────
    draw_title_block_pdf(c, all_fields, 2, "DRAWING LIST", total)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W_mm/2, H_mm-28*mm, "DRAWING LIST")
    # Table
    col_ws = [20*mm, 70*mm, 100*mm, 25*mm, 20*mm]
    headers = ["SL.NO", "DRAWING NUMBER", "DESCRIPTION", "SHEET NO", "REV"]
    x0, y0 = 15*mm, H_mm-42*mm
    row_h = 10*mm
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.Color(0.12, 0.31, 0.49))
    x_cur = x0
    for cw in col_ws:
        c.rect(x_cur, y0, cw, row_h, fill=1)
        x_cur += cw
    c.setFillColor(colors.white)
    x_cur = x0
    for h_txt, cw in zip(headers, col_ws):
        c.drawCentredString(x_cur + cw/2, y0+3*mm, h_txt)
        x_cur += cw
    c.setFillColor(colors.black)
    for idx, row in enumerate(dl[:20]):
        y_row = y0 - (idx+1)*row_h
        vals = [row.get("sl_no",""), pi.get("dwg_no",""),
                row.get("description",""), row.get("sheet_no",""), row.get("rev","0")]
        x_cur = x0
        shade = colors.Color(0.93,0.96,0.99) if idx%2==0 else colors.white
        for v, cw in zip(vals, col_ws):
            c.setFillColor(shade)
            c.rect(x_cur, y_row, cw, row_h, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 7)
            c.drawCentredString(x_cur+cw/2, y_row+3*mm, str(v)[:30])
            x_cur += cw
    c.showPage()

    # ── SHEET 3: PANEL SPEC ──────────────────────────────
    draw_title_block_pdf(c, all_fields, 3, "PANEL SPECIFICATION", total)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W_mm/2, H_mm-28*mm, "PANEL SPECIFICATION")
    spec_items = [
        ("1",  "MANUFACTURER",           pi.get("manufacturer","")),
        ("2",  "ENCLOSURE DIMENSION",     spec.get("enclosure_dimension","")),
        ("3",  "CONSTRUCTION",            spec.get("construction","")),
        ("4a", "WIRING - CONTROL",        spec.get("wiring_control","")),
        ("4b", "WIRING - AC POWER",       spec.get("wiring_ac_power","")),
        ("4c", "WIRING - DC POWER",       spec.get("wiring_dc_power","")),
        ("4d", "WIRING - EARTHING",       spec.get("wiring_earthing","")),
    ]
    y_s = H_mm - 48*mm
    for sl, label, val in spec_items:
        c.setFillColor(colors.Color(0.93,0.96,0.99))
        c.rect(15*mm, y_s-2*mm, 25*mm, 9*mm, fill=1)
        c.rect(40*mm, y_s-2*mm, 90*mm, 9*mm, fill=1)
        c.setFillColor(colors.white)
        c.rect(130*mm, y_s-2*mm, W_mm-155*mm-130*mm, 9*mm, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(17*mm, y_s+1*mm, sl)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(42*mm, y_s+1*mm, label)
        c.setFont("Helvetica", 7)
        c.drawString(132*mm, y_s+1*mm, str(val)[:80])
        y_s -= 12*mm
    c.showPage()

    # ── SHEET 4: BOM ─────────────────────────────────────
    draw_title_block_pdf(c, all_fields, 4, "BILL OF MATERIALS", total)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W_mm/2, H_mm-28*mm, "BILL OF MATERIALS")
    bom_col_ws = [15*mm, 35*mm, 175*mm, 15*mm, 35*mm]
    bom_hdrs   = ["SL.NO", "PANEL TAG", "DESCRIPTION", "QTY", "MAKE"]
    x0, y0 = 15*mm, H_mm-44*mm
    row_h = 9*mm
    c.setFillColor(colors.Color(0.12,0.31,0.49))
    x_cur = x0
    for cw in bom_col_ws:
        c.rect(x_cur, y0, cw, row_h, fill=1)
        x_cur += cw
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7)
    x_cur = x0
    for h_txt, cw in zip(bom_hdrs, bom_col_ws):
        c.drawCentredString(x_cur+cw/2, y0+3*mm, h_txt)
        x_cur += cw
    c.setFillColor(colors.black)
    for idx, item in enumerate(bom[:18]):
        y_row = y0 - (idx+1)*row_h
        vals = [item.get("sl_no",""), item.get("panel_tag",""),
                item.get("description","")[:70], item.get("qty",""), item.get("make","")]
        x_cur = x0
        shade = colors.Color(0.96,0.98,1.0) if idx%2==0 else colors.white
        for v, cw in zip(vals, bom_col_ws):
            c.setFillColor(shade)
            c.rect(x_cur, y_row, cw, row_h, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 7)
            c.drawCentredString(x_cur+cw/2, y_row+2.5*mm, str(v))
            x_cur += cw
    c.showPage()

    # ── SHEET 5: DIGITAL INPUT ───────────────────────────
    if di:
        draw_title_block_pdf(c, all_fields, 5, "DIGITAL INPUT", total)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(W_mm/2, H_mm-28*mm, "DIGITAL INPUT")
        # RTU dashed box
        c.setDash(4, 3)
        c.rect(85*mm, 45*mm, W_mm-240*mm, H_mm-85*mm)
        c.setDash()
        c.setFont("Helvetica-Bold", 8)
        c.drawString(W_mm/2-15*mm, H_mm-38*mm, "AXION-2240")
        for idx, ch in enumerate(di[:24]):
            col = idx // 12
            row = idx % 12
            x_tb  = (15 + col*165)*mm
            x_rtu = (95 + col*165)*mm
            y_ch  = H_mm - (50 + row*16)*mm
            # Terminal circle
            c.setStrokeColor(colors.green)
            c.circle(x_tb+4*mm, y_ch, 2.5*mm)
            c.setStrokeColor(colors.black)
            c.setFont("Helvetica", 6)
            c.drawString(x_tb+8*mm, y_ch-1*mm, ch.get("terminal",""))
            # Wire
            c.setStrokeColor(colors.red)
            c.line(x_tb+12*mm, y_ch, x_rtu-3*mm, y_ch)
            c.setStrokeColor(colors.black)
            c.setFont("Helvetica", 6)
            c.drawString(x_rtu-2*mm, y_ch+1*mm, ch.get("connector",""))
            # Arrow symbol
            c.setStrokeColor(colors.blue)
            c.line(x_rtu+6*mm, y_ch, x_rtu+14*mm, y_ch)
            c.setStrokeColor(colors.black)
            # Channel label
            c.setFont("Helvetica", 5.5)
            label = f"{ch.get('channel','')}  {ch.get('label','SPARE')}"
            c.drawString(x_rtu+15*mm, y_ch-1*mm, label)
        c.showPage()

    # ── SHEET 6: DIGITAL OUTPUT ──────────────────────────
    if do_ch:
        draw_title_block_pdf(c, all_fields, 6, "DIGITAL OUTPUT", total)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(W_mm/2, H_mm-28*mm, "DIGITAL OUTPUT")
        c.setDash(4, 3)
        c.rect(85*mm, 45*mm, W_mm-240*mm, H_mm-85*mm)
        c.setDash()
        c.setFont("Helvetica-Bold", 8)
        c.drawString(W_mm/2-15*mm, H_mm-38*mm, "AXION-2240")
        for idx, ch in enumerate(do_ch[:16]):
            col = idx // 8
            row = idx % 8
            x_rtu = (90 + col*180)*mm
            x_tb  = (170 + col*180)*mm
            y_ch  = H_mm - (55 + row*22)*mm
            c.setFont("Helvetica", 6)
            c.drawString(x_rtu, y_ch+1*mm, ch.get("connector",""))
            # Relay symbol box
            c.setStrokeColor(colors.blue)
            c.rect(x_rtu+8*mm, y_ch-3*mm, 10*mm, 6*mm)
            c.setStrokeColor(colors.black)
            c.setFont("Helvetica", 5.5)
            c.drawString(x_rtu+9*mm, y_ch-1*mm, ch.get("channel","")[-4:])
            c.setStrokeColor(colors.red)
            c.line(x_rtu+18*mm, y_ch, x_tb-3*mm, y_ch)
            c.setStrokeColor(colors.green)
            c.circle(x_tb, y_ch, 2.5*mm)
            c.setStrokeColor(colors.black)
            c.setFont("Helvetica", 6)
            c.drawString(x_tb+4*mm, y_ch-1*mm, ch.get("terminal",""))
            c.setFont("Helvetica", 5.5)
            c.drawString(x_rtu-20*mm, y_ch-1*mm,
                f"{ch.get('channel','')}  {ch.get('label','SPARE')}")
        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────
# UI — MAIN APP
# ─────────────────────────────────────────────
st.title("⚡ RTU Drawing Template Engine")
st.caption("Upload a reference PDF → AI extracts all data → Edit fields or chat → Generate new PDF + DXF")

col_left, col_right = st.columns([1, 1], gap="large")

# ══════════════════════════════════════════
# LEFT COLUMN — UPLOAD + EDIT FIELDS
# ══════════════════════════════════════════
with col_left:
    st.subheader("📄 Step 1 — Upload Reference Drawing")
    uploaded = st.file_uploader("Upload RTU Drawing PDF", type=["pdf"])

    if uploaded and not st.session_state.pdf_extracted:
        with st.spinner("🔍 AI is reading your drawing..."):
            try:
                data = extract_from_pdf(uploaded)
                st.session_state.fields      = data
                st.session_state.bom_items   = data.get("bom", [])
                st.session_state.di_channels = data.get("di_channels", [])
                st.session_state.do_channels = data.get("do_channels", [])
                st.session_state.drawing_list= data.get("drawing_list", [])
                st.session_state.pdf_extracted = True
                st.success(f"✅ Extracted {len(st.session_state.bom_items)} BOM items, "
                           f"{len(st.session_state.di_channels)} DI channels, "
                           f"{len(st.session_state.do_channels)} DO channels")
            except Exception as e:
                st.error(f"Extraction error: {e}")

    if st.session_state.pdf_extracted:
        pi = st.session_state.fields.get("project_info", {})

        # ── PROJECT INFO ──────────────────────────────
        st.markdown('<div class="section-head">PROJECT INFORMATION</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            pi["client"]      = st.text_input("Client",       pi.get("client",""))
            pi["project"]     = st.text_input("Project",      pi.get("project",""))
            pi["panel_tag"]   = st.text_input("Panel Tag",    pi.get("panel_tag","RTU"))
            pi["panel_no"]    = st.text_input("Panel No.",    pi.get("panel_no","RTU"))
            pi["manufacturer"]= st.text_input("Manufacturer", pi.get("manufacturer",""))
        with c2:
            pi["dwg_no"]      = st.text_input("Drawing No.",  pi.get("dwg_no",""))
            pi["rev"]         = st.text_input("Revision",     pi.get("rev","0"))
            pi["date"]        = st.text_input("Date",         pi.get("date",""))
            pi["designed_by"] = st.text_input("Designed By",  pi.get("designed_by",""))
            pi["checked_by"]  = st.text_input("Checked By",   pi.get("checked_by",""))
            pi["approved_by"] = st.text_input("Approved By",  pi.get("approved_by",""))
        st.session_state.fields["project_info"] = pi

        # ── BOM ───────────────────────────────────────
        st.markdown('<div class="section-head">BILL OF MATERIALS</div>', unsafe_allow_html=True)
        bom_edit = st.session_state.bom_items
        for i, item in enumerate(bom_edit):
            bc1, bc2, bc3, bc4, bc5 = st.columns([1,2,5,1,2])
            with bc1: item["sl_no"]      = st.text_input("SL",  item.get("sl_no",""),  key=f"bsl{i}", label_visibility="collapsed")
            with bc2: item["panel_tag"]  = st.text_input("Tag", item.get("panel_tag",""), key=f"btag{i}", label_visibility="collapsed")
            with bc3: item["description"]= st.text_input("Desc",item.get("description",""), key=f"bdsc{i}", label_visibility="collapsed")
            with bc4: item["qty"]        = st.text_input("Qty", item.get("qty",""),    key=f"bqty{i}", label_visibility="collapsed")
            with bc5: item["make"]       = st.text_input("Make",item.get("make",""),   key=f"bmk{i}", label_visibility="collapsed")

        if st.button("➕ Add BOM Row"):
            st.session_state.bom_items.append({"sl_no":"","panel_tag":"","description":"","qty":"","make":""})
            st.rerun()

        # ── DI CHANNELS ───────────────────────────────
        st.markdown('<div class="section-head">DIGITAL INPUTS</div>', unsafe_allow_html=True)
        for i, ch in enumerate(st.session_state.di_channels):
            dc1, dc2, dc3 = st.columns([2,2,4])
            with dc1: ch["channel"]  = st.text_input("Ch",  ch.get("channel",""),  key=f"dic{i}", label_visibility="collapsed")
            with dc2: ch["terminal"] = st.text_input("TB",  ch.get("terminal",""), key=f"dit{i}", label_visibility="collapsed")
            with dc3: ch["label"]    = st.text_input("Lbl", ch.get("label","SPARE"), key=f"dil{i}", label_visibility="collapsed")

        # ── DO CHANNELS ───────────────────────────────
        st.markdown('<div class="section-head">DIGITAL OUTPUTS</div>', unsafe_allow_html=True)
        for i, ch in enumerate(st.session_state.do_channels):
            dc1, dc2, dc3 = st.columns([2,2,4])
            with dc1: ch["channel"]  = st.text_input("Ch",  ch.get("channel",""),  key=f"doc{i}", label_visibility="collapsed")
            with dc2: ch["terminal"] = st.text_input("TB",  ch.get("terminal",""), key=f"dot{i}", label_visibility="collapsed")
            with dc3: ch["label"]    = st.text_input("Lbl", ch.get("label","SPARE"), key=f"dol{i}", label_visibility="collapsed")


# ══════════════════════════════════════════
# RIGHT COLUMN — AI CHAT + GENERATE
# ══════════════════════════════════════════
with col_right:
    st.subheader("💬 Step 2 — AI Chat to Update Drawing")

    if not st.session_state.pdf_extracted:
        st.info("Upload a drawing PDF on the left to get started.")
    else:
        st.caption("Tell me what to change in plain English. Examples:")
        st.code(
            'Change client to "ADANI POWER"\n'
            'Set project to "220KV MUNDRA SS"\n'
            'Update drawing number to PSCE_ADANI_RTU_E_020011001\n'
            'Set IN01 label to "52-1 CLOSE STATUS"\n'
            'Change designed by to RK, date to 05.03.2026\n'
            'Update OUT01 label to "TRIP BREAKER 1"',
            language="text"
        )

        # Chat history display
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history[-8:]:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

        # Chat input
        user_input = st.text_input("Your instruction:", key="chat_input",
                                    placeholder="e.g. Change client to NTPC, project to 400KV SIPAT SS")
        if st.button("▶ Apply Change", use_container_width=True) and user_input:
            with st.spinner("Updating fields..."):
                # Bundle all current fields
                all_fields = {
                    **st.session_state.fields,
                    "bom":         st.session_state.bom_items,
                    "di_channels": st.session_state.di_channels,
                    "do_channels": st.session_state.do_channels,
                    "drawing_list":st.session_state.drawing_list,
                }
                try:
                    updated, summary = process_chat_command(user_input, all_fields)
                    st.session_state.fields       = updated
                    st.session_state.bom_items    = updated.get("bom", st.session_state.bom_items)
                    st.session_state.di_channels  = updated.get("di_channels", st.session_state.di_channels)
                    st.session_state.do_channels  = updated.get("do_channels", st.session_state.do_channels)
                    st.session_state.drawing_list = updated.get("drawing_list", st.session_state.drawing_list)
                    st.session_state.chat_history.append({"role":"user",    "content": user_input})
                    st.session_state.chat_history.append({"role":"assistant","content": f"✅ Updated:\n{summary}"})
                    st.rerun()
                except Exception as e:
                    st.error(f"Update error: {e}")

        st.divider()

        # ── GENERATE OUTPUTS ──────────────────────────
        st.subheader("📥 Step 3 — Generate Drawing Package")

        proj = st.session_state.fields.get("project_info",{})
        st.markdown(f"""
        **Current Settings:**
        - Client: `{proj.get('client','-')}`
        - Project: `{proj.get('project','-')}`
        - DWG No.: `{proj.get('dwg_no','-')}`
        - DI Channels: `{len(st.session_state.di_channels)}`
        - DO Channels: `{len(st.session_state.do_channels)}`
        - BOM Items: `{len(st.session_state.bom_items)}`
        """)

        if st.button("⚡ Generate PDF + DXF", type="primary", use_container_width=True):
            all_fields = {
                **st.session_state.fields,
                "bom":          st.session_state.bom_items,
                "di_channels":  st.session_state.di_channels,
                "do_channels":  st.session_state.do_channels,
                "drawing_list": st.session_state.drawing_list,
            }
            with st.spinner("Generating drawing package..."):
                try:
                    pdf_bytes = generate_pdf(all_fields)
                    dxf_str   = generate_dxf(all_fields)
                    dwg = proj.get("dwg_no","RTU_Drawing").replace("/","_")
                    st.success("✅ Drawing package generated!")
                    dl1, dl2 = st.columns(2)
                    with dl1:
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_bytes,
                            file_name=f"{dwg}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with dl2:
                        st.download_button(
                            label="📐 Download DXF",
                            data=dxf_str,
                            file_name=f"{dwg}.dxf",
                            mime="application/dxf",
                            use_container_width=True
                        )
                except Exception as e:
                    import traceback
                    st.error(f"Generation error: {e}")
                    st.code(traceback.format_exc())

        st.divider()

        # ── RESET ─────────────────────────────────────
        if st.button("🔄 Load New Drawing", use_container_width=True):
            for k in ["fields","bom_items","di_channels","do_channels",
                      "chat_history","pdf_extracted","drawing_list"]:
                st.session_state[k] = {} if k == "fields" else []
            st.session_state.pdf_extracted = False
            st.rerun()
