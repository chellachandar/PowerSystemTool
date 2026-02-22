import streamlit as st
import pandas as pd
import ezdxf
import io

# --- DRAFTING ENGINE: IDENTIFYING BAY REQUIREMENTS ---
def create_sld_from_logic(df):
    df.columns = [str(c).strip() for c in df.columns]
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Y-Offsets identifying the "Stack" for each bay
    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR = 70, 55, 15
    
    for _, row in df.iterrows():
        try:
            x = float(str(row.get('X_Pos', 0)).strip())
        except: continue

        # Identify Requirement: LINE vs XFMR vs COUPLER
        bay_type = str(row.get('Type', 'LINE')).upper()
        
        # 1. Busbar Requirement (Shared across all bays)
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A))
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B))
        
        # 2. Switching Requirement (CB)
        msp.add_lwpolyline([(x-2, Y_CB-2), (x+2, Y_CB-2), (x+2, Y_CB+2), (x-2, Y_CB+2)], close=True)
        
        # 3. Measurement Requirement (CT)
        msp.add_circle((x, Y_CT), radius=1.5)
        
        # 4. Transformation Requirement (XFMR only)
        if "XFMR" in bay_type:
            msp.add_circle((x, Y_TR), radius=3)
            msp.add_circle((x, Y_TR - 5), radius=3)
        
        # 5. Trunk Line Connection
        bot_y = 5 if "XFMR" in bay_type else 20
        msp.add_line((x, Y_BUS_A), (x, bot_y))
        
        # 6. Label Requirements
        msp.add_text(str(row.get('Bay_Name', '')), dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(str(row.get('CB_Rating', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(str(row.get('CT_Ratio', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CT))

    return doc

# --- UI: HEADER SEARCH & EXECUTION ---
st.title("⚡ Power System SLD Automator")

uploaded_file = st.file_uploader("Upload Substation Data", type=["xlsx", "csv"])

if uploaded_file:
    # Logic to identify the start of the data rows
    raw = pd.read_excel(uploaded_file, header=None) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file, header=None)
    
    header_idx = None
    for i, row in raw.head(20).iterrows():
        if 'X_Pos' in [str(v).strip() for v in row.values if pd.notna(v)]:
            header_idx = i
            break
            
    if header_idx is not None:
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, header=header_idx) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file, header=header_idx)
        st.success(f"Bay logic identified from Row {header_idx + 1}")
        
        if st.button("Generate AutoCAD SLD"):
            doc = create_sld_from_logic(df)
            dxf_io = io.StringIO()
            doc.write(dxf_io)
            st.download_button("📥 Download .dxf", dxf_io.getvalue(), "Substation.dxf")
    else:
        st.error("Could not identify the Bay Requirement headers. Ensure 'X_Pos' is in your file.")
