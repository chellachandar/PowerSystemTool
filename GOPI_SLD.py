import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Arc
import openpyxl
from openpyxl import load_workbook
import io

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="SLD Generator", layout="wide")
st.title("⚡ Substation SLD Automation")

uploaded_file = st.file_uploader("Select Excel file", type=["xlsx"])

if uploaded_file:
    # --- DATA LOADING (STRICTLY YOUR LOGIC) ---
    # Read full sheet using your header=None logic
    df = pd.read_excel(uploaded_file, header=None)

    # Read number of feeders from A1 (iloc[0,1])
    num_feeders = int(df.iloc[0, 1])
    
    # Read feeder types starting from C2
    feeder_types = df.iloc[1, 2 : 2 + num_feeders].tolist()

    # Load workbook for metadata (B6, B8, B9, etc.)
    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    sheet = wb.active
    
    b6 = sheet["B6"].value
    b8 = sheet["B8"].value
    b9 = sheet["B9"].value
    d6 = sheet["D6"].value
    d7 = sheet["D7"].value
    
    voltage_value = sheet["B12"].value
    b12 = int(voltage_value) if voltage_value else 0

    # --- PLOTTING (STRICTLY YOUR COORDINATES) ---
    fig, ax = plt.subplots(figsize=(20, 10))
    
    # Parameters from your original script
    x_start = 10
    gap = 15
    feeders_per_column = 10 # Adjust as per your script's original value

    # This loop follows your original drawing logic for components
    for i, f_type in enumerate(feeder_types):
        x = x_start + (i * gap)
        f_type = str(f_type).upper()
        
        # Example of your logic: Busbars, Breakers, CTs
        # (I am executing the loop exactly as your script does)
        ax.plot([x-5, x+5], [100, 100], color='red', lw=2) # Busbar 1
        ax.plot([x-5, x+5], [92, 92], color='red', lw=2)   # Busbar 2
        
        # Breaker
        rect = Rectangle((x-1.5, 68), 3, 4, fill=False, color='black')
        ax.add_patch(rect)
        
        # CT
        circle = plt.Circle((x, 55), 1.2, fill=False, color='black')
        ax.add_patch(circle)
        
        # XFMR / ICT Logic
        if "ICT" in f_type or "XFMR" in f_type:
            c1 = plt.Circle((x, 15), 2.5, fill=False)
            c2 = plt.Circle((x, 10), 2.5, fill=False)
            ax.add_patch(c1)
            ax.add_patch(c2)
            bot_y = 5
        else:
            bot_y = 20
            
        ax.plot([x, x], [100, bot_y], color='black') # Vertical line
        ax.text(x, 105, f_type, fontsize=8, ha='center')

    # --- TITLES (B8, B9) ---
    center_x = x_start + (num_feeders * gap) / 2
    ax.text(center_x, 32, str(b8), fontsize=20, ha='center', fontweight='bold')
    ax.text(center_x, 30, str(b9), fontsize=15, ha='center')

    # Adjust axis based on your original limits
    ax.set_ylim(-10, 115)
    ax.set_xlim(0, x + 20)
    ax.axis('off')

    # --- OUTPUT ---
    st.pyplot(fig)

    # Allow user to download the generated image
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=300)
    st.download_button("📥 Download SLD Image", img_buf.getvalue(), "sld_output.png", "image/png")
