import streamlit as st
import pandas as pd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

# --- 1. SYMBOL ENGINE ---
def create_block_definitions(doc):
    """Defines professional symbols as reusable blocks."""
    # Circuit Breaker (CB)
    cb_block = doc.blocks.new(name='CB_SYMBOL')
    cb_block.add_lwpolyline([(-2, -2), (2, -2), (2, 2), (-2, 2)], close=True, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    
    # Current Transformer (CT)
    ct_block = doc.blocks.new(name='CT_SYMBOL')
    ct_block.add_circle((0, 0), radius=1.5, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

    # Transformer (XFMR)
    xfmr_block = doc.blocks.new(name='XFMR_SYMBOL')
    xfmr_block.add_circle((0, 0), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    xfmr_block.add_circle((0, -5), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

# --- 2. DRAFTING ENGINE ---
def create_block_sld(df):
    # --- CRITICAL: Robust Header Cleaning ---
    # This fixes the KeyError by removing hidden spaces from column names
    df.columns = df.columns.astype(str).str.strip()
    
    doc = ezdxf.new('R2010')
    
    # Professional Layer Setup
    doc.layers.new(name='PRIMARY_EQUIPMENT', dxfattribs={'color': 7}) 
    doc.layers.new(name='BUSBARS', dxfattribs={'color': 1})           
    doc.layers.new(name='ANNOTATION', dxfattribs={'color': 4})        
    doc.layers.new(name='LEGEND', dxfattribs={'color': 2})            
    
    create_block_definitions(doc)
    msp = doc.modelspace()

    # Calculate Legend Position (Safety check for X_Pos)
    if 'X_Pos' in df.columns:
        leg_x = df['X_Pos'].max() + 50
    else:
        # Fallback if cleaning failed
        leg_x = 300 
    leg_y = 100

    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR_TOP = 70, 55, 15
    
    for _, row in df.iterrows():
        # Using .get() ensures the loop doesn't crash on individual rows
        x = row.get('X_Pos', 0)
        b_type = str(row.get('Type', 'LINE')).upper()
        cb_val = str(row.get('CB_Rating', ''))
        ct_val = str(row.get('CT_Ratio', ''))
        bay_name = str(row.get('Bay_Name', 'Bay'))
        
        # 1. Busbars
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        
        # 2. Equipment Placement
        msp.add_blockref('CB_SYMBOL', (x, Y_CB))
        msp.add_blockref('CT_SYMBOL', (x, Y_CT))
        
        if "XFMR" in b_type:
            msp.add_blockref('XFMR_SYMBOL', (x, Y_TR_TOP))
        
        # 3. Connections & Text
        bottom_y = 5 if "XFMR" in b_type else 20
        msp.add_line((x, Y_BUS_A), (x, bottom_y), dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
        
        msp.add_text(bay_name, dxfattribs={'layer': 'ANNOTATION', 'height': 2.5}).set_placement((x, 110))
        msp.add_text(cb_val, dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(ct_val, dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, Y_CT))

    # 4. Legend
    msp.add_text("LEGEND", dxfattribs={'layer': 'LEGEND', 'height': 3}).set_placement((leg_x, leg_y))
    items = [("CB", "Circuit Breaker"), ("CT", "Current Transformer"), ("XFMR", "Transformer")]
    for i, (code, name) in enumerate(items):
        msp.add_text(f"{code}: {name}", dxfattribs={'layer': 'LEGEND', 'height': 2}).set_placement((leg_x, leg_y - 10 - (i*5)))
        
    return doc

# --- 3. UI LAYER ---
st.set_page_config(page_title="Power SLD Automator", layout="wide")
st.title("⚡ Senior Power System Professional: SLD Automation")

uploaded_file = st.file_uploader("Upload Substation Data (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # Handle CSV or Excel specifically
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.write("### Data Preview", df.head())
        
        # Error check: verify columns before drawing
        df.columns = df.columns.astype(str).str.strip()
        if 'X_Pos' not in df.columns:
            st.error(f"Missing 'X_Pos' column. Found columns: {list(df.columns)}")
        else:
            if st.button("Generate Professional SLD"):
                doc = create_block_sld(df)
                
                # DXF File
                dxf_io = io.StringIO()
                doc.write(dxf_io)
                
                # PDF Preview
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
                st.success("Drafting Complete.")
    except Exception as e:
        st.error(f"Error processing file: {e}")
