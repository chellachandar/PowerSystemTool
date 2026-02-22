import streamlit as st
import pandas as pd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

# --- 1. SYMBOL ENGINE ---
def create_block_definitions(doc):
    cb_block = doc.blocks.new(name='CB_SYMBOL')
    cb_block.add_lwpolyline([(-2, -2), (2, -2), (2, 2), (-2, 2)], close=True, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    
    ct_block = doc.blocks.new(name='CT_SYMBOL')
    ct_block.add_circle((0, 0), radius=1.5, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

    xfmr_block = doc.blocks.new(name='XFMR_SYMBOL')
    xfmr_block.add_circle((0, 0), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    xfmr_block.add_circle((0, -5), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

# --- 2. DRAFTING ENGINE ---
def create_block_sld(df):
    # Ensure headers are clean
    df.columns = df.columns.astype(str).str.strip()
    
    doc = ezdxf.new('R2010')
    doc.layers.new(name='PRIMARY_EQUIPMENT', dxfattribs={'color': 7}) 
    doc.layers.new(name='BUSBARS', dxfattribs={'color': 1})           
    doc.layers.new(name='ANNOTATION', dxfattribs={'color': 4})        
    doc.layers.new(name='LEGEND', dxfattribs={'color': 2})            
    
    create_block_definitions(doc)
    msp = doc.modelspace()

    # Dynamic Legend Positioning based on the cleaned X_Pos column
    leg_x = df['X_Pos'].max() + 50 if 'X_Pos' in df.columns else 300
    leg_y = 100

    for _, row in df.iterrows():
        x = row.get('X_Pos', 0)
        b_type = str(row.get('Type', 'LINE')).upper()
        
        # 1. Busbars (Red Layer)
        msp.add_line((x-20, 100), (x+20, 100), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        msp.add_line((x-20, 92), (x+20, 92), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        
        # 2. Block Placement
        msp.add_blockref('CB_SYMBOL', (x, 70))
        msp.add_blockref('CT_SYMBOL', (x, 55))
        if "XFMR" in b_type:
            msp.add_blockref('XFMR_SYMBOL', (x, 15))
        
        # 3. Connectivity & Annotations
        bot_y = 5 if "XFMR" in b_type else 20
        msp.add_line((x, 100), (x, bot_y), dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
        msp.add_text(str(row.get('Bay_Name', '')), dxfattribs={'layer': 'ANNOTATION', 'height': 2.5}).set_placement((x, 110))
        msp.add_text(str(row.get('CB_Rating', '')), dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, 70))
        msp.add_text(str(row.get('CT_Ratio', '')), dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, 55))

    # 4. Add Legend
    msp.add_text("LEGEND", dxfattribs={'layer': 'LEGEND', 'height': 3}).set_placement((leg_x, leg_y))
    for i, (c, n) in enumerate([("CB", "Circuit Breaker"), ("CT", "Current Transformer"), ("XFMR", "Transformer")]):
        msp.add_text(f"{c}: {n}", dxfattribs={'layer': 'LEGEND', 'height': 2}).set_placement((leg_x, leg_y - 10 - (i*5)))
        
    return doc

# --- 3. STREAMLIT UI WITH AUTO-HEADER DETECTION ---
st.set_page_config(page_title="Power SLD Automator", layout="wide")
st.title("⚡ Senior Power System Professional: SLD Automation")

uploaded_file = st.file_uploader("Upload Substation Data (Do not edit your file)", type=["xlsx", "csv"])

if uploaded_file:
    # Read the file to find where the actual headers start
    if uploaded_file.name.endswith('.csv'):
        temp_df = pd.read_csv(uploaded_file, header=None)
    else:
        temp_df = pd.read_excel(uploaded_file, header=None)

    # Search for the row containing "X_Pos"
    header_row = 0
    for idx, row in temp_df.iterrows():
        if "X_Pos" in [str(val).strip() for val in row.values]:
            header_row = idx
            break
    
    # Re-read the file correctly starting from the detected header row
    uploaded_file.seek(0)
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, header=header_row)
    else:
        df = pd.read_excel(uploaded_file, header=header_row)
    
    df.columns = df.columns.astype(str).str.strip()
    st.write("### Verified Data Preview", df.head())
    
    if st.button("Generate Professional SLD"):
        doc = create_block_sld(df)
        
        # DXF Output
        dxf_io = io.StringIO()
        doc.write(dxf_io)
        
        # PDF Output
        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
        pdf_io = io.BytesIO()
        fig.savefig(pdf_io, format='pdf', dpi=300)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download AutoCAD (.dxf)", dxf_io.getvalue(), "Substation_Output.dxf")
        with col2:
            st.download_button("📥 Download PDF Report", pdf_io.getvalue(), "Substation_Report.pdf")
