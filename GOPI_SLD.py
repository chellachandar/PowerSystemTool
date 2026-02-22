import streamlit as st
import pandas as pd
import ezdxf
import io

# --- 1. DRAFTING ENGINE (STRICTLY FROM YOUR SLD_Automation.py) ---
def create_dxf_from_script(df):
    # Ensure column names are stripped of hidden spaces
    df.columns = df.columns.astype(str).str.strip()
    
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Standard Y-Offsets from your working script
    Y_BUS_A = 100
    Y_BUS_B = 92
    Y_CB = 70
    Y_CT = 55
    Y_TR_TOP = 15
    
    for _, row in df.iterrows():
        try:
            # Clean and validate the X_Pos coordinate
            x_val = str(row.get('X_Pos', '0')).strip()
            x = float(x_val) if x_val != '' else 0.0
        except:
            continue # Skip rows with invalid coordinates
            
        b_type = str(row.get('Type', 'LINE')).upper()
        
        # 1. Busbars
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A))
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B))
        
        # 2. Circuit Breaker (Square)
        msp.add_lwpolyline([(x-2, Y_CB-2), (x+2, Y_CB-2), (x+2, Y_CB+2), (x-2, Y_CB+2)], close=True)
        
        # 3. Current Transformer (Circle)
        msp.add_circle((x, Y_CT), radius=1.5)
        
        # 4. Transformer (Double Circle for XFMR type)
        if "XFMR" in b_type:
            msp.add_circle((x, Y_TR_TOP), radius=3)
            msp.add_circle((x, Y_TR_TOP - 5), radius=3)
        
        # 5. Connection Trunk Line
        bot_y = 5 if "XFMR" in b_type else 20
        msp.add_line((x, Y_BUS_A), (x, bot_y))
        
        # 6. Text Labels
        msp.add_text(str(row.get('Bay_Name', '')), dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(str(row.get('CB_Rating', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(str(row.get('CT_Ratio', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CT))

    return doc

# --- 2. INTELLIGENT UI LAYER ---
st.set_page_config(page_title="Power System SLD Automator", layout="wide")
st.title("⚡ Power System SLD Automation")
st.markdown("Automated drafting tool for Senior Power System professionals.")

uploaded_file = st.file_uploader("Upload Substation Input File", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # Load the file as raw data to identify header location
        if uploaded_file.name.endswith('.csv'):
            raw = pd.read_csv(uploaded_file, header=None)
        else:
            raw = pd.read_excel(uploaded_file, header=None)

        # FUZZY HEADER SEARCH: Scan first 20 rows for key column names
        header_row_index = None
        targets = ['X_Pos', 'Bay_Name', 'Type', 'CB_Rating']
        
        for i, row in raw.head(20).iterrows():
            vals = [str(v).strip().lower() for v in row.values if pd.notna(v)]
            if any(t.lower() in vals for t in targets):
                header_row_index = i
                break
        
        if header_row_index is None:
            st.error("Header not found. Ensure a row contains 'X_Pos', 'Bay_Name', or 'Type'.")
            st.write("First 10 rows of your file:", raw.head(10))
        else:
            # Re-read file using the detected header row
            uploaded_file.seek(0)
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, header=header_row_index)
            else:
                df = pd.read_excel(uploaded_file, header=header_row_index)

            # Cleanup final headers
            df.columns = df.columns.astype(str).str.strip()
            st.success(f"Headers successfully identified at row {header_row_index + 1}")
            st.dataframe(df.head())

            if st.button("Generate AutoCAD DXF"):
                with st.spinner("Processing..."):
                    doc = create_dxf_from_script(df)
                    dxf_out = io.StringIO()
                    doc.write(dxf_out)
                    
                    st.download_button(
                        label="📥 Download .dxf File",
                        data=dxf_out.getvalue(),
                        file_name="Substation_SLD.dxf",
                        mime="application/dxf"
                    )
                    st.success("Drafting complete based on existing logic.")

    except Exception as e:
        st.error(f"Critical System Error: {e}")
