import streamlit as st
import pandas as pd
import math
import tempfile
from fpdf import FPDF

# =====================================================
# PDF GENERATION FUNCTION
# =====================================================
def generate_pdf_report(mva, hv_kv, bus_fault_ka, rct, rlead, ir, existing_vk, ifl, ifault, df):
    # Initialize PDF in Landscape mode to fit the data table
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "ESI 48-3 High Impedance REF Calculation Report", ln=True, align="C")
    pdf.ln(5)

    # Section 1: System Data
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "1. System & Transformer Data", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Transformer MVA: {mva} MVA  |  HV Voltage: {hv_kv} kV  |  Bus Fault: {bus_fault_ka} kA", ln=True)
    pdf.cell(0, 6, f"CT Resistance (Rct): {rct} Ohms  |  Lead Resistance: {rlead} Ohms", ln=True)
    pdf.cell(0, 6, f"Relay Pickup (Ir): {ir} A  |  Existing Vk: {existing_vk} V", ln=True)
    pdf.ln(5)

    # Section 2: Derived Parameters
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "2. Derived System Parameters", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Full Load Current (IFL): {round(ifl, 2)} A", ln=True)
    pdf.cell(0, 6, f"Through Fault Current (Ifault): {round(ifault, 2)} A", ln=True)
    pdf.ln(5)

    # Section 3: Results Table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "3. CT Comparison Results", ln=True)
    pdf.set_font("Arial", "B", 10)

    # Define table columns and widths
    cols = ["CT Ratio", "Load OK", "Vs (V)", "Vk (Strict)", "Vk (Rec.)", "Rst (Ohm)", "Peak V", "Metrosil?"]
    widths = [25, 25, 20, 25, 25, 25, 25, 25]

    # Print Header
    for col, width in zip(cols, widths):
        pdf.cell(width, 8, col, border=1, align="C")
    pdf.ln()

    # Print Rows
    pdf.set_font("Arial", "", 9)
    for index, row in df.iterrows():
        # Clean emojis for the PDF text (FPDF doesn't handle emojis well by default)
        load_text = "YES" if "YES" in str(row["Load Adequate"]) else "NO"
        metrosil_text = "YES" if "YES" in str(row["Metrosil?"]) else "NO"
        
        pdf.cell(widths[0], 8, str(row["CT Ratio"]), border=1, align="C")
        pdf.cell(widths[1], 8, load_text, border=1, align="C")
        pdf.cell(widths[2], 8, str(row["Vs (V)"]), border=1, align="C")
        pdf.cell(widths[3], 8, str(row["Vk (Strict ESI)"]), border=1, align="C")
        pdf.cell(widths[4], 8, str(row["Vk (Recommended)"]), border=1, align="C")
        pdf.cell(widths[5], 8, str(row["Rst (Ω)"]), border=1, align="C")
        pdf.cell(widths[6], 8, str(row["Peak Voltage (V)"]), border=1, align="C")
        pdf.cell(widths[7], 8, metrosil_text, border=1, align="C")
        pdf.ln()

    # Save to a temporary file and return the bytes
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        with open(tmp_file.name, "rb") as f:
            return f.read()


# =====================================================
# STREAMLIT UI & CONFIG
# =====================================================
st.set_page_config(page_title="ESI REF Optimizer - Professional", layout="wide")

st.title("⚡ ESI 48-3 Compliant High Impedance REF Optimizer")

# =====================================================
# INPUT SECTION
# =====================================================
st.header("Transformer & System Data")

col1, col2 = st.columns(2)

with col1:
    mva = st.number_input("Transformer MVA", value=100.0, min_value=0.1)
    hv_kv = st.number_input("HV Voltage (kV)", value=220.0, min_value=0.1)
    bus_fault_ka = st.number_input("System Bus Fault Level (kA)", value=7.0, min_value=0.1)

with col2:
    rct = st.number_input("CT Secondary Resistance (Ω)", value=6.0, min_value=0.0)
    rlead = st.number_input("Lead Resistance (Ω)", value=1.0, min_value=0.0)
    ir = st.number_input("Relay Pickup Current (A)", value=0.1, min_value=0.001) # Prevent div by zero
    existing_vk = st.number_input("Existing CT Knee Point Vk (Optional)", value=0.0, min_value=0.0)

ct_input = st.text_input("Available CT Ratios (comma separated)", "400,600,800")


# =====================================================
# CALCULATION SECTION
# =====================================================
if st.button("Calculate REF Settings", type="primary"):

    ct_ratios = sorted([int(x.strip()) for x in ct_input.split(",")])

    # 1. Full Load Current
    ifl = (mva * 1000) / (math.sqrt(3) * hv_kv)

    # 2. Through Fault Current
    ifault = bus_fault_ka * 1000

    if bus_fault_ka > 25:
        st.warning("⚠ Fault level very high. High Impedance REF may become impractical. Consider Low Impedance REF.")

    results = []

    for ct in ct_ratios:
        load_ok = ct >= ifl
        isec_fault = ifault / ct

        # Stability Voltage (Vs) 
        vs = isec_fault * (rct + rlead)
        v_set = vs  # Setting voltage (Vset) is equal to Vs for max sensitivity

        # Strict ESI Knee Point (Vk >= 2 * Vset)
        vk_min = 2 * v_set

        # Engineering Recommended Knee Point
        vk_eng = 3 * v_set

        # Correct Stabilising Resistor (Based on Vset)
        rst = v_set / ir

        # Resistor Power Rating (Continuous rating at setting voltage)
        resistor_power = (v_set ** 2) / rst

        # Peak Voltage Calculation (ESI 48-3 Section 8)
        # Vf is the maximum prospective voltage if CT did not saturate
        v_f = isec_fault * (rct + rlead + rst)
        
        # Assume the installed CT meets the engineering recommended Vk if an existing one isn't provided
        vk_calc = existing_vk if existing_vk > 0 else vk_eng 
        
        if v_f > vk_calc:
            peak_voltage = 2 * math.sqrt(2 * vk_calc * (v_f - vk_calc))
        else:
            peak_voltage = v_f 
            
        # Metrosil Requirement (Vp > 3000V)
        metrosil_required = peak_voltage > 3000

        # Existing Vk validation
        margin = None
        verdict = "—"
        if existing_vk > 0:
            margin = existing_vk / vk_min
            verdict = "PASS" if existing_vk >= vk_min else "FAIL"

        results.append({
            "CT Ratio": f"{ct}/1",
            "Load Adequate": "✅ YES" if load_ok else "❌ NO",
            "I_sec Fault (A)": round(isec_fault, 2),
            "Vs (V)": round(vs, 2),
            "Vk (Strict ESI)": round(vk_min, 2),
            "Vk (Recommended)": round(vk_eng, 2),
            "Rst (Ω)": round(rst, 2),
            "Resistor Power (W)": round(resistor_power, 2),
            "Peak Voltage (V)": round(peak_voltage, 2),
            "Metrosil?": "🚨 YES" if metrosil_required else "NO",
            "Stability Factor": round(vk_min / vs if vs != 0 else 0, 2),
            "Verdict": verdict
        })

    df = pd.DataFrame(results)

    st.subheader("CT Comparison Results")
    
    # Pandas Styler to highlight warnings/fails
    def highlight_rows(row):
        if row["Verdict"] == "FAIL" or "❌" in row["Load Adequate"]:
            return ['background-color: #ffcccc'] * len(row)
        if "🚨" in row["Metrosil?"]:
            return ['background-color: #fff0b3'] * len(row)
        return [''] * len(row)

    styled_df = df.style.apply(highlight_rows, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    # =====================================================
    # PDF EXPORT BUTTON
    # =====================================================
    pdf_bytes = generate_pdf_report(
        mva, hv_kv, bus_fault_ka, rct, rlead, ir, existing_vk, ifl, ifault, df
    )
    
    st.download_button(
        label="📄 Download Official Calculation Report (PDF)",
        data=pdf_bytes,
        file_name="ESI_48_3_REF_Calculation.pdf",
        mime="application/pdf",
    )

    # =====================================================
    # CT AUTO SELECTION LOGIC
    # =====================================================
    df_valid = df[
        (df["Load Adequate"] == "✅ YES") &
        ((df["Verdict"] != "FAIL") if existing_vk > 0 else True)
    ]

    if not df_valid.empty:
        recommended_ct = df_valid.iloc[0]
        st.success(f"**Recommended CT Ratio:** {recommended_ct['CT Ratio']}")
    else:
        st.error("⚠ No CT satisfies both the full load and Vk requirements.")

    # =====================================================
    # DERIVED SYSTEM VALUES
    # =====================================================
    st.subheader("Derived System Parameters")

    colA, colB, colC = st.columns(3)

    with colA:
        st.metric("Full Load Current (A)", round(ifl, 2))
    with colB:
        st.metric("Through Fault Current (A)", round(ifault, 2))
    with colC:
        st.metric("Bus Fault Level (kA)", bus_fault_ka)

    st.markdown("---")

    # =====================================================
    # FORMULAE DISPLAY
    # =====================================================
    st.subheader("📘 Formulae Used (ESI 48-3 Basis)")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V}")
        st.latex(r"I_{sec} = \frac{I_{fault}}{CT}")
        st.latex(r"V_s = I_{sec} (R_{CT} + R_{lead})")
        st.latex(r"V_f = I_{sec} (R_{CT} + R_{lead} + R_{st})")
    with col_f2:
        st.latex(r"V_k(min) = 2 V_s")
        st.latex(r"V_k(eng) = 3 V_s")
        st.latex(r"R_{st} = \frac{V_s}{I_r}")
        st.latex(r"V_{p} = 2\sqrt{2V_k(V_f - V_k)}")
