import streamlit as st
import pandas as pd
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

# --- CORE DRAWING ENGINE ---
def create_sld(df):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Coordinates (Y-offsets)
    Y_BUS_A = 100
    Y_BUS_B = 92
    Y_CB = 70
    Y_CT = 55
    Y_TR_TOP = 15
    
    for _, row in df.iterrows():
        x = row['X_Pos']
        b_type = str(row['Type']).upper()
        
        # 1. Draw Double Busbars
        msp.add_line((x-20, Y_BUS_A), (x+20, Y_BUS_A), dxfattribs={'lineweight': 25})
        msp.add_line((x-20, Y_BUS_B), (x+20, Y_BUS_B), dxfattribs={'lineweight': 25})
        
        # 2. Draw CB (Circuit Breaker)
        msp.add_lwpolyline([(x-2, Y_CB-2), (x+2, Y_CB-2), (x+2, Y_CB+2), (x-2, Y_CB+2)], close=True)
        
        # 3. Draw CT (Current Transformer) - Simple Circle per your Legend 
        msp.add_circle((x, Y_CT), radius=1.5)
        
        # 4. Transformer Specific Logic
        if b_type == "XFMR":
            msp.add_circle((x, Y_TR_TOP), radius=3)
            msp.add_circle((x, Y_TR_TOP - 5), radius=3)
        
        # 5. Connect the vertical feeder line
        bottom_y = 5 if b_type == "XFMR" else 20
        msp.add_line((x, Y_BUS_A), (x, bottom_y))
        
        # 6. Text Labels
        msp.add_text(row['Bay_Name'], dxfattribs={'height': 2.5}).set_placement((x, 110))
        msp.add_text(row['CB_Rating'], dxfattribs={'height': 1.5}).set_placement((x + 4, Y_CB))

    # --- ADD LEGEND  ---
    leg_x, leg_y = df['X_Pos'].max() + 50, 100
    msp.add_text("LEGEND", dxfattribs={'height': 3}).set_placement((leg_x, leg_y))
    legend_items = [("CB", "Circuit Breaker"), ("CT", "Current Transformer"), ("XFMR", "Transformer")]
    for i, (code, name) in enumerate(legend_items):
        msp.add_text(f"{code}: {name}", dxfattribs={'height': 2}).set_placement((leg_x, leg_y - 10 - (i*5)))
        
    return doc

# --- STREAMLIT INTERFACE ---
st.title("⚡ Power System SLD Automator")
st.info("Initial Phase: 3 Line + 1 Coupler + 2 Transformer Arrangement")

uploaded_file = st.file_uploader("Upload Substation Excel", type="xlsx")

if uploaded_file:
    data = pd.read_excel(uploaded_file)
    st.dataframe(data)
    
    if st.button("Generate Outputs"):
        doc = create_sld(data)
        
        # DXF Export
        dxf_buff = io.StringIO()
        doc.write(dxf_buff)
        
        # PDF Export
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
        pdf_buff = io.BytesIO()
        fig.savefig(pdf_buff, format='pdf')
        
        st.download_button("Download DXF (AutoCAD)", dxf_buff.getvalue(), "output.dxf")
        st.download_button("Download PDF Report", pdf_buff.getvalue(), "output.pdf")
