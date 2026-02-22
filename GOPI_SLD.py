import streamlit as st
import pandas as pd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

# --- 1. DRAFTING ENGINE (STRICT POSITION-BASED LOGIC) ---
def create_dxf_from_script(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Standard Y-Offsets from your working SLD_Automation.py
    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR_TOP = 70, 55, 15
    
    for _, row in df.iterrows():
        try:
            # We bypass names and use Column Indexes (0=A, 1=B, 2=C, 3=D...)
            # Mapping based on your 'updated excel.xlsx' structure:
            x = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0.0 # Column D: X_Pos
            bay_name = str(row.iloc[1])                             # Column B: Bay_Name
            b_type = str(row.iloc[2]).upper()                       # Column C: Type
            cb_val = str(row.iloc[4])                               # Column E: CB_Rating
            ct_val = str(row.iloc[5])                               # Column F: CT_Ratio
        except:
            continue
            
        # Draw Geometry
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A))
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B))
        msp.add_lwpolyline([(x-2, Y_CB-2), (x+2, Y_CB-2), (x+2, Y_CB+2), (x-2, Y_CB+2)], close=True)
        msp.add_circle((x, Y_CT), radius=1.5)
        
        if "XFMR" in b_type:
            msp.add_circle((x, Y_TR_TOP), radius=3)
            msp.add_circle((x, Y_TR_TOP - 5), radius=3)
        
        bot_y = 5 if "XFMR" in b_type else 20
        msp.add_line((x, Y_BUS_A), (x, bot_y))
        
        # Annotations
        msp.add_text(bay_name, dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(cb_val, dxfattribs={'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(ct_val, dxfattribs={'height': 1.5}).set_placement((x+4, Y_CT))

    return doc

# --- 2. STREAMLIT UI WITH PDF CONFIRMATION ---
st.title("⚡ Power System SLD Automator")
st.markdown("Automated DXF & PDF generation for Senior Professionals.")

uploaded_file = st.file_uploader("Upload Substation Data", type=["xlsx", "csv"])

if uploaded_file:
    # Read raw file with NO headers to bypass summary rows
    df_raw = pd.read_excel(uploaded_file, header=None) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file, header=None)
    
    # Skip the first 2 rows (Summary info) and treat Row 3 as the start of data
    df_clean = df_raw.iloc[2:].reset_index(drop=True)
    
    st.write("### Data Preview (Columns A-F mapped automatically)", df_clean.head())

    if st.button("Generate AutoCAD & PDF"):
        doc = create_dxf_from_script(df_clean)
        
        # 1. Prepare DXF
        dxf_io = io.StringIO()
        doc.write(dxf_io)
        
        # 2. Prepare PDF for quick confirmation
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
        pdf_io = io.BytesIO()
        fig.savefig(pdf_io, format='pdf', dpi=300)
        
        st.success("Files Generated!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download DXF", dxf_io.getvalue(), "Substation.dxf")
        with col2:
            st.download_button("📥 Download PDF Confirmation", pdf_io.getvalue(), "Substation_Preview.pdf")
            
        # Display the PDF directly in Streamlit for instant confirmation
        st.pyplot(fig)
