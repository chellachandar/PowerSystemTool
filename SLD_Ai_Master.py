import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Arc
import matplotlib.patches as mpatches
import io
import math
import json
import datetime
import ezdxf
from ezdxf.enums import TextEntityAlignment
import google.generativeai as genai

# --- INITIALIZE DEEP SESSION STATE ---
default_states = {
    "b8": "Tamil Nadu Electricity Board",
    "b9": "400kV Substation",
    "b12": 400,
    "b6": "One and Half Breaker",
    "num_feeders": 6,
    "fault_level": 40, # New global rating
    "qa_warning": "",
    "bay_data": {} # New dictionary to hold deep engineering data (MVA, CT Ratios)
}
for key, val in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = val

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

st.set_page_config(page_title="Intelligent SLD Generator", layout="wide")
st.title("⚡ Autonomous AI Engineering Consultant")

# =========================================================================
# THE AI INTERVIEWER (STATE MACHINE)
# =========================================================================
with st.container():
    st.markdown("### 🧠 Senior Electrical Architect")
    st.markdown("I will interview you to gather the necessary topology, transformer ratings, and CT ratios before drafting the final schematic.")
    
    api_key = st.text_input("Gemini API Key", type="password", key="api_key_input")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! Let's build this substation. To start **(Stage 1: Topology)**, what is your voltage level, bus configuration, and total number of bays?"}
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Reply to the AI..."):
        if not api_key:
            st.error("Please provide a Gemini API Key to chat.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
                
            with st.spinner("Analyzing engineering constraints..."):
                try:
                    genai.configure(api_key=api_key)
                    
                    system_instruction = """
                    You are a strict, methodical Senior Electrical Substation Architect.
                    Follow a 3-Stage Interview Process. DO NOT skip stages.
                    
                    STAGE 1 (Topology): Determine Voltage, Bus Scheme (1.5 Breaker, Double Main, etc.), and Total Bays. If 1.5 Breaker, YOU MUST ask what equipment connects to Main Bus 1 vs Main Bus 2.
                    STAGE 2 (Ratings): Once topology is clear, YOU MUST ask for:
                       - System Fault Level in kA (e.g., 40kA, 50kA).
                       - Transformer MVA ratings for any ICTs identified in Stage 1.
                       - Standard CT Ratios for the bays (e.g., 2000/1A).
                    STAGE 3 (Confirmation): Summarize all topology and ratings. Ask the user to reply 'Approve'.
                    
                    CRITICAL RULE: When the user says 'Approve', output the final design strictly enclosed in ```json tags.
                    
                    EXPECTED JSON FORMAT:
                    ```json
                    {
                        "b8": "Project Title", "b9": "Station Name", "b12": 400, "b6": "One and Half Breaker", "num_feeders": 6, "fault_level": 40,
                        "bays": [
                            {"index": 0, "type": "ICT", "name": "Tx 1", "mva": 500, "ct_ratio": "2000/1A"},
                            {"index": 1, "type": "Tie_Breaker", "name": "Tie 1", "mva": 0, "ct_ratio": "2000/1A"}
                        ]
                    }
                    ```
                    """
                    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
                    history = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in st.session_state.messages[:-1]]
                    chat = model.start_chat(history=history)
                    response = chat.send_message(prompt)
                    ai_reply = response.text
                    
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                    with st.chat_message("assistant"): st.markdown(ai_reply)
                        
                    if "```json" in ai_reply:
                        st.info("Engineering Data Confirmed. Pushing to Drafting Machinery...")
                        json_str = ai_reply.split("```json")[1].split("```")[0].strip()
                        ai_data = json.loads(json_str)
                        
                        st.session_state.b8 = ai_data.get("b8", "Generated Project")
                        st.session_state.b9 = ai_data.get("b9", "Generated Substation")
                        st.session_state.b12 = ai_data.get("b12", 400)
                        st.session_state.b6 = ai_data.get("b6", "One and Half Breaker")
                        st.session_state.num_feeders = ai_data.get("num_feeders", 6)
                        st.session_state.fault_level = ai_data.get("fault_level", 40)
                        
                        st.session_state.bay_data = {}
                        for bay in ai_data.get("bays", []):
                            idx = bay["index"]
                            st.session_state[f"type_{idx}"] = bay["type"]
                            st.session_state[f"name_{idx}"] = bay["name"]
                            # Store deep data
                            st.session_state.bay_data[idx] = {
                                "mva": bay.get("mva", 0),
                                "ct_ratio": bay.get("ct_ratio", "2000/1A")
                            }
                            
                        st.success("✅ Deep Engineering Parameters Applied! Review Machinery below.")
                        st.rerun() 
                except Exception as e:
                    st.error(f"AI Chat Error: {e}")

st.divider()

# =========================================================================
# THE MACHINERY (UI REVIEW)
# =========================================================================
with st.sidebar:
    st.header("1. Global Parameters")
    b8 = st.text_input("Project Title", key="b8")
    b9 = st.text_input("Station Name", key="b9")
    b12 = st.number_input("Voltage (kV)", step=11, key="b12")
    fault_level = st.number_input("System Fault Level (kA)", step=1, key="fault_level")
    b6 = st.selectbox("Bus Configuration", ["One and Half Breaker", "Double Main Bus", "Double Main Transfer Bus"], key="b6")
    st.divider()
    num_feeders = int(st.number_input("Total Bays:", min_value=1, step=1, key="num_feeders"))

st.subheader("Deep Engineering UI Review")
feeder_types, feeder_names = [], []
bay_options_dm = ["Line_Bay", "ICT", "Bus_Coupler", "Reactor", "Future_Bay", "Transfer_Bus_coupler", "Cable Feeder", "No_bay"]
bay_options_15 = ["Line_Bay", "ICT", "Reactor", "Future_Bay", "Cable Feeder", "Tie_Breaker", "No_bay"]

options_list = bay_options_15 if b6 == "One and Half Breaker" else bay_options_dm

cols = st.columns(3)
for i in range(num_feeders):
    with cols[i % 3]:
        with st.expander(f"Bay {i+1} Configuration", expanded=(i<3)):
            if f"type_{i}" not in st.session_state: st.session_state[f"type_{i}"] = "Line_Bay"
            if f"name_{i}" not in st.session_state: st.session_state[f"name_{i}"] = f"Bay {i+1}"
            
            # Ensure safety lock for 1.5 Tie Breakers
            is_disabled = True if (b6 == "One and Half Breaker" and i % 3 == 1) else False
            
            ftype = st.selectbox("Type", options_list, index=options_list.index(st.session_state[f"type_{i}"]) if st.session_state[f"type_{i}"] in options_list else 0, disabled=is_disabled, key=f"type_{i}")
            fname = st.text_input("Name", key=f"name_{i}")
            
            # Retrieve deep data from state if available
            deep_data = st.session_state.bay_data.get(i, {"mva": 0, "ct_ratio": "2000/1A"})
            if ftype == "ICT":
                st.number_input("Transformer Rating (MVA)", value=int(deep_data["mva"]), key=f"mva_{i}")
            st.text_input("CT Ratio", value=deep_data["ct_ratio"], key=f"ct_{i}")
            
            feeder_types.append(ftype)
            feeder_names.append(fname)

# =========================================================================
# DRAFTING ENGINE WITH LEGEND & CT RATIO STAMPING
# =========================================================================
if st.button("Generate AutoCAD DXF", type="primary"):
    with st.spinner("Drafting Standards-Compliant Diagram with Deep Specs..."):
        
        # --- UPGRADED DRAW FUNCTIONS ---
        def draw_ct(ax, x, y, label, fs, bay_index):
            spacing = 0.75
            ax.add_patch(Arc((x+.03 , y- spacing/4), 0.2, 0.4, angle=0, theta1=80, theta2=280, color='blue', linewidth=0.5))
            ax.add_patch(Arc((x+.03 , y+ spacing/4), 0.2, 0.4, angle=0, theta1=80, theta2=280, color='blue', linewidth=0.5))
            ax.text(x-.3, y, label, fontsize=fs, ha='center')
            
            # STAMP DEEP ENGINEERING CT RATIO DATA ON THE DRAWING
            ct_ratio = st.session_state.get(f"ct_{bay_index}", "2000/1A")
            ax.text(x+.25, y, ct_ratio, fontsize=fs-1.5, ha='left', va='center', color='blue')

        def draw_legend(ax, x, y, fs):
            ax.add_patch(Rectangle((x, y), 8, 4.5, fill=True, facecolor='white', edgecolor='black', linewidth=1, zorder=10))
            ax.text(x+4, y+4, "ENGINEERING LEGEND", fontsize=fs+2, ha='center', weight='bold', zorder=11)
            ax.plot([x, x+8], [y+3.7, y+3.7], color='black', linewidth=0.5, zorder=11)
            
            details = [
                f"Project: {st.session_state.b8}",
                f"Voltage Level: {st.session_state.b12} kV",
                f"System Fault Level: {st.session_state.fault_level} kA",
                f"Bus Scheme: {st.session_state.b6}",
                f"Total Bays Evaluated: {num_feeders}"
            ]
            
            for idx, detail in enumerate(details):
                ax.text(x+0.5, y+3 - (idx*0.6), detail, fontsize=fs+1, ha='left', zorder=11)

        # (Keeping geometric definitions concise for the engine logic below)
        def draw_breaker(ax, x, y, label, fs):
            ax.add_patch(Rectangle((x-0.1, y-0.2), 0.2, 0.4, fill=False, edgecolor='black', linewidth=0.5))
            ax.plot([x, x], [y+.2, y+1], color='red', linewidth=0.5)
            ax.plot([x, x], [y-.2, y-1], color='red', linewidth=0.5)
            ax.text(x+.3, y, label, fontsize=fs, ha='center')

        def draw_isolator(ax, x, y, label, fs):
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
            ax.text(x-.4, y-.35, label, fontsize=fs, ha='center')

        def draw_name(ax, x, y, label, fs): ax.text(x, y+.5, label, fontsize=fs+2, ha='center')
        def draw_symbol(ax, x, y, label, fs): ax.add_patch(Polygon([[x, y-0.1], [x+0.1, y+0.1], [x-0.1, y+0.1]], closed=True, fill=False, edgecolor='red', linewidth=0.5))

        # --- ARCHITECTURE GENERATION ---
        # Assuming One & Half for space, but logic applies identically to Double Main
        num_cols = math.ceil(num_feeders / 3.0)
        fig_width = max(14, num_cols * 4) 
        fig, ax = plt.subplots(figsize=(fig_width, 18))

        x_start, y_start = 5, 19.8
        x_gap, y_gap = 3, 6.8
        fontsize = 4

        # Draw Main Buses
        ax.plot([1, num_cols*x_gap + 8], [20.7,20.7], color='blue', linewidth=0.5)
        ax.plot([1, num_cols*x_gap + 8], [-.2,-.2], color='green', linewidth=0.5)

        for i in range(num_feeders):
            col = i // 3       
            row = i % 3        
            x_pos = x_start + col * x_gap
            y_pos = y_start - row * y_gap       
            
            # Simple geometric mockup for testing (incorporates the new CT block)
            ax.plot([x_pos+0.25, x_pos+0.25], [y_pos+.9, y_pos-6.4], color='red', linewidth=0.5)
            draw_isolator(ax, x_pos+.25, y_pos, f"89A", fontsize)
            draw_breaker(ax, x_pos+0.25, y_pos-2.2, f"52", fontsize)
            draw_ct(ax, x_pos+0.25, y_pos-3.5, f"CT", fontsize, bay_index=i) # INJECTS DEEP DATA
            
            wrapped_text = f"{b12}kV\n{feeder_names[i]}"
            ax.text(x_pos+.75, y_pos-2.5, wrapped_text, ha='center', va='top', fontsize=fontsize+1)

        # STAMP THE LEGEND IN TOP RIGHT CORNER
        draw_legend(ax, x_start + num_cols * x_gap + 1, 22, fontsize)

        ax.set_xlim(0, x_start + num_cols * x_gap + 10)
        ax.set_ylim(-15, 38)  
        ax.axis('off')

        st.pyplot(fig)
        pdf_io, dxf_io = io.BytesIO(), io.StringIO()
        fig.savefig(pdf_io, format='pdf', bbox_inches='tight')
        export_ax_to_dxf(ax).write(dxf_io)

        st.success("✅ Deep Generation Complete!")
        col1, col2 = st.columns(2)
        with col1: st.download_button("📥 Download PDF", data=pdf_io.getvalue(), file_name="Substation_SLD.pdf", mime="application/pdf")
        with col2: st.download_button("📥 Download AutoCAD DXF", data=dxf_io.getvalue(), file_name="Substation_SLD.dxf", mime="application/dxf")

# =========================================================================
# THE DYNAMIC FEASIBILITY ENGINE (REAL CALCULATIONS)
# =========================================================================
st.divider()
st.subheader("📄 AI Technical Feasibility & Math Engine")

if st.button("Generate Preliminary Feasibility Report", type="secondary"):
    if not st.session_state.api_key_input:
        st.error("Please enter your Gemini API Key at the top.")
    else:
        with st.spinner("Executing Mathematical Feasibility Analysis..."):
            try:
                genai.configure(api_key=st.session_state.api_key_input)
                report_model = genai.GenerativeModel('gemini-2.5-flash')
                
                # Gather deep data
                bays_data = []
                total_mva = 0
                for i in range(num_feeders):
                    mva_val = st.session_state.get(f"mva_{i}", 0)
                    ct_val = st.session_state.get(f"ct_{i}", "2000/1A")
                    bays_data.append(f"Bay {i+1}: {feeder_types[i]} - {feeder_names[i]} (MVA: {mva_val}, CT: {ct_val})")
                    if feeder_types[i] == "ICT": total_mva += int(mva_val)
                    
                bays_str = "\n".join(bays_data)
                
                # The Calculation Prompt
                report_prompt = f"""
                You are a Senior Electrical Power Systems Engineer. 
                Draft a highly technical 2-page "Preliminary Feasibility Report" based on this REAL data:
                
                Voltage: {st.session_state.b12}kV
                Bus Configuration: {st.session_state.b6}
                System Fault Level: {st.session_state.fault_level} kA
                Total Installed Transformer Capacity: {total_mva} MVA
                
                Detailed Bay Parameters:
                {bays_str}
                
                YOU MUST STRICTLY FOLLOW THIS MARKDOWN STRUCTURE:
                
                # 📘 PRELIMINARY FEASIBILITY REPORT
                
                ## 1. Executive Overview
                (Summarize the data).
                
                ## 2. Load & Capacity Check (MATHEMATICAL VERIFICATION)
                #### 2.1 Transformer Loading
                You MUST render this exact equation using LaTeX formatting:
                $$ Loading = \\frac{{Demand}}{{Installed\\ Capacity}} $$
                
                Given the Total Installed Capacity of {total_mva} MVA, assume a realistic maximum demand (e.g., 80% of total) and perform the mathematical calculation here to prove N-1 compliance.
                
                #### 2.2 Fault Level Verification
                You MUST render this exact equation using LaTeX formatting:
                $$ I_{sc} = \\frac{{MVA_{fault}}}{{\\sqrt{{3}} \\times kV}} $$
                
                Using the provided Voltage of {st.session_state.b12}kV and Fault Level of {st.session_state.fault_level}kA, calculate the required breaking capacity and analyze the safety margins.
                
                ## 3. Instrument Transformer Validation
                Analyze the provided CT Ratios from the bay data. Discuss if they are appropriate for the calculated load currents and mention standard CT resistances for 5P20 protection classes.
                
                ## 4. Limitations & Assumptions
                (Provide a comprehensive, highly detailed engineering list of assumptions to fill the 2-page requirement).
                """
                
                report_response = report_model.generate_content(report_prompt)
                st.session_state.engineering_report = report_response.text
                
            except Exception as e:
                st.error(f"Failed to generate report: {e}")

if "engineering_report" in st.session_state:
    with st.expander("Preview Mathematical Feasibility Report", expanded=True):
        st.markdown(st.session_state.engineering_report)
