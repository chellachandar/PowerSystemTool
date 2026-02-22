import streamlit as st
import pandas as pd
import ezdxf
import io

# --- 1. DRAFTING ENGINE (STRICTLY BASED ON YOUR LOGIC) ---
def create_dxf_from_script(df):
    # Standardize headers to match your script's keys
    df.columns = df.columns.astype(str).str.strip()
    
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Standard Y-Offsets from your working logic
    Y_BUS_A = 100
    Y_BUS_B = 92
    Y_CB = 70
    Y_CT = 55
    Y_TR_TOP = 15
    
    for _, row in df.iterrows():
        # Get coordinates and data from your specific columns
        x = row.get('X_Pos', 0)
        b_type = str(row.get('Type', 'LINE')).upper()
        
        # 1. Busbars (Your logic: Two horizontal lines)
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A))
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B))
        
        # 2. Circuit Breaker (Your logic: A square)
        msp.add_lwpolyline([(x-2, Y_CB-2), (x+2, Y_CB-2), (x+2, Y_CB+2), (x-2, Y_CB+2)], close=True)
        
        # 3. Current Transformer (Your logic: A circle)
        msp.add_circle((x, Y_CT), radius=1.5)
        
        # 4. Transformer (Your logic: Double circles for XFMR type)
        if "XFMR" in b_type:
            msp.add_circle((x, Y_TR_TOP), radius=3)
            msp.add_circle((x, Y_TR_TOP - 5), radius=3)
        
        # 5. Connection (Vertical line through components)
        bottom_y = 5 if "XFMR" in b_type else 20
        msp.add_line((x, Y_BUS_A), (x, bottom_y))
        
        # 6. Labels (Pulling directly from your column names)
        msp.add_text(str(row.get('Bay_Name', '')), dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(str(row.get('CB_Rating', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(str(row.get('CT_Ratio', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CT))

    return doc

# --- 2. STREAMLIT INTERFACE ---
st.set_page_config(page_title="SLD Automation Tool", layout="wide")
st.title("⚡ Power System SLD Automation")

uploaded_file = st.file_uploader("Upload Substation Input File", type=["xlsx", "csv"])

if uploaded_file:
    # Handle both CSV and Excel while skipping title rows
    try:
        if uploaded_file.name.endswith('.csv'):
            # Detect header row containing 'X_Pos'
            temp_df = pd.read_csv(uploaded_file, header=None)
            header_idx = next(i for i, r in temp_df.iterrows() if "X_Pos" in [str(v).strip() for v in r.values])
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=header_idx)
        else:
            temp_df = pd.read_excel(uploaded_file, header=None)
            header_idx = next(i for i, r in temp_df.iterrows() if "X_Pos" in [str(v).strip() for v in r.values])
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, header=header_idx)

        st.write("### Input Data Preview", df.head())

        if st.button("Generate AutoCAD DXF"):
            doc = create_dxf_from_script(df)
            
            # Export to DXF stream
            dxf_io = io.StringIO()
            doc.write(dxf_io)
            
            st.download_button(
                label="📥 Download .dxf File",
                data=dxf_io.getvalue(),
                file_name="Substation_SLD.dxf",
                mime="application/dxf"
            )
            st.success("DXF generated based on provided script logic.")

    except Exception as e:
        st.error(f"Error: {e}. Ensure 'X_Pos' column exists in the file.")
