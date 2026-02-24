import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Arc
import matplotlib.patches as mpatches
import io
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment

# --- GEOMETRICALLY PERFECT DXF ENGINE ---
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
st.set_page_config(page_title="Intelligent SLD Generator", layout="wide")
st.title("⚡ Intelligent Substation SLD Generator")

with st.sidebar:
    st.header("1. Global Parameters")
    b8 = st.text_input("Project Title", value="Tamil Nadu Electricity Board")
    b9 = st.text_input("Subtitle / Station Name", value="400kV Substation")
    b12 = st.number_input("Voltage (kV)", value=400, step=11)
    b6 = st.selectbox("Bus Configuration", ["One and Half Breaker", "Double Main Bus", "Double Main Transfer Bus"])
    
    st.divider()
    st.header("2. Station Size")
    num_feeders = int(st.number_input("Enter total number of Bays:", min_value=1, value=6, step=1))

# --- DYNAMIC BAY GENERATION ---
st.subheader(f"Configure {num_feeders} Bays")
feeder_types = []
feeder_names = []

bay_options_dm = ["Line_Bay", "ICT", "Bus_Coupler", "Reactor", "Future_Bay", "Transfer_Bus_coupler", "Cable Feeder", "No_bay"]
bay_options_15 = ["Line_Bay", "ICT", "Reactor", "Future_Bay", "Cable Feeder", "Tie_Breaker", "No_bay"]

if b6 == "One and Half Breaker":
    st.info("💡 **One and a Half Breaker Scheme:** Middle bays are strictly locked to 'Tie_Breaker' to prevent architectural errors.")
    num_diameters = math.ceil(num_feeders / 3)
    
    for d in range(num_diameters):
        with st.container():
            st.markdown(f"#### Diameter {d+1}")
            cols = st.columns(3)
            
            for j in range(3):
                idx = d * 3 + j
                if idx < num_feeders:
                    with cols[j]:
                        if j == 0: 
                            position_label = "🔼 Top (Main Bus 1)"
                            default_idx = 0 
                            is_disabled = False
                        elif j == 1: 
                            position_label = "↔️ Middle (Tie Bay)"
                            default_idx = bay_options_15.index("Tie_Breaker") 
                            is_disabled = True 
                        else: 
                            position_label = "🔽 Bottom (Main Bus 2)"
                            default_idx = 0 
                            is_disabled = False
                            
                        st.markdown(f"**Bay {idx+1}: {position_label}**")
                        ftype = st.selectbox(f"Type", bay_options_15, index=default_idx, disabled=is_disabled, key=f"type_{idx}")
                        fname = st.text_input(f"Name", value=f"Bay No {idx+1}", key=f"name_{idx}")
                        feeder_types.append(ftype)
                        feeder_names.append(fname)
        st.write("---")

else:
    st.info("💡 **Double Main / Transfer Bus Detected:** Arranging bays in a horizontal sequence.")
    cols = st.columns(4)
    for i in range(num_feeders):
        with cols[i % 4]:
            st.markdown(f"**Bay {i+1}**")
            ftype = st.selectbox(f"Type", bay_options_dm, index=0, key=f"type_{i}")
            fname = st.text_input(f"Name", value=f"Bay No {i+1}", key=f"name_{i}")
            feeder_types.append(ftype)
            feeder_names.append(fname)
            st.write("---")

# --- GENERATION ---
if st.button("Generate AutoCAD DXF", type="primary"):
    
    errors = []
    if not b8.strip(): errors.append("❌ Project Title cannot be blank.")
    if not b9.strip(): errors.append("❌ Subtitle cannot be blank.")
    empty_bays = [str(i+1) for i, name in enumerate(feeder_names) if not name.strip()]
    if empty_bays: errors.append(f"❌ Missing names in Bays: {', '.join(empty_bays)}.")

    if errors:
        for error in errors: st.error(error)
        st.stop() 

    with st.spinner(f"Drafting Standards-Compliant Diagram..."):
        
        # --- DATA SANITIZATION ---
        for i in range(len(feeder_types)):
            if b6 in ["Double Main Transfer Bus", "Double Main Bus"]:
                if feeder_types[i] == "" or feeder_types[i] == "Future_Bay": 
                    feeder_types[i] = "Line_Bay"
            else:
                if feeder_types[i] in ["", "Cable Feeder"]: 
                    feeder_types[i] = "Line_Bay"

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
            if b6 == "Double Main Transfer Bus" :
                ax.plot([x, x], [y-.12, y+.2], color='red', linewidth=0.5)
                ax.text(x+.2, y-.2, label, fontsize=fs, ha='center')
            else:
                ax.plot([x, x], [y-.12, y+.4], color='red', linewidth=0.5)
                ax.text(x+.3, y-.3, label, fontsize=fs, ha='center')
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

        # =========================================================================
        # ARCHITECTURE 1: DOUBLE MAIN / TRANSFER BUS
        # =========================================================================
        if b6 in ["Double Main Transfer Bus", "Double Main Bus"]:
            fig_width = max(12, num_feeders * 2)
            fig, ax = plt.subplots(figsize=(fig_width, 6))
            x_start, y_start, gap = 5, 8.2, 2
            fontsize = 4 if num_feeders > 3 else 3

            def get_labels_dm(feeder_num):
                return {
                    "base_isolator" : f"{b12+feeder_num}89A", "base_isolatorb" : f"{b12+feeder_num}89B", "breaker_lbl" : f"{b12+feeder_num}52",
                    "earth_lbl1" : f"{b12+feeder_num}89AE", "earth_lbl2" : f"{b12+feeder_num}89CE1", "iso_lbl2" : f"{b12+feeder_num}89C",
                    "iso_lbl3" : f"{b12+feeder_num}89D", "ct_lbl" : f"{int((b12+feeder_num))}CT", "wt_lbl" : f"{int((b12+feeder_num))}WT",
                    "cvt_lbl" : f"{int((b12+feeder_num))}CVT", "la_lbl" : f"{int((b12+feeder_num))}LA", "symbol_lbl" : f"{int((b12+feeder_num))}",
                    "earth_lbl3" : f"{b12+feeder_num}89CE2", "ict_lbl" : f"{int((b12+feeder_num))}ICT", "rect_lbl" : f"{int((b12+feeder_num))}Reactor",
                    "symbol_lbl_Tcup" : f"{int((b12+feeder_num))} \n (TFR_Bus_coupler)", "earth_lbl1_Bcup" : f"{b12+feeder_num}89AE1",
                    "earth_lbl2_Bcup" : f"{b12+feeder_num}89AE2", "earth_lbl3_Bcup" : f"{b12+feeder_num}89BE1", "earth_lbl4_Bcup" : f"{b12+feeder_num}89BE2",
                    "symbol_lbl_Bcup" : f"{int((b12+feeder_num))} \n (Bus_coupler)", "No_bay_lbl" : f"{int((b12+feeder_num))} \n (Not Exist)"
                }

            def dm_draw_feeder1(ax, x_offset, y_offset, feeder_num, fs, f_type):
                L = get_labels_dm(feeder_num)
                ax.plot([x_offset, x_offset], [y_offset, y_offset+1.8], color='red', linewidth=0.5)
                ax.plot([x_offset+0.5, x_offset+0.5], [y_offset, y_offset+0.8], color='red', linewidth=0.5)
                ax.plot([x_offset, x_offset+0.5], [y_offset-1.2, y_offset-1.2], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset, y_offset, L["base_isolator"], fs)
                draw_isolator(ax, x_offset+0.5, y_offset, L["base_isolatorb"], fs)
                earth_sh(ax, x_offset, y_offset, L["earth_lbl1"], fs)
                draw_breaker(ax, x_offset+0.25, y_offset-2.2, L["breaker_lbl"], fs)
                if b6=="Double Main Transfer Bus":
                    ax.plot([x_offset+.25, x_offset+0.5], [y_offset-4.5, y_offset-4.5], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.5, x_offset+0.5], [y_offset-4.5, y_offset-7.5], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.5, x_offset+0.5], [y_offset-7.75, y_offset-10], color='red', linewidth=0.5)
                    earth_sh(ax, x_offset+0.25, y_offset-2.2, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-3.2, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-3.2, L["earth_lbl3"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["iso_lbl3"], fs)
                    draw_ct(ax, x_offset+0.5, y_offset-6.7, L["ct_lbl"], fs)
                    if f_type=="Cable Feeder": ax.plot([x_offset+0.5, x_offset+0.5], [y_offset-7.5, y_offset-7.75], color='red', linewidth=0.5)
                    else: draw_wt(ax, x_offset+0.5, y_offset-7.6, L["wt_lbl"], fs)
                    draw_cvt(ax, x_offset+0.5, y_offset-7.7, L["cvt_lbl"], fs)
                    draw_la(ax, x_offset+0.5, y_offset-9, L["la_lbl"], fs)
                    la_comp(ax, x_offset, y_offset-9.2)
                    draw_name(ax, x_offset+0.25, y_offset+1.75,L["symbol_lbl"], fs)
                    draw_symbol(ax, x_offset+0.5, y_offset-10.1, L["symbol_lbl"], fs)
                elif b6=="Double Main Bus":
                    ax.plot([x_offset+.25, x_offset+0.25], [y_offset-2.7, y_offset-4.5], color='red', linewidth=0.5)
                    draw_ct(ax, x_offset+0.25, y_offset-3.4, L["ct_lbl"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-3.7, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.7, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-4.85, L["earth_lbl3"], fs)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.9, y_offset-6.55], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-6.75, y_offset-10.4], color='red', linewidth=0.5)
                    if f_type=="Cable Feeder": ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-6.55, y_offset-6.75], color='red', linewidth=0.5)
                    else: draw_wt(ax, x_offset+0.25, y_offset-6.6, L["wt_lbl"], fs)
                    draw_cvt(ax, x_offset+0.25, y_offset-7, L["cvt_lbl"], fs)
                    draw_la(ax, x_offset+0.25, y_offset-8.5, L["la_lbl"], fs)
                    la_comp(ax, x_offset-0.25, y_offset-8.7)
                    draw_name(ax, x_offset+0.25, y_offset+1.75,L["symbol_lbl"], fs)
                    draw_symbol(ax, x_offset+0.25, y_offset-10.5, L["symbol_lbl"], fs)

            def dm_draw_feeder2(ax, x_offset, y_offset, feeder_num, fs):
                L = get_labels_dm(feeder_num)
                ax.plot([x_offset, x_offset], [y_offset, y_offset+1.8], color='red', linewidth=0.5)
                ax.plot([x_offset+0.5, x_offset+0.5], [y_offset, y_offset+0.8], color='red', linewidth=0.5)
                ax.plot([x_offset, x_offset+0.5], [y_offset-1.2, y_offset-1.2], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset, y_offset, L["base_isolator"], fs)
                draw_isolator(ax, x_offset+0.5, y_offset, L["base_isolatorb"], fs)
                earth_sh(ax, x_offset, y_offset, L["earth_lbl1"], fs)
                draw_breaker(ax, x_offset+0.25, y_offset-2.2, L["breaker_lbl"], fs)
                if b6=="Double Main Transfer Bus":
                    ax.plot([x_offset+.25, x_offset+0.5], [y_offset-4.5, y_offset-4.5], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.5, x_offset+0.5], [y_offset-4.5, y_offset-8.85], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.5, x_offset+0.5], [y_offset-10, y_offset-11.1], color='red', linewidth=0.5)
                    earth_sh(ax, x_offset+0.25, y_offset-2.2, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-3.2, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-3.2, L["earth_lbl3"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["iso_lbl3"], fs)
                    draw_ct(ax, x_offset+0.5, y_offset-6.7, L["ct_lbl"], fs)
                    draw_la(ax,x_offset+0.5, y_offset-7.6, L["la_lbl"], fs)
                    la_comp(ax, x_offset, y_offset-7.8)
                    draw_ict(ax,x_offset+0.5, y_offset-9, L["ict_lbl"], fs)
                    draw_symbol(ax, x_offset+0.5, y_offset-11.2, L["symbol_lbl"], fs)
                    draw_name(ax, x_offset+0.25, y_offset+1.75, L["symbol_lbl"], fs)
                elif b6=="Double Main Bus":
                    ax.plot([x_offset+.25, x_offset+0.25], [y_offset-2.7, y_offset-4.5], color='red', linewidth=0.5)
                    draw_ct(ax, x_offset+0.25, y_offset-3.4, L["ct_lbl"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-3.7, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.7, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-4.85, L["earth_lbl3"], fs)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.9, y_offset-7.8], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-9, y_offset-10.1], color='red', linewidth=0.5)
                    draw_la(ax,x_offset+0.25, y_offset-6.6, L["la_lbl"], fs)
                    la_comp(ax, x_offset-.25, y_offset-6.8)
                    draw_ict(ax,x_offset+0.25, y_offset-8, L["ict_lbl"], fs)
                    draw_symbol(ax, x_offset+0.25, y_offset-10.2, L["symbol_lbl"], fs)
                    draw_name(ax, x_offset+0.25, y_offset+1.75, L["symbol_lbl"], fs)

            def dm_draw_feeder3(ax, x_offset, y_offset, feeder_num, fs):
                L = get_labels_dm(feeder_num)
                ax.plot([x_offset, x_offset], [y_offset, y_offset+1.8], color='red', linewidth=0.5)
                ax.plot([x_offset+0.5, x_offset+0.5], [y_offset, y_offset+0.8], color='red', linewidth=0.5)
                ax.plot([x_offset, x_offset+0.5], [y_offset-1.2, y_offset-1.2], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset, y_offset, L["base_isolator"], fs)
                draw_isolator(ax, x_offset+0.5, y_offset, L["base_isolatorb"], fs)
                earth_sh(ax, x_offset, y_offset, L["earth_lbl1"], fs)
                draw_breaker(ax, x_offset+0.25, y_offset-2.2, L["breaker_lbl"], fs)
                if b6=="Double Main Transfer Bus":
                    ax.plot([x_offset+.25, x_offset+0.5], [y_offset-4.5, y_offset-4.5], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.5, x_offset+0.5], [y_offset-4.5, y_offset-8.85], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.5, x_offset+0.5], [y_offset-10, y_offset-11.1], color='red', linewidth=0.5)
                    earth_sh(ax, x_offset+0.25, y_offset-2.2, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-3.2, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-3.2, L["earth_lbl3"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["iso_lbl3"], fs)
                    draw_ct(ax, x_offset+0.5, y_offset-6.7, L["ct_lbl"], fs)
                    draw_la(ax,x_offset+0.5, y_offset-7.6, L["la_lbl"], fs)
                    la_comp(ax, x_offset, y_offset-7.8)
                    draw_reacter(ax,x_offset+0.5, y_offset-9, L["rect_lbl"], fs)
                    draw_earth_symbol(ax, x_offset+0.5, y_offset-11.2, L["symbol_lbl"], fs)
                    draw_name(ax, x_offset+0.25, y_offset+1.75, L["symbol_lbl"], fs)
                elif b6=="Double Main Bus":
                    ax.plot([x_offset+.25, x_offset+0.25], [y_offset-2.7, y_offset-4.5], color='red', linewidth=0.5)
                    draw_ct(ax, x_offset+0.25, y_offset-3.4, L["ct_lbl"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-3.7, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.7, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-4.85, L["earth_lbl3"], fs)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.9, y_offset-7.85], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-9, y_offset-10.1], color='red', linewidth=0.5)
                    draw_la(ax,x_offset+0.25, y_offset-6.6, L["la_lbl"], fs)
                    la_comp(ax, x_offset-.25, y_offset-6.8)
                    draw_reacter(ax,x_offset+0.25, y_offset-8, L["rect_lbl"], fs)
                    draw_earth_symbol(ax, x_offset+0.25, y_offset-10.2, L["symbol_lbl"], fs)
                    draw_name(ax, x_offset+0.25, y_offset+1.75, L["symbol_lbl"], fs)

            def dm_draw_feeder4(ax, x_offset, y_offset, feeder_num, fs, f_type):
                L = get_labels_dm(feeder_num)
                if b6=="Double Main Transfer Bus":
                    ax.plot([x_offset, x_offset], [y_offset, y_offset+1.8], color='red', linewidth=0.5)
                    ax.plot([x_offset+.5, x_offset+.5], [y_offset, y_offset+0.8], color='red', linewidth=0.5)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-3.2, y_offset-4.6], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset, y_offset,L["base_isolator"], fs)
                    draw_isolator(ax, x_offset+0.5, y_offset, L["base_isolatorb"], fs)
                    earth_sh(ax, x_offset, y_offset, L["earth_lbl1"], fs)
                    ax.plot([x_offset, x_offset+0.5], [y_offset-1.2, y_offset-1.2], color='red', linewidth=0.5)
                    draw_breaker(ax, x_offset+0.25, y_offset-2.2, L["breaker_lbl"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-3.6, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.25, y_offset-4.6, L["earth_lbl3"], fs)
                    draw_ct(ax, x_offset+0.25, y_offset-3.5, L["ct_lbl"], fs)
                    draw_name(ax, x_offset+0.25, y_offset+1.75, L["symbol_lbl_Tcup"], fs)
                elif b6=="Double Main Bus": dm_draw_feeder1(ax, x_offset, y_offset, feeder_num, fs, f_type)

            def dm_draw_feeder5(ax, x_offset, y_offset, feeder_num, fs):
                L = get_labels_dm(feeder_num)
                ax.plot([x_offset-.2, x_offset-.2], [y_offset-.3, y_offset+1.8], color='red', linewidth=0.5)
                ax.plot([x_offset+0.7, x_offset+.7], [y_offset-.3, y_offset+0.8], color='red', linewidth=0.5)
                ax.plot([x_offset-.2, x_offset-.2], [y_offset-4, y_offset-1.5], color='red', linewidth=0.5)
                ax.plot([x_offset+0.7, x_offset+.7], [y_offset-4, y_offset-1.5], color='red', linewidth=0.5)
                draw_isolator(ax, x_offset-.2, y_offset-.3, L["base_isolator"], fs)
                draw_isolator(ax, x_offset+0.7, y_offset-.3, L["base_isolatorb"], fs)
                earth_sh(ax, x_offset-0.2, y_offset+.8, L["earth_lbl1_Bcup"], fs)
                earth_sh(ax, x_offset-0.2, y_offset-.5, L["earth_lbl2_Bcup"], fs)
                earth_sh(ax, x_offset+.7, y_offset+.8, L["earth_lbl3_Bcup"], fs)
                earth_sh(ax, x_offset+.7, y_offset-.5, L["earth_lbl4_Bcup"], fs)
                draw_ct(ax, x_offset-0.2, y_offset-2.5, L["ct_lbl"], fs)
                draw_breaker_coupler(ax, x_offset+0.25, y_offset-4, L["breaker_lbl"], fs)
                draw_name(ax, x_offset+0.25, y_offset+1.75, L["symbol_lbl_Bcup"], fs)

            def dm_draw_feeder6(ax, x_offset, y_offset, feeder_num, fs):
                L = get_labels_dm(feeder_num)
                draw_name(ax, x_offset+0.25, y_offset+1.75, L["No_bay_lbl"], fs)

            for i in range(num_feeders):
                f_type, f_name, x_pos, feeder_label = feeder_types[i], feeder_names[i], x_start + i * gap, i + 1
                ax.plot([1, num_feeders*3], [10, 10], color='blue', linewidth=0.5)
                ax.text(1.5, 10.5, f"{b12} KV_BUS1", fontsize=fontsize+4,  va='center')
                ax.plot([1, num_feeders*3], [9, 9], color='green', linewidth=0.5)
                ax.text(1.5, 9.5, f"{b12} KV_BUS2", fontsize=fontsize+4,  va='center')
                if b6=="Double Main Transfer Bus":
                    ax.plot([1, num_feeders*3], [2.4, 2.4], color='black', linewidth=0.5)
                    ax.text(1.5, 2.4+.5, f"{b12} KV_Transfer BUS", fontsize=fontsize+4,  va='center')

                if f_type in ['Line_Bay', 'Tie_Breaker']: dm_draw_feeder1(ax, x_pos, y_start, feeder_label, fontsize, f_type)
                elif f_type == 'ICT' : dm_draw_feeder2(ax, x_pos, y_start, feeder_label, fontsize)
                elif f_type == 'Reactor' : dm_draw_feeder3(ax, x_pos, y_start, feeder_label, fontsize)
                elif f_type == 'Transfer_Bus_coupler' : dm_draw_feeder4(ax, x_pos, y_start, feeder_label, fontsize, f_type)
                elif f_type == 'Bus_Coupler' : dm_draw_feeder5(ax, x_pos, y_start, feeder_label, fontsize)
                elif f_type == 'No_bay' : dm_draw_feeder6(ax, x_pos, y_start, feeder_label, fontsize)
                elif f_type == 'Cable Feeder' : dm_draw_feeder1(ax, x_pos, y_start, feeder_label, fontsize, f_type)
                else: dm_draw_feeder1(ax, x_pos, y_start, feeder_label, fontsize, f_type)

                words, lines, current_line = f_name.split(), [], ""
                for word in words:
                    if len(current_line + " " + word) <= 24: current_line = current_line + " " + word if current_line else word
                    else: lines.append(current_line); current_line = word
                if current_line: lines.append(current_line)
                wrapped_text = "\n".join(lines)
                full_text = f"{b12 + feeder_label}\n{wrapped_text}"
                if b6=="Double Main Transfer Bus": ax.text(x_pos+.5, y_start-12, full_text, ha='center', va='top', fontsize=fontsize+1)
                elif b6=="Double Main Bus": ax.text(x_pos+.25, y_start-11.25, full_text, ha='center', va='top', fontsize=fontsize+1)

            center_x = x_start + ((num_feeders - 1) * gap) / 2.0
            ax.text(center_x, 14, b8, fontsize=fontsize+25, va='center', ha='center')  
            ax.text(center_x, 12, b9, fontsize=fontsize+15, va='center', ha='center')  
            ax.set_xlim(1,(num_feeders)*2+6); ax.set_ylim(-6*1.05, 1.5*10.5); ax.axis('off')

        # =========================================================================
        # ARCHITECTURE 2: ONE AND A HALF BREAKER
        # =========================================================================
        else:
            num_cols = math.ceil(num_feeders / 3.0)
            fig_width = max(12, num_cols * 4) 
            fig, ax = plt.subplots(figsize=(fig_width, 18))
            x_start, y_start, x_gap, y_gap, feeders_per_column, fontsize = 5, 19.8, 3, 6.8, 3, 4

            def get_labels_15(feeder_num, i):
                bay_num, earth_label, current_type = i + 1, f"{b12+feeder_num}89AE", feeder_types[i]
                ct_label = f"{int(b12+feeder_num)}CT"
                if current_type == "ICT": iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89T", f"{b12+feeder_num}89TE"
                elif current_type == "Line_Bay": iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89L", f"{b12+feeder_num}89LE"
                elif current_type == "Reactor": iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89R", f"{b12+feeder_num}89RE"
                else: iso_lbl2, earth_lbl3 = f"{b12+feeder_num}89C", f"{b12+feeder_num}89CE"
                labels = {
                    "base_isolator": f"{b12+feeder_num}89A", "base_isolatorb": f"{b12+feeder_num}89B", "breaker_lbl": f"{b12+feeder_num}52",
                    "earth_lbl1": earth_label, "earth_lbl2": f"{b12+feeder_num}89BE", "iso_lbl2": iso_lbl2, "ct_lbl": f"{int(b12+feeder_num)}CT", 
                    "wt_lbl": f"{int(b12+feeder_num)}WT", "cvt_lbl": f"{int(b12+feeder_num)}CVT", "la_lbl": f"{int(b12+feeder_num)}LA",
                    "symbol_lbl": f"{int(b12+feeder_num)}", "earth_lbl3": earth_lbl3, "ict_lbl": f"{int(b12+feeder_num)}ICT", "rect_lbl": f"{int(b12+feeder_num)}Reactor",
                    "No_bay_lbl" : f"{int((b12+feeder_num))} \n (Not Exist)"
                }
                if bay_num % 3 == 0: labels["base_isolator"], labels["base_isolatorb"], labels["earth_lbl1"], labels["earth_lbl2"] = labels["base_isolatorb"], labels["base_isolator"], labels["earth_lbl2"], labels["earth_lbl1"]
                return labels

            def common_15(ax, x_offset, y_offset, feeder_num, fs, i):
                L = get_labels_15(feeder_num, i)
                draw_isolator(ax, x_offset+.25, y_offset,L["base_isolator"], fs)
                earth_sh(ax, x_offset+.25, y_offset-.5, L["earth_lbl1"], fs)
                draw_breaker(ax, x_offset+0.25, y_offset-2.2, L["breaker_lbl"], fs)
                earth_sh(ax, x_offset+0.25, y_offset-3.6, L["earth_lbl2"], fs)
                draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["base_isolatorb"], fs)
                draw_ct(ax, x_offset+0.25, y_offset-3.5, L["ct_lbl"], fs) 
                ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-3.2, y_offset-4.6+.2], color='red', linewidth=0.5)
                draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)

            # --- GEOMETRICALLY SYMMETRIC TIE BAY (EQUI-SPACED FIX) ---
            def middle_common_15(ax, x_offset, y_offset, feeder_num, fs, i):
            L = get_labels_15(feeder_num, i)
            # Define absolute CB center reference for symmetry
            cb_center_y = y_offset - 2.5 
            
            # 1. TIE BREAKER (Center Reference)
            draw_breaker(ax, x_offset+0.25, cb_center_y, L["breaker_lbl"], fs)
            
            # --- TOP HALF (Symmetrical Upwards) ---
            # ACT: 1.25 units from center
            ct_a_lbl = L["ct_lbl"].replace("CT", "ACT")
            draw_ct(ax, x_offset+0.25, cb_center_y + 1.25, ct_a_lbl, fs)  
            
            # Top Earth Switch: 2.5 units from center
            earth_sh(ax, x_offset+0.25, cb_center_y + 2.5, L["earth_lbl1"], fs)
            
            # Top Isolator: 3.1 units from center
            draw_isolator(ax, x_offset+0.25, cb_center_y + 3.1, L["base_isolator"], fs)
            
            # --- BOTTOM HALF (Symmetrical Downwards) ---
            # BCT: 1.25 units from center
            ct_b_lbl = L["ct_lbl"].replace("CT", "BCT")
            draw_ct(ax, x_offset+0.25, cb_center_y - 1.25, ct_b_lbl, fs)  
            
            # Bottom Earth Switch: 2.5 units from center
            earth_sh(ax, x_offset+0.25, cb_center_y - 2.5, L["earth_lbl2"], fs)
            
            # Bottom Isolator: 3.1 units from center
            draw_isolator(ax, x_offset+0.25, cb_center_y - 3.1, L["base_isolatorb"], fs)
            
            # --- UNIFORM CONNECTING LINE ---
            # Perfectly spans from the top terminal to the bottom terminal
            ax.plot([x_offset+0.25, x_offset+0.25], [cb_center_y + 3.1, cb_center_y - 3.1], color='red', linewidth=0.5)
            draw_name(ax, x_offset-0.5, cb_center_y, L["symbol_lbl"], fs)

                def grid_draw_feeder1(ax, x_offset, y_offset, feeder_num, fs, i):
                L, n = get_labels_15(feeder_num, i), i+1
                if (n - 1) % 3 == 0:
                    common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                    ax.plot([x_offset+.25, x_offset+.75], [y_offset-5.8, y_offset-5.8], color='red', linewidth=0.5)
                    ax.plot([x_offset+.75, x_offset+.75], [y_offset-5.8, y_offset+6.3], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset+0.75,y_offset+2 , L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.75, y_offset+3, L["earth_lbl3"], fs)
                    draw_wt(ax, x_offset+.75, y_offset+3.2, L["wt_lbl"], fs); draw_cvt(ax, x_offset+.75, y_offset+5, L["cvt_lbl"], fs)
                    draw_la(ax, x_offset+.75, y_offset+5.2, L["la_lbl"], fs); la_comp(ax, x_offset+.3, y_offset+5)
                    draw_symbol_upp(ax, x_offset+.75, y_offset+6.4, L["symbol_lbl"], fs)
                elif (n - 2) % 3 == 0: middle_common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                elif (n - 3) % 3 == 0:
                    common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                    ax.plot([x_offset+.25, x_offset+.75], [y_offset+.5, y_offset+.5], color='red', linewidth=0.5)
                    ax.plot([x_offset+.75, x_offset+.75], [y_offset+.5, y_offset-11], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset+0.75, y_offset-7, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.75, y_offset-7.3, L["earth_lbl3"], fs)
                    draw_wt(ax, x_offset+.75, y_offset-8.6, L["wt_lbl"], fs); draw_cvt(ax, x_offset+.75, y_offset-8.7, L["cvt_lbl"], fs)
                    draw_la(ax, x_offset+.75, y_offset-10, L["la_lbl"], fs); la_comp(ax, x_offset+.3, y_offset-10.2)
                    draw_symbol(ax, x_offset+.75, y_offset-11.1, L["symbol_lbl"], fs)

            def grid_draw_feeder2(ax, x_offset, y_offset, feeder_num, fs, i):
                L, n = get_labels_15(feeder_num, i), i+1
                if (n - 1) % 3 == 0:
                    common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                    ax.plot([x_offset+.25, x_offset+.75], [y_offset-5.8, y_offset-5.8], color='red', linewidth=0.5)
                    ax.plot([x_offset+.75, x_offset+.75], [y_offset-5.8, y_offset+6.3], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset+0.75,y_offset+2 , L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.75, y_offset+3, L["earth_lbl3"], fs)
                    draw_la(ax, x_offset+.75, y_offset+3.6, L["la_lbl"], fs); la_comp(ax, x_offset+.3, y_offset+3.4)
                    draw_ict_upp(ax,x_offset+0.75, y_offset+5.2, L["ict_lbl"], fs)
                    draw_symbol_upp(ax, x_offset+.75, y_offset+6.4, L["symbol_lbl"], fs)
                elif (n - 2) % 3 == 0: middle_common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                elif (n - 3) % 3 == 0:
                    common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                    ax.plot([x_offset+.25, x_offset+.75], [y_offset+.5, y_offset+.5], color='red', linewidth=0.5)
                    ax.plot([x_offset+.75, x_offset+.75], [y_offset+.5, y_offset-11.5], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset+0.75, y_offset-7, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.75, y_offset-7.3, L["earth_lbl3"], fs)
                    draw_ict(ax,x_offset+0.75, y_offset-10, L["ict_lbl"], fs)
                    draw_la(ax, x_offset+.75, y_offset-9, L["la_lbl"], fs); la_comp(ax, x_offset+.3, y_offset-9.2)
                    draw_symbol(ax, x_offset+.75, y_offset-11.6, L["symbol_lbl"], fs)

            def grid_draw_feeder3(ax, x_offset, y_offset, feeder_num, fs, i):
                L, n = get_labels_15(feeder_num, i), i+1
                if (n - 1) % 3 == 0:
                    common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                    ax.plot([x_offset+.25, x_offset+.75], [y_offset-5.8, y_offset-5.8], color='red', linewidth=0.5)
                    ax.plot([x_offset+.75, x_offset+.75], [y_offset-5.8, y_offset+6.3], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset+0.75,y_offset+2 , L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.75, y_offset+3, L["earth_lbl3"], fs)
                    draw_la(ax, x_offset+.75, y_offset+3.6, L["la_lbl"], fs); la_comp(ax, x_offset+.3, y_offset+3.4)
                    draw_reacter(ax,x_offset+0.75, y_offset+5.2, L["rect_lbl"], fs)
                    draw_earth_symbol_upp(ax, x_offset+.75, y_offset+6.6, L["symbol_lbl"], fs)
                elif (n - 2) % 3 == 0: middle_common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                elif (n - 3) % 3 == 0:
                    common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                    ax.plot([x_offset+.25, x_offset+.75], [y_offset+.5, y_offset+.5], color='red', linewidth=0.5)
                    ax.plot([x_offset+.75, x_offset+.75], [y_offset+.5, y_offset-11.5], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset+0.75, y_offset-7, L["iso_lbl2"], fs)
                    earth_sh(ax, x_offset+0.75, y_offset-7.3, L["earth_lbl3"], fs)
                    draw_reacter(ax,x_offset+0.75, y_offset-10, L["rect_lbl"], fs)
                    draw_la(ax, x_offset+.75, y_offset-9, L["la_lbl"], fs); la_comp(ax, x_offset+.3, y_offset-9.2)
                    draw_earth_symbol(ax, x_offset+.75, y_offset-11.6, L["symbol_lbl"], fs)

            def grid_draw_feeder4(ax, x_offset, y_offset, feeder_num, fs, i):
                L, n = get_labels_15(feeder_num, i), i+1
                if (n - 1) % 3 == 0:
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.9, y_offset+.4], color='red', linewidth=0.5)
                    draw_isolator(ax, x_offset+.25, y_offset,L["base_isolator"], fs)
                    earth_sh(ax, x_offset+.25, y_offset-.5, L["earth_lbl1"], fs)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-1, y_offset-5.95], color='red', linewidth=0.5)
                    draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)
                elif (n - 2) % 3 == 0: middle_common_15(ax, x_offset, y_offset, feeder_num, fs, i)
                elif (n - 3) % 3 == 0:
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset-5.8, y_offset-6.4], color='red', linewidth=0.5)
                    earth_sh(ax, x_offset+0.25, y_offset-3.6, L["earth_lbl2"], fs)
                    draw_isolator(ax, x_offset+0.25, y_offset-4.6, L["base_isolatorb"], fs)
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+.45, y_offset-4.6], color='red', linewidth=0.5)
                    draw_name(ax, x_offset-0.5, y_offset-3,L["symbol_lbl"], fs)

            def grid_draw_feeder5(ax, x_offset, y_offset, feeder_num, fs, i):
                L, n = get_labels_15(feeder_num, i), i+1
                if (n - 2) % 3 == 0: 
                    ax.plot([x_offset+0.25, x_offset+0.25], [y_offset+1.1, y_offset-4.6], color='red', linewidth=0.5)
                    draw_name(ax, x_offset-0.5, y_offset-3,L["No_bay_lbl"], fs)
                else: draw_name(ax, x_offset-0.5, y_offset-3,L["No_bay_lbl"], fs)

            for i in range(num_feeders):
                f_type, f_name, col, row = feeder_types[i], feeder_names[i], i // feeders_per_column, i % feeders_per_column
                x_pos, y_pos, feeder_label = x_start + col * x_gap, y_start - row * y_gap, i + 1
                ax.plot([1, num_cols*x_gap + 8], [20.7,20.7], color='blue', linewidth=0.5)
                ax.plot([1, num_cols*x_gap + 8], [-.2,-.2], color='green', linewidth=0.5)

                if f_type in ['Line_Bay', 'Tie_Breaker']: grid_draw_feeder1(ax, x_pos, y_pos, feeder_label, fontsize, i)
                elif f_type == 'ICT': grid_draw_feeder2(ax, x_pos, y_pos, feeder_label, fontsize, i)
                elif f_type == 'Reactor': grid_draw_feeder3(ax, x_pos, y_pos, feeder_label, fontsize, i)
                elif f_type == 'Future_Bay': grid_draw_feeder4(ax, x_pos, y_pos, feeder_label, fontsize, i)
                elif f_type == 'No_bay': grid_draw_feeder5(ax, x_pos, y_pos, feeder_label, fontsize, i)
                else: grid_draw_feeder1(ax, x_pos, y_pos, feeder_label, fontsize, i)

                n, words, lines, current_line = i + 1, f_name.split(), [], ""
                for word in words:
                    if len(current_line + " " + word) <= 24: current_line = current_line + " " + word if current_line else word
                    else: lines.append(current_line); current_line = word
                if current_line: lines.append(current_line)
                wrapped_text = "\n".join(lines)
                full_text = f"{b12 + feeder_label}\n{wrapped_text}"
                y_label_pos = y_start + 8.5 if n % 3 == 1 else None if n % 3 == 2 else y_start - 26
                if y_label_pos is not None: ax.text(x_pos+.75, y_label_pos, full_text, ha='center', va='top', fontsize=fontsize+1)
            
            center_x = x_start + ((num_cols - 1) * x_gap) / 2.0
            ax.text(1.5, 21.1, f"{b12} KV_BUS1", fontsize=fontsize+4, va='center')
            ax.text(1.5, .1, f"{b12} KV_BUS2", fontsize=fontsize+4, va='center')
            ax.text(center_x, 32, b8, fontsize=fontsize+25, va='center', ha='center')  
            ax.text(center_x, 30, b9, fontsize=fontsize+15, va='center', ha='center')  
            ax.set_xlim(0, x_start + num_cols * x_gap + 2); ax.set_ylim(-15, 38); ax.axis('off')

        # =========================================================================
        # RENDER AND EXPORT 
        # =========================================================================
        st.pyplot(fig)
        pdf_io, dxf_io = io.BytesIO(), io.StringIO()
        fig.savefig(pdf_io, format='pdf', bbox_inches='tight')
        export_ax_to_dxf(ax).write(dxf_io)
        st.success("✅ Generation Complete!")
        col1, col2 = st.columns(2)
        with col1: st.download_button("📥 Download PDF", data=pdf_io.getvalue(), file_name="Substation_SLD.pdf", mime="application/pdf")
        with col2: st.download_button("📥 Download AutoCAD DXF", data=dxf_io.getvalue(), file_name="Substation_SLD.dxf", mime="application/dxf")
