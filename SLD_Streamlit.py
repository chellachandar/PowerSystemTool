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
            pts = [(x, y), (x+w), (x+w, y+h), (x, y+h)]
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
    st.info("💡 **One and a Half Breaker Scheme:** Middle bays are strictly locked to 'Tie_Breaker'.")
    num_diameters = math.ceil(num_feeders / 3)
    for d in range(num_diameters):
        with st.container():
            st.markdown(f"#### Diameter {d+1}")
            cols = st.columns(3)
            for j in range(3):
                idx = d * 3 + j
                if idx < num_feeders:
                    with cols[j]:
                        if j == 1: # Tie Bay
                            ftype = "Tie_Breaker"
                            st.selectbox(f"Type (Locked)", ["Tie_Breaker"], index=0, disabled=True, key=f"type_{idx}")
                        else:
                            ftype = st.selectbox(f"Type", bay_options_15, index=0, key=f"type_{idx}")
                        fname = st.text_input(f"Name", value=f"Bay No {idx+1}", key=f"name_{idx}")
                        feeder_types.append(ftype)
                        feeder_names.append(fname)
        st.write("---")
else:
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
    with st.spinner(f"Drafting Standards-Compliant Diagram..."):
        fig, ax = plt.subplots(figsize=(20, 20))
        
        # --- DRAFTING FUNCTIONS ---
        def draw_breaker(ax, x, y, label, fs):
            ax.add_patch(Rectangle((x-0.1, y-0.2), 0.2, 0.4, fill=False, edgecolor='black', linewidth=0.5))
            ax.plot([x, x], [y+.2, y+1], color='red', linewidth=0.5)
            ax.plot([x, x], [y-.2, y-1], color='red', linewidth=0.5)
            ax.text(x+.3, y, label, fontsize=fs, ha='center')

        def draw_isolator(ax, x, y, label, fs):
            ax.plot([x, x], [y-.12, y+.4], color='red', linewidth=0.5)
            ax.text(x+.3, y-.3, label, fontsize=fs, ha='center')
            ax.add_patch(Arc((x , y-0.15), 0.04, 0.08, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.add_patch(Arc((x , y-0.65), 0.04, 0.08, angle=0, theta1=0, theta2=360, color='red', linewidth=0.5))
            ax.plot([x-.05, x+.05], [y-.55, y-.25], color='red', linewidth=0.5)
            ax.plot([x, x], [y-.7, y-1.2], color='red', linewidth=0.5)

        def earth_sh(ax, x, y, label, fs):
            y_base = y - 0.2
            ax.plot([x, x-0.2], [y_base-0.6, y_base-0.6], color='red', linewidth=0.5)
            ax.plot([x-0.2, x-0.35], [y_base-0.35, y_base-0.6], color='green', linewidth=0.5)
            ax.plot([x-0.35, x-0.5], [y_base-0.6, y_base-0.6], color='green', linewidth=0.5)
            ax.text(x-0.4, y_base-0.35, label, fontsize=fs, ha='center')

        def draw_ct(ax, x, y, label, fs):
            ax.add_patch(Arc((x+0.03 , y-0.18), 0.2, 0.4, angle=0, theta1=80, theta2=280, color='blue', linewidth=0.5))
            ax.add_patch(Arc((x+0.03 , y+0.18), 0.2, 0.4, angle=0, theta1=80, theta2=280, color='blue', linewidth=0.5))
            ax.text(x-0.3, y, label, fontsize=fs, ha='center')

        def draw_name(ax, x, y, label, fs):
            ax.text(x, y+0.5, label, fontsize=fs+2, ha='center')

        if b6 == "One and Half Breaker":
            def get_labels_15(feeder_num, i):
                return {
                    "base_isolator": f"{b12+feeder_num}89A", 
                    "base_isolatorb": f"{b12+feeder_num}89B", 
                    "breaker_lbl": f"{b12+feeder_num}52",
                    "earth_lbl1": f"{b12+feeder_num}89AE", 
                    "earth_lbl2": f"{b12+feeder_num}89BE", 
                    "ct_lbl": f"{int(b12+feeder_num)}CT",
                    "symbol_lbl": f"{int(b12+feeder_num)}"
                }

            # --- THE SYMMETRICAL TIE BAY FUNCTION ---
            def middle_common_15(ax, x_offset, y_offset, feeder_num, fs, i):
                L = get_labels_15(feeder_num, i)
                cb_center_y = y_offset - 2.5 
                
                # 1. TIE BREAKER (Center Reference)
                draw_breaker(ax, x_offset+0.25, cb_center_y, L["breaker_lbl"], fs)
                
                # --- TOP HALF (Upwards) ---
                ct_a_lbl = L["ct_lbl"].replace("CT", "ACT")
                draw_ct(ax, x_offset+0.25, cb_center_y + 1.25, ct_a_lbl, fs)  
                earth_sh(ax, x_offset+0.25, cb_center_y + 2.5, L["earth_lbl1"], fs)
                draw_isolator(ax, x_offset+0.25, cb_center_y + 3.1, L["base_isolator"], fs)
                
                # --- BOTTOM HALF (Mirrored Downwards) ---
                ct_b_lbl = L["ct_lbl"].replace("CT", "BCT")
                draw_ct(ax, x_offset+0.25, cb_center_y - 1.25, ct_b_lbl, fs)  
                earth_sh(ax, x_offset+0.25, cb_center_y - 2.5, L["earth_lbl2"], fs)
                draw_isolator(ax, x_offset+0.25, cb_center_y - 3.1, L["base_isolatorb"], fs)
                
                # Continuous wire
                ax.plot([x_offset+0.25, x_offset+0.25], [cb_center_y + 3.1, cb_center_y - 3.1], color='red', linewidth=0.5)
                draw_name(ax, x_offset-0.5, cb_center_y, L["symbol_lbl"], fs)

            # Execution logic for drawing bays would follow here...
            for i in range(num_feeders):
                x_pos = 5 + (i // 3) * 3
                y_pos = 19.8 - (i % 3) * 6.8
                if (i % 3) == 1:
                    middle_common_15(ax, x_pos, y_pos, i+1, 4, i)

        ax.axis('off')
        st.pyplot(fig)
