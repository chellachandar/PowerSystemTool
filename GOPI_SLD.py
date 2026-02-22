import streamlit as st
import pandas as pd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

def create_block_definitions(doc):
    """Creates reusable symbols within the CAD file."""
    # 1. Circuit Breaker Block
    cb_block = doc.blocks.new(name='CB_SYMBOL')
    cb_block.add_lwpolyline([(-2, -2), (2, -2), (2, 2), (-2, 2)], close=True, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    
    # 2. Current Transformer Block
    ct_block = doc.blocks.new(name='CT_SYMBOL')
    ct_block.add_circle((0, 0), radius=1.5, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

    # 3. Transformer Block (Two overlapping circles)
    xfmr_block = doc.blocks.new(name='XFMR_SYMBOL')
    xfmr_block.add_circle((0, 0), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    xfmr_block.add_circle((0, -5), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

def create_block_sld(df):
    doc = ezdxf.new('R2010')
    
    # Setup Layers
    doc.layers.new(name='PRIMARY_EQUIPMENT', dxfattribs={'color': 7})
    doc.layers.new(name='BUSBARS', dxfattribs={'color': 1})
    doc.layers.new(name='ANNOTATION', dxfattribs={'color': 4})
    
    # Initialize Block Definitions
    create_block_definitions(doc)
    msp = doc.modelspace()

    # Vertical Offsets
    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR_TOP = 70, 55, 15
    
    for _, row in df.iterrows():
        x = row['X_Pos']
        b_type = str(row['Type']).upper()
        
        # 1. Add Busbars
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        
        # 2. Insert CB Block
        msp.add_blockref('CB_SYMBOL', (x, Y_CB))
        msp.add_text(row['CB_Rating'], dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, Y_CB))

        # 3. Insert CT Block
        msp.add_blockref('CT_SYMBOL', (x, Y_CT))
        msp.add_text(row['CT_Ratio'], dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, Y_CT))
        
        # 4. Insert Transformer Block if applicable
        if b_type == "XFMR":
            msp.add_blockref('XFMR_SYMBOL', (x, Y_TR_TOP))
        
        # 5. Connection Lines
        bottom_y = 5 if b_type == "XFMR" else 20
        msp.add_line((x, Y_BUS_A), (x, bottom_y), dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
        
        # 6. Bay Label
        msp.add_text(row['Bay_Name'], dxfattribs={'layer': 'ANNOTATION', 'height': 2.5}).set_placement((x, 110))

    return doc

# --- STREAMLIT UI ---
st.set_page_config(page_title="Pro Block SLD Generator", layout="wide")
st.title("⚡ Senior Power System Professional: SLD Automation")
st.markdown("This version uses **Block Definitions** and **Layer Management** for professional AutoCAD editing.")

uploaded_file = st.file_uploader("Upload Substation Excel", type="xlsx")

if uploaded_file:
    data = pd.read_excel(uploaded_file)
    if st.button("Generate Final Pro Outputs"):
        doc = create_block_sld(data)
        
        dxf_buff = io.StringIO()
        doc.write(dxf_buff)
        
        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
        pdf_buff = io.BytesIO()
        fig.savefig(pdf_buff, format='pdf')
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download Block-Based DXF", dxf_buff.getvalue(), "Substation_Final.dxf")
        with col2:
            st.download_button("📥 Download Final PDF", pdf_buff.getvalue(), "Substation_Final.pdf")
