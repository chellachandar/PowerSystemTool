My apologies for the confusion! I completely understand what you are asking for.

You do not want an arbitrary "Max 30" limit imposed by the software. You want a dynamic input where you type the **exact number of bays** your specific station has (e.g., 5, 12, 20, or 25). Once you enter that number, the screen should immediately adapt and show you *only* that many bay selection options.

The good news is that **Streamlit is a reactive framework**. This means the moment you change the "Number of Bays" input on the screen, the entire web page instantly refreshes to match your command. If you type "12", exactly 12 bay configuration boxes will immediately appear.

Regarding the PDF you attached (which still showed 20 bays): That happened because the older script was still reading the fixed length of the Excel rows. By removing Excel entirely, the Python drafting engine is now strictly bound *only* to the number you type on the screen.

Here is the refined code with the hard limits removed, pure dynamic bay generation, and strict validation checks to prevent empty inputs.

### The Refined Dynamic UI Code

*(Replace your `app.py` with this exact code. Notice how `num_feeders` dynamically creates the UI rows!)*

```python
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Arc
import matplotlib.patches as mpatches
import io
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment

# --- GEOMETRICALLY PERFECT DXF ENGINE (UNCHANGED) ---
def export_ax_to_dxf(ax):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    for line in ax.lines:
        xdata, ydata = line.get_xdata(), line.get_ydata()
        dxf_color = {'red': 1, 'green': 3, 'blue': 5}.get(line.get_color(), 7)
        for idx in range(len(xdata)-1):
            msp.add_line((xdata[idx], ydata[idx]), (xdata[idx+1], ydata[idx+1]), dxfattribs={'color': dxf_color})

    for patch in ax.patches:
        def get_dxf_color(rgba):
            if rgba[0] > 0.5 and rgba[1] < 0.5 and rgba[2] < 0.5: return 1 
            elif rgba[1] > 0.4 and rgba[0] < 0.5 and rgba[2] < 0.5: return 3 
            elif rgba[2] > 0.5 and rgba[0] < 0.5 and rgba[1] < 0.5: return 5 
            return 7 
            
        edge_color = get_dxf_color(patch.get_edgecolor())
        face_color = get_dxf_color(patch.get_facecolor())
        
        if isinstance(patch, mpatches.Rectangle):
            x, y = patch.get_xy()
            w, h = patch.get_width(), patch.get_height()
            pts = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
            if patch.get_fill():
                hatch = msp.add_hatch(color=face_color)
                hatch.paths.add_polyline_path(pts, is_closed=True)
            msp.add_lwpolyline(pts, close=True, dxfattribs={'color': edge_color})
            
        elif isinstance(patch, mpatches.Polygon):
            pts = patch.get_xy()
            if len(pts) > 1 and (pts[0][0] == pts[-1][0] and pts[0][1] == pts[-1][1]):
                pts = pts[:-1] 
            if patch.get_fill():
                hatch = msp.add_hatch(color=face_color)
                hatch.paths.add_polyline_path(pts, is_closed=True)
            msp.add_lwpolyline(pts, close=True, dxfattribs={'color': edge_color})
            
        elif isinstance(patch, mpatches.Arc):
            w, h = patch.width, patch.height
            
            def true_to_parametric(theta_deg, w, h):
                t_rad = math.atan2(w * math.sin(math.radians(theta_deg)), h * math.cos(math.radians(theta_deg)))
                return math.degrees(t_rad) % 360.0
                
            t1 = true_to_parametric(patch.theta1, w, h)
            t2 = true_to_parametric(patch.theta2, w, h)
            if t2 <= t1 and not math.isclose(patch.theta1, patch.theta2): t2 += 360.0
                
            num_segments = 36
            angles = [math.radians(t1 + (t2 - t1) * i / num_segments) for i in range(num_segments + 1)]
            cx, cy = patch.center
            rot = math.radians(patch.angle)
            cos_r, sin_r = math.cos(rot), math.sin(rot)
            
            pts = []
            for a in angles:
                ex, ey = (w / 2.0) * math.cos(a), (h / 2.0) * math.sin(a)
                pts.append((ex * cos_r - ey * sin_r + cx, ex * sin_r + ey * cos_r + cy))
            msp.add_lwpolyline(pts, dxfattribs={'color': edge_color})

    for txt in ax.texts:
        x, y = txt.get_position()
        text_str = txt.get_text()
        if not text_str.strip(): continue
            
        fs, ha, va = txt.get_fontsize(), txt.get_ha(), txt.get_va()
        dxf_color = {'red': 1, 'green': 3, 'blue': 5}.get(txt.get_color(), 7)
        h_scale = fs * 0.025  
        line_gap = h_scale * 1.3 
        
        lines = text_str.split('\n')
        block_height = (len(lines) - 1) * line_gap + h_scale
        
        start_center_y = y - (h_scale / 2.0) if va == 'top' else y + block_height - (h_scale / 2.0) if va in ['bottom', 'baseline'] else y + (block_height / 2.0) - (h_scale / 2.0)
            
        align = TextEntityAlignment.MIDDLE_LEFT if ha == 'left' else TextEntityAlignment.MIDDLE_RIGHT if ha == 'right' else TextEntityAlignment.MIDDLE_CENTER
        
        current_y = start_center_y
        for l_str in lines:
            if l_str.strip():
                dtxt = msp.add_text(l_str, dxfattribs={'height': h_scale, 'color': dxf_color, 'width': 0.85})
                dtxt.set_placement((x, current_y), align=align)
            current_y -= line_gap 

    return doc


# --- DIRECT UI APPLICATION ---
st.set_page_config(page_title="Dynamic SLD Generator", layout="wide")
st.title("⚡ Dynamic Substation SLD Generator")

with st.sidebar:
    st.header("1. Global Parameters")
    # Placeholders enforce manual entry. No default names are provided.
    b8 = st.text_input("Project Title", value="", placeholder="e.g. POWERGRID CORPORATION")
    b9 = st.text_input("Subtitle / Station Name", value="", placeholder="e.g. YELAHANKA SS")
    b12 = st.number_input("Voltage (kV)", value=400, step=11)
    b6 = st.selectbox("Bus Configuration", ["One and Half Breaker", "Double Main Bus", "Double Main Transfer Bus"])
    
    st.divider()
    st.header("2. Station Size (Dynamic UI)")
    
    # USER INPUT: Type 5, 12, 20, etc. The screen will instantly update to show exactly this many bays.
    num_feeders = st.number_input("Enter the exact number of Bays for this station:", min_value=1, value=5, step=1)
    
    if b6 == "One and Half Breaker":
        st.write("Specify Tie Bay Locations:")
        d6 = st.number_input("Tie Bay 1 (Index)", min_value=1, max_value=int(num_feeders), value=min(12, int(num_feeders)))
        d7 = st.number_input("Tie Bay 2 (Index)", min_value=1, max_value=int(num_feeders), value=min(13, int(num_feeders)))
    else:
        d6, d7 = None, None

# --- DYNAMIC BAY GENERATION ---
st.subheader(f"Configure {int(num_feeders)} Bays")
st.write("Select the equipment type and provide a name for each bay below.")

feeder_types = []
feeder_names = []
bay_options = ["Line_Bay", "ICT", "Bus_Coupler", "Reactor", "Future_Bay", "Transfer_Bus_coupler", "Cable Feeder", "No_bay"]

# This loop strictly reads the number you typed in the sidebar and generates exactly that many UI boxes.
cols = st.columns(4)
for i in range(int(num_feeders)):
    with cols[i % 4]:
        st.markdown(f"**Bay {i+1}**")
        ftype = st.selectbox(f"Type", bay_options, key=f"type_{i}")
        fname = st.text_input(f"Name", value="", placeholder=f"Name for Bay {i+1}", key=f"name_{i}")
        feeder_types.append(ftype)
        feeder_names.append(fname)
        st.write("---")

# --- STRICT VALIDATION & GENERATION ---
if st.button("Generate AutoCAD DXF", type="primary"):
    
    errors = []
    if not b8.strip():
        errors.append("❌ Project Title cannot be blank.")
    if not b9.strip():
        errors.append("❌ Subtitle / Station Name cannot be blank.")
        
    empty_bays = [str(i+1) for i, name in enumerate(feeder_names) if not name.strip()]
    if empty_bays:
        errors.append(f"❌ Missing names in Bays: {', '.join(empty_bays)}. All configured bays must have a name.")
        
    if b6 == "One and Half Breaker":
        if d6 > num_feeders or d7 > num_feeders:
            errors.append(f"❌ Tie Bay indices cannot exceed the total number of bays ({num_feeders}).")

    if errors:
        for error in errors:
            st.error(error)
        st.stop() # Halts the program if validation fails

    # --- START DRAFTING ---
    with st.spinner(f"Validation Passed! Drafting {int(num_feeders)}-Bay Single Line Diagram..."):
        
        # --- DATA SANITIZATION ---
        for i in range(len(feeder_types)):
            if b6 in ["Double Main Transfer Bus", "Double Main Bus"]:
                if feeder_types[i] == "" or feeder_types[i] == "Future_Bay": 
                    feeder_types[i] = "Line_Bay"
            else:
                if feeder_types[i] in ["", "Bus_Coupler", "Cable Feeder", "Transfer_Bus_coupler"]: 
                    feeder_types[i] = "Line_Bay"

        def get_fontsize(num_feeders):
            return 3 if b6 == "Double Main Transfer Bus" else 4

        # --- DRAFTING FUNCTIONS ---
        def draw_breaker(ax, x, y, label, fs):
            ax.add_patch(Rectangle((x-0.1, y-0.2), 0.2, 0.4, fill=False, edgecolor='black', linewidth=0.5))
            ax.plot([x, x], [y+.2, y+1], color='red', linewidth=0.5)
            ax.plot([x, x], [y-.2, y-1], color='red', linewidth=0.5)
            ax.text(x+.3, y, label, fontsize=fs, ha='center')

        def draw_breaker_coupler(ax, x, y, label, fs):
            ax.add_patch(Rectangle((x-0.1, y-0.2), 0.2, 0.4, fill=False, edgecolor='black', linewidth=0.5))
            ax.plot([x-.45, x-.1], [y, y], color='red', linewidth=0.5)
            ax.plot([x+.1, x+.45], [y, y], color='red', linewidth=0.5)
            ax.text(x, y+.5, label, fontsize=fs, ha='center')

        def draw_isolator(ax, x, y, label, fs):
            ax.plot([x, x], [y-.12, y+.2 if b6 == "Double Main Transfer Bus" else y+.4], color='red', linewidth=0.5)
            ax.text(x+.2 if b6 == "Double Main Transfer Bus" else x+.3, y-.2 if b6 == "Double Main Transfer Bus" else y-.3, label, fontsize=fs, ha='center')
            ax.add_patch(Arc((x , y-0.6/4), 0.04, 0.08, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.add_patch(Arc((x , y-.5-0.6/4), 0.04, 0.08, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.plot([x-.05, x+.05], [y-.55, y-.25], color='red', linewidth=0.5)
            ax.plot([x, x], [y-.7, y-1.2], color='red', linewidth=0.5)

        def earth_sh(ax, x, y, label, fs):
            y = y - .2
            ax.plot([x, x-.2], [y-.6, y-.6], color='red', linewidth=0.5)
            ax.add_patch(Arc((x-.2 , y-.45-0.6/4), 0.04, 0.08, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.add_patch(Arc((x-.35 , y-.45-0.6/4), 0.04, 0.08, angle=0, theta1=0, theta2=360, color='green', linewidth=0.5))
            ax.plot([x-.2, x-.35], [y-.35, y-.6], color='green', linewidth=0.5)
            ax.plot([x-.35, x-.5], [y-.6, y-.6], color='green', linewidth=0.5)
            ax.plot([x-.5, x-.5], [y-.45, y-.75], color='green', linewidth=0.5)
            ax.plot([x-.55, x-.55], [y-.5, y-.7], color='green', linewidth=0.5)
            ax.plot([x-.6, x-.6], [y-.55, y-.65], color='green', linewidth=0.5)
            ax.text(x-.4, y-.35, label, fontsize=fs, ha='center')

        def draw_ct(ax, x, y, label, fs):
            spacing = 0.75
            ax.add_patch(Arc((x+.03 , y- spacing/4), 0.2, 0.4, angle=0, theta1=80, theta2=280, color='blue', linewidth=0.5))
            ax.add_patch(Arc((x+.03 , y+ spacing/4), 0.2, 0.4, angle=0, theta1=80, theta2=280, color='blue', linewidth=0.5))
            ax.text(x-.3, y, label, fontsize=fs, ha='center')

        def draw_wt(ax, x, y, label, fs):
            ax.add_patch(Arc((x , y-0.6/4), 0.2, 0.4, angle=0, theta1=90, theta2=360, color='red', linewidth=0.5))
            ax.plot([x, x+.1], [y-.15, y-.15], color='red', linewidth=0.5)
            ax.text(x-.3, y, label, fontsize=fs, ha='center')

        def draw_cvt(ax, x, y, label, fs):
            y = y - .2
            ax.plot([x, x + .15], [y - .6, y - .6], color='red', linewidth=0.5)
            ax.plot([x + .15, x + .15], [y - .45, y - .75], color='red', linewidth=0.5)
            ax.plot([x + .2, x + .2], [y - .45, y - .75], color='red', linewidth=0.5)
            ax.plot([x + .2, x + .55], [y - .6, y - .6], color='red', linewidth=0.5)
            ax.plot([x + .55, x + .55], [y - .45, y - .75], color='red', linewidth=0.5)
            ax.plot([x + .6, x + .6], [y - .45, y - .75], color='red', linewidth=0.5)
            ax.plot([x + .6, x + .7], [y - .6, y - .6], color='red', linewidth=0.5)
            ax.plot([x + .7, x + .7], [y - .45, y - .75], color='green', linewidth=0.5)
            ax.plot([x + .75, x + .75], [y - .5, y - .7], color='green', linewidth=0.5)
            ax.plot([x + .8, x + .8], [y - .55, y - .65], color='green', linewidth=0.5)
            ax.plot([x + .375, x + .375], [y - .6, y - 1.4], color='red', linewidth=0.5)
            ax.plot([x + .375, x + .45], [y - 1.4, y - 1.4], color='red', linewidth=0.5)
            ax.add_patch(Arc((x+.45 , y-1.4-0.45/4), 0.1, 0.2, angle=0, theta1=270, theta2=90, color='red', linewidth=0.5))
            ax.add_patch(Arc((x+.45 , y-1.4+0.45/4), 0.1, 0.2, angle=0, theta1=270, theta2=90, color='red', linewidth=0.5))
            ax.plot([x + .575, x + .575], [y - 1, y - 1.7], color='red', linewidth=.5)
            ax.plot([x + .55, x + .55], [y - 1, y - 1.7], color='red', linewidth=.5)
            ax.add_patch(Arc((x+.675 , y-1.1- 0.25/4), 0.1, 0.2, angle=0, theta1=80, theta2=280, color='red', linewidth=.5))
            ax.add_patch(Arc((x+.675 , y-1.025+ 0.25/4), 0.1, 0.2, angle=0, theta1=80, theta2=280, color='red', linewidth=.5))
            ax.add_patch(Arc((x+.675 , y-1.6+ 0.25/4), 0.1, 0.2, angle=0, theta1=80, theta2=280, color='red', linewidth=.5))
            ax.text(x + .4, y - .4, label, fontsize=fs, ha='center')
            ax.add_patch(Arc((x+.675 , y-1.8+ 0.25/4), 0.1, 0.2, angle=0, theta1=80, theta2=280, color='red', linewidth=.5))

        def draw_symbol(ax, x, y, label, fs):
            ax.add_patch(Polygon([[x, y-0.1], [x+0.1, y+0.1], [x-0.1, y+0.1]], closed=True, fill=False, edgecolor='red', linewidth=0.5))

        def draw_symbol_upp(ax, x, y, label, fs):
            ax.add_patch(Polygon([[x, y+0.1], [x+0.1, y-0.1], [x-0.1, y-0.1]], closed=True, fill=False, edgecolor='red', linewidth=0.5))

        def draw_name(ax, x, y, label, fs):
            ax.text(x, y+.5, label, fontsize=fs+2, ha='center')

        def draw_la(ax, x, y, label, fs):
            y = y - .2
            ax.plot([x-.9, x], [y, y], color='red', linewidth=0.5)
            ax.plot([x - .9, x - .9], [y +.2, y -.2], color='green', linewidth=0.5)
            ax.plot([x - .95, x - .95], [y +.15, y -.15], color='green', linewidth=0.5)
            ax.plot([x - 1, x - 1], [y +.1, y -.1], color='green', linewidth=0.5)
            ax.text(x-.5, y-0.5, label, fontsize=fs, ha='center')

        def la_comp(ax, x, y):
            ax.add_patch(Polygon([[x+0.1, y+0.1], [x-0.1, y], [x+0.1, y-0.1]], closed=True, fill=True,color='red', linewidth=0.5))
            ax.add_patch(Rectangle((x-0.2, y-0.2), 0.4, 0.4, fill=False, edgecolor='red', linewidth=0.5))

        def draw_ict(ax, x, y, label, fs):
            ax.add_patch(Arc((x , y-0.6/4), 0.3, 0.6, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.add_patch(Arc((x-.15 , y-0.6/4), 0.2, 0.4, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.add_patch(Arc((x , (y-.255-0.6/4)), 0.4, 1.2, angle=0, theta1=270, theta2=90, color='red', linewidth=.5))
            ax.text(x-.25, y-.7, label, fontsize=fs, ha='center')

        def draw_ict_upp(ax, x, y, label, fs):
            ax.add_patch(Arc((x , y-.525-0.6/4), 0.3, 0.6, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.add_patch(Arc((x-.15 , y-.525-0.6/4), 0.2, 0.4, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.add_patch(Arc((x , (y-.255-0.6/4)), 0.4, 1.2, angle=0, theta1=270, theta2=90, color='red', linewidth=.5))
            ax.text(x-.3, y-.2, label, fontsize=fs, ha='center')

        def draw_reacter(ax, x, y, label, fs):
            ax.add_patch(Arc((x-.025 , y- .2/4), 0.2, 0.4, angle=0, theta1=80, theta2=300, color='red', linewidth=0.5))
            ax.add_patch(Arc((x-.025 , y-1.2/4), 0.2, 0.4, angle=0, theta1=60, theta2=300, color='red', linewidth=0.5))
            ax.add_patch(Arc((x-.025 , y-2.2/4), 0.2, 0.4, angle=0, theta1=60, theta2=300, color='red', linewidth=0.5))
            ax.add_patch(Arc((x-.025 , y-3.2/4), 0.2, 0.4, angle=0, theta1=60, theta2=280, color='red', linewidth=0.5))
            ax.text(x-.45, y-.8, label, fontsize=fs, ha='center')

        def draw_earth_symbol(ax, x, y, label, fs):
            ax.plot([x-.125, x+.125], [y+.1, y+.1], color='green', linewidth=0.5)
            ax.plot([x-.1, x+.1], [y, y], color='green', linewidth=0.5)
            ax.plot([x-.075, x+.075], [y-.1, y-.1], color='green', linewidth=0.5)
            ax.plot([x-.05, x+.05], [y-.2, y-.2], color='green', linewidth=0.5)
            ax.plot([x-.025, x+.025], [y-.3, y-.3], color='green', linewidth=0.5)

        def draw_earth_symbol_upp(ax, x, y, label, fs):
            ax.plot([x-.125, x+.125], [y-.3, y-.3], color='green', linewidth=0.5)
            ax.plot([x-.1, x+.1], [y-.2, y-.2], color='green', linewidth=0.5)
            ax.plot([x-.075, x+.075], [y-.1, y-.1], color='green', linewidth=0.5)
            ax.plot([x-.05, x+.05], [y, y], color='green', linewidth=0.5)
            ax.plot([x-.025, x+.025], [y+.1, y+.1], color='green', linewidth=0.5)

        def get_labels(feeder_num, i):
            bay_num = i + 1 
            earth_label = f"{b12+feeder_num}89AE2" if bay_num in [d6, d7] else f"{b12+feeder_num}89AE"
            earth_label2 = f"{b12+feeder_num}89AE1" 

            current_type = feeder_types[i] if i < len(feeder_types) else ""

            ct_label = f"{b12+feeder_num}CT"
            if current_type in ["Line_Bay", "Future_Bay"] and (bay_num % 3 == 1 or bay_num % 3 == 0):
                pair_index = i - 2 if bay_num % 3 == 0 else i + 2  
                if pair_index < len(feeder_types) and feeder_types[pair_index] in ["Line_Bay", "Future_Bay"]:
                    ct_label = f"{b12+feeder_num+1}BCT" if (bay_num - 1) % 3 == 0 else f"{b12+feeder_num-1}ACT"
                else:
                    ct_label = f"{b12+feeder_num+1}CT" if (bay_num - 1) % 3 == 0 else f"{b12+feeder_num-1}CT" if bay_num % 3 == 0 else f"{b12+feeder_num}CT"
            else:
                ct_label = f"{b12+feeder_num+1}CT" if (bay_num - 1) % 3 == 0 else f"{b12+feeder_num-1}CT" if bay_num % 3 == 0 else f"{int(b12+feeder_num)}CT"

            if current_type == "ICT":
                iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89T", f"{b12+feeder_num}89TE"
            elif current_type == "Line_Bay":
                iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89L", f"{b12+feeder_num}89LE"
            elif current_type == "Reactor":
                iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89R", f"{b12+feeder_num}89RE"
            else:
                iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89C", f"{b12+feeder_num}89CE"

            labels = {
                "base_isolator": f"{b12+feeder_num}89A", "base_isolatorb": f"{b12+feeder_num}89B", "breaker_lbl": f"{b12+feeder_num}52",
                "earth_lbl1": earth_label, "earth_lbl_BUS": earth_label2, "earth_lbl2": f"{b12+feeder_num}89BE",
                "iso_lbl2": iso_lbl2, "ct_lbl": f"{int(b12+feeder_num)}CT", "ct_lbl_middle": ct_label,
                "wt_lbl": f"{int(b12+feeder_num)}WT", "cvt_lbl": f"{int(b12+feeder_num)}CVT", "la_lbl": f"{int(b12+feeder_num)}LA",
                "symbol_lbl": f"{int(b12+feeder_num)}", "earth_lbl3": earth_lbl3, "ict_lbl": f"{int(b12+feeder_num)}ICT", "rect_lbl": f"{int(b12+feeder_num)}Reactor"
            }
            if bay_num % 3 == 0:
                labels["base_isolator"], labels["base_isolatorb"], labels["earth_lbl1"], labels["earth_lbl2"] = \
                    labels["base_isolatorb"], labels["base_isolator"], labels["earth_lbl2"], labels["earth_lbl1"]
            return labels

        def common(ax, x_offset, y_offset, feeder_num, fs, i):
            L = get_labels(feeder_num, i)
            draw_isolator(ax, x_offset+.25, y_offset,L["base_isolator"], fs)
            earth_sh(ax, x_offset+.25, y_offset-.5, L["earth_lbl1"], fs)
            draw_breaker(ax, x_offset+0.25, y_offset-2.2, L["breaker_lbl"], fs)
            earth_sh(ax, x_offset+0.25, y_offset-3.6, L["earth_lbl2"], fs)
            draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["base_isolatorb"], fs)
            draw_ct(ax, x_offset+0.25, y_offset-3.5, L["ct_lbl"], fs)
            ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-3.2, y_offset-4.6+.2], color='red', linewidth=0.5)
            draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)
            n=i+1
            if n == d6 and (n - 1) % 3 == 0: earth_sh(ax, x_offset+.25, y_offset+1.1, L["earth_lbl_BUS"], fs)
            if n == d7 and (n - 3) % 3 == 0: earth_sh(ax, x_offset+.25, y_offset-4.9, L["earth_lbl_BUS"], fs)

        def middle_common(ax, x_offset, y_offset, feeder_num, fs, i):
            L = get_labels(feeder_num, i)
            draw_isolator(ax, x_offset+.25, y_offset+1.1-.5,L["base_isolator"], fs)
            earth_sh(ax, x_offset+.25, y_offset+.6-.5, L["earth_lbl1"], fs)
            ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-.15-.4, y_offset-.5-1.5], color='red', linewidth=0.5)
            draw_breaker(ax, x_offset+0.25, y_offset-2.2-.3-.5, L["breaker_lbl"], fs)
            earth_sh(ax, x_offset+0.25, y_offset-3.6-.1-.5, L["earth_lbl2"], fs)
            draw_isolator(ax, x_offset+0.25, y_offset-4.6-.1-.5, L["base_isolatorb"], fs)
            ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-3.2-.8, y_offset-4.6-.6], color='red', linewidth=0.5)
            draw_name(ax, x_offset-0.5, y_offset-3-.6,L["symbol_lbl"], fs)

        def draw_feeder1(ax, x_offset, y_offset, feeder_num, fs, i):
            L, n = get_labels(feeder_num, i), i+1
            if (n - 1) % 3 == 0:
                common(ax, x_offset, y_offset, feeder_num, fs, i)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                ax.plot([x_offset+.25, x_offset+.75], [y_offset-5.8, y_offset-5.8], color='red', linewidth=0.5)
                ax.plot([x_offset+.75, x_offset+.75], [y_offset-5.8, y_offset+6.3], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset+0.75,y_offset+2 , L["iso_lbl2"], fs)
                earth_sh(ax, x_offset+0.75, y_offset+3, L["earth_lbl3"], fs)
                draw_wt(ax, x_offset+.75, y_offset+3.2, L["wt_lbl"], fs)
                draw_cvt(ax, x_offset+.75, y_offset+5, L["cvt_lbl"], fs)
                draw_la(ax, x_offset+.75, y_offset+5.2, L["la_lbl"], fs)
                la_comp(ax, x_offset+.3, y_offset+5)
                draw_symbol_upp(ax, x_offset+.75, y_offset+6.4, L["symbol_lbl"], fs)
                draw_ct(ax, x_offset+0.25, y_offset-10.9, L["ct_lbl_middle"], fs)
            elif (n - 2) % 3 == 0: middle_common(ax, x_offset, y_offset, feeder_num, fs, i)
            elif (n - 3) % 3 == 0:
                common(ax, x_offset, y_offset, feeder_num, fs, i)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                ax.plot([x_offset+.25, x_offset+.75], [y_offset+.5, y_offset+.5], color='red', linewidth=0.5)
                ax.plot([x_offset+.75, x_offset+.75], [y_offset+.5, y_offset-11], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset+0.75, y_offset-7, L["iso_lbl2"], fs)
                earth_sh(ax, x_offset+0.75, y_offset-7.3, L["earth_lbl3"], fs)
                draw_wt(ax, x_offset+.75, y_offset-8.6, L["wt_lbl"], fs)
                draw_cvt(ax, x_offset+.75, y_offset-8.7, L["cvt_lbl"], fs)
                draw_la(ax, x_offset+.75, y_offset-10, L["la_lbl"], fs)
                la_comp(ax, x_offset+.3, y_offset-10.2)
                draw_symbol(ax, x_offset+.75, y_offset-11.1, L["symbol_lbl"], fs)
                draw_ct(ax, x_offset+0.25, y_offset+5, L["ct_lbl_middle"], fs)

        def draw_feeder2(ax, x_offset, y_offset, feeder_num, fs, i):
            L, n = get_labels(feeder_num, i), i+1
            if (n - 1) % 3 == 0:
                common(ax, x_offset, y_offset, feeder_num, fs, i)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                ax.plot([x_offset+.25, x_offset+.75], [y_offset-5.8, y_offset-5.8], color='red', linewidth=0.5)
                ax.plot([x_offset+.75, x_offset+.75], [y_offset-5.8, y_offset+6.3], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset+0.75,y_offset+2 , L["iso_lbl2"], fs)
                earth_sh(ax, x_offset+0.75, y_offset+3, L["earth_lbl3"], fs)
                draw_la(ax, x_offset+.75, y_offset+3.6, L["la_lbl"], fs)
                la_comp(ax, x_offset+.3, y_offset+3.4)
                draw_ict_upp(ax,x_offset+0.75, y_offset+5.2, L["ict_lbl"], fs)
                draw_symbol_upp(ax, x_offset+.75, y_offset+6.4, L["symbol_lbl"], fs)
            elif (n - 2) % 3 == 0: middle_common(ax, x_offset, y_offset, feeder_num, fs, i)
            elif (n - 3) % 3 == 0:
                common(ax, x_offset, y_offset, feeder_num, fs, i)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                ax.plot([x_offset+.25, x_offset+.75], [y_offset+.5, y_offset+.5], color='red', linewidth=0.5)
                ax.plot([x_offset+.75, x_offset+.75], [y_offset+.5, y_offset-11.5], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset+0.75, y_offset-7, L["iso_lbl2"], fs)
                earth_sh(ax, x_offset+0.75, y_offset-7.3, L["earth_lbl3"], fs)
                draw_ict(ax,x_offset+0.75, y_offset-10, L["ict_lbl"], fs)
                draw_la(ax, x_offset+.75, y_offset-9, L["la_lbl"], fs)
                la_comp(ax, x_offset+.3, y_offset-9.2)
                draw_symbol(ax, x_offset+.75, y_offset-11.6, L["symbol_lbl"], fs)

        def draw_feeder3(ax, x_offset, y_offset, feeder_num, fs, i):
            L, n = get_labels(feeder_num, i), i+1
            if (n - 1) % 3 == 0:
                common(ax, x_offset, y_offset, feeder_num, fs, i)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                ax.plot([x_offset+.25, x_offset+.75], [y_offset-5.8, y_offset-5.8], color='red', linewidth=0.5)
                ax.plot([x_offset+.75, x_offset+.75], [y_offset-5.8, y_offset+6.3], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset+0.75,y_offset+2 , L["iso_lbl2"], fs)
                earth_sh(ax, x_offset+0.75, y_offset+3, L["earth_lbl3"], fs)
                draw_la(ax, x_offset+.75, y_offset+3.6, L["la_lbl"], fs)
                la_comp(ax, x_offset+.3, y_offset+3.4)
                draw_reacter(ax,x_offset+0.75, y_offset+5.2, L["rect_lbl"], fs)
                draw_earth_symbol_upp(ax, x_offset+.75, y_offset+6.6, L["symbol_lbl"], fs)
            elif (n - 2) % 3 == 0: middle_common(ax, x_offset, y_offset, feeder_num, fs, i)
            elif (n - 3) % 3 == 0:
                common(ax, x_offset, y_offset, feeder_num, fs, i)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                ax.plot([x_offset+.25, x_offset+.75], [y_offset+.5, y_offset+.5], color='red', linewidth=0.5)
                ax.plot([x_offset+.75, x_offset+.75], [y_offset+.5, y_offset-11.5], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset+0.75, y_offset-7, L["iso_lbl2"], fs)
                earth_sh(ax, x_offset+0.75, y_offset-7.3, L["earth_lbl3"], fs)
                draw_reacter(ax,x_offset+0.75, y_offset-10, L["rect_lbl"], fs)
                draw_la(ax, x_offset+.75, y_offset-9, L["la_lbl"], fs)
                la_comp(ax, x_offset+.3, y_offset-9.2)
                draw_earth_symbol(ax, x_offset+.75, y_offset-11.6, L["symbol_lbl"], fs)

        def draw_feeder4(ax, x_offset, y_offset, feeder_num, fs, i):
            L, n = get_labels(feeder_num, i), i+1
            if (n - 1) % 3 == 0:
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset+.25, y_offset,L["base_isolator"], fs)
                earth_sh(ax, x_offset+.25, y_offset-.5, L["earth_lbl1"], fs)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-1, y_offset-5.95], color='red', linewidth=0.5)
                draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)
                draw_ct(ax, x_offset+0.25, y_offset-10.9, L["ct_lbl_middle"], fs)
            elif (n - 2) % 3 == 0: middle_common(ax, x_offset, y_offset, feeder_num, fs, i)
            elif (n - 3) % 3 == 0:
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                earth_sh(ax, x_offset+0.25, y_offset-3.6, L["earth_lbl2"], fs)
                draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["base_isolatorb"], fs)
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.45, y_offset-4.6], color='red', linewidth=0.5)
                draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)
                draw_ct(ax, x_offset+0.25, y_offset+5, L["ct_lbl_middle"], fs)

        def draw_feeder5(ax, x_offset, y_offset, feeder_num, fs, i):
            L, n = get_labels(feeder_num, i), i+1
            if (n - 1) % 3 == 0: 
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset-6], color='red', linewidth=0.5)
                draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)
            elif (n - 2) % 3 == 0: middle_common(ax, x_offset, y_offset, feeder_num, fs, i)
            elif (n - 3) % 3 == 0:
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.5, y_offset-6.4], color='red', linewidth=0.5)
                draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)

        # -------------------------------------------------------------
        # PLOTTING EXECUTION (STRICTLY BOUND TO YOUR UI NUMBER)
        # -------------------------------------------------------------
        num_feeders_int = int(num_feeders)
        fig_width = max(12, num_feeders_int/4 * 6)
        fig, ax = plt.subplots(figsize=(fig_width, 18))
        x_start, y_start, gap = 5, 19.8, 3
        fontsize = get_fontsize(num_feeders_int)
        feeders_per_column, y_gap, x_gap = 3, 6.8, gap

        ax.plot([1, num_feeders_int*2], [20.7,20.7], color='blue', linewidth=0.5)
        ax.plot([1, num_feeders_int*2], [-.2,-.2], color='green', linewidth=0.5)

        for i in range(num_feeders_int):
            f_type = feeder_types[i]
            f_name = feeder_names[i]
            col = i // feeders_per_column       
            row = i % feeders_per_column        
            x_pos = x_start + col * x_gap
            y_pos = y_start - row * y_gap       
            feeder_label = i + 1

            if f_type == 'Line_Bay': 
                draw_feeder1(ax, x_pos, y_pos, feeder_label, fontsize, i)
            elif f_type == 'ICT': 
                draw_feeder2(ax, x_pos, y_pos, feeder_label, fontsize, i)
            elif f_type == 'Reactor': 
                draw_feeder3(ax, x_pos, y_pos, feeder_label, fontsize, i)
            elif f_type == 'Future_Bay': 
                draw_feeder4(ax, x_pos, y_pos, feeder_label, fontsize, i)
            elif f_type == 'No_bay': 
                draw_feeder5(ax, x_pos, y_pos, feeder_label, fontsize, i)
            else: 
                draw_feeder1(ax, x_pos, y_pos, feeder_label, fontsize, i)

            n = i + 1
            words = f_name.split()
            lines, current_line = [], ""
            for word in words:
                if len(current_line + " " + word) <= 24:
                    current_line = current_line + " " + word if current_line else word
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line: lines.append(current_line)
            wrapped_text = "\n".join(lines)

            full_text = f"{b12 + feeder_label}\n{wrapped_text}"
            y_label_pos = y_start + 8.5 if n % 3 == 1 else None if n % 3 == 2 else y_start - 26
            
            if y_label_pos is not None:
                ax.text(x_pos+.75, y_label_pos, full_text, ha='center', va='top', fontsize=fontsize+1)
        
        center_x = (x_start + (num_feeders_int/3)*gap)/2
        ax.text(1.5, 21.1, f"{b12} KV_BUS1", fontsize=fontsize+4, va='center')
        ax.text(1.5, .1, f"{b12} KV_BUS2", fontsize=fontsize+4, va='center')
        ax.text(center_x, 32, b8, fontsize=fontsize+25, va='center', ha='center')  
        ax.text(center_x, 30, b9, fontsize=fontsize+15, va='center', ha='center')  

        ax.set_xlim(0, x_start + num_feeders_int/3 * gap + x_start)
        ax.set_ylim(-10,35)  
        ax.axis('off')

        st.pyplot(fig)
        pdf_io, dxf_io = io.BytesIO(), io.StringIO()
        fig.savefig(pdf_io, format='pdf', bbox_inches='tight')
        export_ax_to_dxf(ax).write(dxf_io)

        st.success("✅ Generation Complete!")
        col1, col2 = st.columns(2)
        with col1: st.download_button("📥 Download PDF", data=pdf_io.getvalue(), file_name="Substation_SLD.pdf", mime="application/pdf")
        with col2: st.download_button("📥 Download AutoCAD DXF", data=dxf_io.getvalue(), file_name="Substation_SLD.dxf", mime="application/dxf")

```
