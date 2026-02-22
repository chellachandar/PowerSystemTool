import streamlit as st
import pandas as pd
import ezdxf
import io

# --- DRAFTING ENGINE (STRICTLY FROM YOUR SLD_Automation.py) ---
def create_dxf_from_script(df):
    # Ensure headers are clean strings
    df.columns = [str(c).strip() for c in df.columns]
    
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Coordinates from your working script
    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR_TOP = 70, 55, 15
    
    for _, row in df.iterrows():
        try:
            # Handle potential non-numeric X_Pos data gracefully
            x_raw = str(row.get('X_Pos', '0')).strip()
            x = float(x_raw) if x_raw.replace('.','',1).isdigit() else 0.0
        except:
            continue
            
        b_type = str(row.get('Type', 'LINE')).upper()
        
        # Geometry Logic
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
        
        # 6. Annotations
        msp.add_text(str(row.get('Bay_Name', '')), dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(str(row.get('CB_Rating', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(str(row.get('CT_Ratio', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CT))

    return doc

# --- UI LAYER WITH DEEP HEADER SCAN ---
st.title("⚡ Power System SLD Automation")

uploaded_file = st.file_uploader("Upload Substation Input File", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # Step 1: Load Raw (headerless) to scan for the true start
        if uploaded_file.name.endswith('.csv'):
            raw = pd.read_csv(uploaded_file, header=None)
        else:
            raw = pd.read_excel(uploaded_file, header=None)

        # Step 2: Deep Scan for Header Row
        header_row_index = None
        # We search for 'X_Pos' or 'Bay_Name' in every cell of the first 50 rows
        for i, row in raw.head(50).iterrows():
            clean_row = [str(val).strip().lower() for val in row.values if pd.notna(val)]
            if 'x_pos' in clean_row or 'bay_name' in clean_row or 'type' in clean_row:
                header_row_index = i
                break
        
        if header_row_index is None:
            st.error("Could not identify the Bay Requirement headers. Ensure 'X_Pos' is in your file.")
            st.write("Inspecting raw file content (First 10 rows):", raw.head(10))
        else:
            # Step 3: Re-read with detected index
            uploaded_file.seek(0)
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, header=header_row_index)
            else:
                df = pd.read_excel(uploaded_file, header=header_row_index)

            # Final cleanup of header names
            df.columns = [str(c).strip() for c in df.columns]
            st.success(f"Bay logic identified from Row {header_row_index + 1}")
            st.dataframe(df.head())

            if st.button("Generate AutoCAD SLD"):
                doc = create_dxf_from_script(df)
                dxf_out = io.StringIO()
                doc.write(dxf_out)
                st.download_button("📥 Download .dxf", dxf_out.getvalue(), "Substation.dxf")

    except Exception as e:
        st.error(f"Critical System Error: {e}")
