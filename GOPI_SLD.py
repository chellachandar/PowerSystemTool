import streamlit as st
import pandas as pd
import ezdxf
import io

# --- DRAFTING ENGINE (STRICTLY FROM YOUR SLD_Automation.py) ---
def create_dxf_from_script(df):
    # Ensure column names are clean and strings
    df.columns = df.columns.astype(str).str.strip()
    
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Coordinates from your working file
    Y_BUS_A, Y_BUS_B = 100, 92
    Y_CB, Y_CT, Y_TR_TOP = 70, 55, 15
    
    for _, row in df.iterrows():
        # Safeguard: only process rows that have an X_Pos value
        try:
            x = float(row.get('X_Pos', 0))
        except:
            continue
            
        b_type = str(row.get('Type', 'LINE')).upper()
        
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
        
        # 6. Text Labels
        msp.add_text(str(row.get('Bay_Name', '')), dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(str(row.get('CB_Rating', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CB))
        msp.add_text(str(row.get('CT_Ratio', '')), dxfattribs={'height': 1.5}).set_placement((x+4, Y_CT))

    return doc

# --- UI LAYER WITH AUTOMATIC HEADER DETECTION ---
st.title("⚡ Power System SLD Automation")

uploaded_file = st.file_uploader("Upload Substation Input File", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # Step 1: Read raw data to find the header row
        if uploaded_file.name.endswith('.csv'):
            raw = pd.read_csv(uploaded_file, header=None)
        else:
            raw = pd.read_excel(uploaded_file, header=None)

        # Step 2: Search for the row containing 'X_Pos'
        header_row_index = None
        for i, row in raw.iterrows():
            if 'X_Pos' in [str(val).strip() for val in row.values]:
                header_row_index = i
                break
        
        if header_row_index is None:
            st.error("Could not find 'X_Pos' in any row. Please check your Excel headers.")
        else:
            # Step 3: Re-read with correct header
            uploaded_file.seek(0)
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, header=header_row_index)
            else:
                df = pd.read_excel(uploaded_file, header=header_row_index)

            st.success(f"Headers detected at row {header_row_index + 1}")
            st.dataframe(df.head())

            if st.button("Generate DXF"):
                doc = create_dxf_from_script(df)
                dxf_out = io.StringIO()
                doc.write(dxf_out)
                st.download_button("📥 Download .dxf", dxf_out.getvalue(), "Substation.dxf")
                
    except Exception as e:
        st.error(f"Processing Error: {e}")
