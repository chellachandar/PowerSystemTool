import streamlit as st
import pandas as pd
import ezdxf
import io

# --- DRAFTING ENGINE (STRICTLY FROM YOUR SLD_Automation.py) ---
def create_dxf_from_script(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Coordinates from your working script
    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR_TOP = 70, 55, 15
    
    for _, row in df.iterrows():
        try:
            # We use position-based indexing (iloc) to avoid Header Errors
            # Assumes: Col 3 = X_Pos, Col 2 = Type, Col 1 = Bay_Name
            x = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0.0
            b_type = str(row.iloc[2]).upper()
            bay_name = str(row.iloc[1])
            cb_rating = str(row.iloc[4])
            ct_ratio = str(row.iloc[5])
        except Exception:
            continue
            
        # 1. Busbars
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A))
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B))
        
        # 2. CB Square
        msp.add_lwpolyline([(x-2, Y_CB-2), (x+2, Y_CB-2), (x+2, Y_CB+2), (x-2, Y_CB+2)], close=True)
        
        # 3. CT Circle
        msp.add_circle((x, Y_CT), radius=1.5)
        
        # 4. XFMR Double Circle
        if "XFMR" in b_type:
            msp.add_circle((x, Y_TR_TOP), radius=3)
            msp.add_circle((x, Y_TR_TOP - 5), radius=3)
        
        # 5. Trunk Line
        bot_y = 5 if "XFMR" in b_type else 20
        msp.add_line((x, Y_BUS_A), (x, bot_y))
        
        # 6. Labels
        msp.add_text(bay_name, dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(cb_rating, dxfattribs={'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(ct_ratio, dxfattribs={'height': 1.5}).set_placement((x+4, Y_CT))

    return doc

# --- UI LAYER WITH MANUAL OVERRIDE ---
st.title("⚡ Power System SLD Automation (Standard Doc Mode)")

uploaded_file = st.file_uploader("Upload Substation Input File", type=["xlsx", "csv"])

if uploaded_file:
    # Read the file with NO HEADER to get the raw table
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file, header=None)
    else:
        df_raw = pd.read_excel(uploaded_file, header=None)

    # We manually find the row where data actually starts (looking for 'ST-01' or similar)
    # We skip the first 2 rows by default to avoid the "Total No.of Bays" summary
    df_clean = df_raw.iloc[2:].reset_index(drop=True)

    st.write("### Verified Data (Manual Mapping Applied)")
    st.dataframe(df_clean.head())

    if st.button("Generate AutoCAD SLD"):
        doc = create_dxf_from_script(df_clean)
        dxf_out = io.StringIO()
        doc.write(dxf_out)
        st.download_button("📥 Download .dxf", dxf_out.getvalue(), "Substation.dxf")
