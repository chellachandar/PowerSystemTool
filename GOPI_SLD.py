import streamlit as st
import pandas as pd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

# --- 1. BLOCK DEFINITIONS ENGINE ---
def create_block_definitions(doc):
    """Creates reusable symbols within the CAD file to act like professional blocks."""
    # Circuit Breaker Block
    cb_block = doc.blocks.new(name='CB_SYMBOL')
    cb_block.add_lwpolyline([(-2, -2), (2, -2), (2, 2), (-2, 2)], close=True, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    
    # Current Transformer Block
    ct_block = doc.blocks.new(name='CT_SYMBOL')
    ct_block.add_circle((0, 0), radius=1.5, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

    # Transformer Block (Two overlapping circles)
    xfmr_block = doc.blocks.new(name='XFMR_SYMBOL')
    xfmr_block.add_circle((0, 0), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
    xfmr_block.add_circle((0, -5), radius=3, dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})

# --- 2. MAIN SLD GENERATOR ---
def create_block_sld(df):
    # --- ROBUST DATA CLEANING ---
    # Strip whitespace from column headers to prevent KeyErrors
    df.columns = df.columns.str.strip()
    
    doc = ezdxf.new('R2010')
    
    # Setup Layers for Senior Professional Standards
    doc.layers.new(name='PRIMARY_EQUIPMENT', dxfattribs={'color': 7}) # White/Black
    doc.layers.new(name='BUSBARS', dxfattribs={'color': 1})           # Red
    doc.layers.new(name='ANNOTATION', dxfattribs={'color': 4})        # Cyan
    doc.layers.new(name='LEGEND', dxfattribs={'color': 2})            # Yellow
    
    # Initialize Symbols
    create_block_definitions(doc)
    msp = doc.modelspace()

    # Vertical Offsets (Topology Logic)
    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR_TOP = 70, 55, 15
    
    for _, row in df.iterrows():
        # Using .get() ensures the script doesn't crash if a column is slightly renamed
        x = row.get('X_Pos', 0)
        b_type = str(row.get('Type', 'LINE')).upper()
        cb_val = str(row.get('CB_Rating', ''))
        ct_val = str(row.get('CT_Ratio', ''))
        bay_name = str(row.get('Bay_Name', 'Unknown Bay'))
        
        # 1. Add Busbars (Continuous)
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B), dxfattribs={'layer': 'BUSBARS', 'lineweight': 35})
        
        # 2. Insert Circuit Breaker Block
        msp.add_blockref('CB_SYMBOL', (x, Y_CB))
        if cb_val:
            msp.add_text(cb_val, dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, Y_CB))

        # 3. Insert Current Transformer Block
        msp.add_blockref('CT_SYMBOL', (x, Y_CT))
        if ct_val:
            msp.add_text(ct_val, dxfattribs={'layer': 'ANNOTATION', 'height': 1.5}).set_placement((x+4, Y_CT))
        
        # 4. Insert Transformer Block
        if "XFMR" in b_type:
            msp.add_blockref('XFMR_SYMBOL', (x, Y_TR_TOP))
        
        # 5. Connection Lines
        bottom_y = 5 if "XFMR" in b_type else 20
        msp.add_line((x, Y_BUS_A), (x, bottom_y), dxfattribs={'layer': 'PRIMARY_EQUIPMENT'})
        
        # 6. Bay Labeling
        msp.add_text(bay_name, dxfattribs={'layer': 'ANNOTATION', 'height': 2.5}).set_placement((x, 110))

    # 7. ADD DYNAMIC LEGEND
    leg_x, leg_y = df['X_Pos'].max() + 50, 100
    msp.add_text("LEGEND", dxfattribs={'layer': 'LEGEND', 'height': 3}).set_placement((leg_x, leg_y))
    legend_items = [("CB", "Circuit Breaker"), ("CT", "Current Transformer"), ("XFMR", "Transformer")]
    for i, (code, name) in enumerate(legend_items):
        msp.add_text(f"{code}: {name}", dxfattribs={'layer': 'LEGEND', 'height': 2}).set_placement((leg_x, leg_y - 10 - (i*5)))
        
    return doc

# --- 3. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Power System SLD Automator", layout="wide")
st.title("⚡ Senior Power Professional: SLD Automation Tool")
st.markdown("""
### Instructions:
1. Upload your **updated excel.xlsx**. 
2. Ensure columns are named: `Bay_Name`, `Type`, `X_Pos`, `CB_Rating`, `CT_Ratio`.
3. The tool will output an editable AutoCAD (.dxf) and a PDF report.
""")

uploaded_file = st.file_uploader("Choose Excel/CSV File", type=["xlsx", "csv"])

if uploaded_file:
    # Read CSV or Excel correctly
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    st.write("### Data Preview", df.head())
    
    if st.button("Generate Professional SLD"):
        with st.spinner('Drafting in progress...'):
            doc = create_block_sld(df)
            
            # Prepare DXF Buffer
            dxf_buff = io.StringIO()
            doc.write(dxf_buff)
            
            # Prepare PDF Buffer using Matplotlib
            fig = plt.figure(figsize=(14, 8))
            ax = fig.add_axes([0, 0, 1, 1])
            Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
            pdf_buff = io.BytesIO()
            fig.savefig(pdf_buff, format='pdf', dpi=300)
            
            st.success("Generation Successful!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Download Editable AutoCAD (.dxf)",
                    data=dxf_buff.getvalue(),
                    file_name="Substation_Automated_SLD.dxf",
                    mime="application/dxf"
                )
            with col2:
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_buff.getvalue(),
                    file_name="Substation_Automated_SLD.pdf",
                    mime="application/pdf"
                )
