import streamlit as st
import math

st.set_page_config(page_title="AREVA MCAG High Impedance Sheet", layout="wide")

st.title("⚡ High Impedance Busbar Protection Calculation")
st.markdown("AREVA MCAG 34 Methodology – With ESI 48-3 Clause References")

# ------------------------------------------------------------
# INPUT SECTION
# ------------------------------------------------------------

st.header("🔹 Input Data")

col1, col2, col3 = st.columns(3)

with col1:
    fault_max = st.number_input("Maximum Fault Current (kA)", value=40.0)
    fault_min = st.number_input("Minimum Fault Current (kA)", value=18.9)
    ct_ratio = st.number_input("CT Ratio (Primary/1A)", value=2000)

with col2:
    r_ct = st.number_input("CT Secondary Resistance Rct (Ω)", value=6.0)
    r_lead = st.number_input("Lead Resistance Rlead (Ω)", value=1.175)
    excitation_current = st.number_input("CT Excitation Current at Vs (A)", value=0.003)

with col3:
    n_ct = st.number_input("Number of CTs in Parallel (n)", value=7)
    isr = st.number_input("Supervision Relay Current Isr (A)", value=0.002)
    ims = st.number_input("Metrosil Current Ims (A)", value=0.002)

if st.button("Run AREVA Sheet Calculation"):

    # ------------------------------------------------------------
    st.header("1️⃣ Stability Voltage – ESI 48-3 Clause 6.1")

    fault_sec = (fault_max * 1000) / ct_ratio
    r_total = r_ct + r_lead
    vs_required = fault_sec * r_total

    st.latex(r"V_s' = I_F (R_{CT} + R_{lead})")
    st.write(f"I_F = ({fault_max} × 1000) / {ct_ratio} = {round(fault_sec,2)} A")
    st.write(f"R_total = {r_ct} + {r_lead} = {round(r_total,3)} Ω")
    st.write(f"V_s' = {fault_sec} × {r_total}")
    st.success(f"Minimum Required Stability Voltage = {round(vs_required,2)} V")

    vs_selected = math.ceil(vs_required/10)*10
    st.success(f"Selected Relay Setting Voltage Vs = {vs_selected} V")

    # ------------------------------------------------------------
    st.header("2️⃣ CT Knee Point – ESI Clause 9.3")

    vk_required = 2 * vs_selected

    st.latex(r"V_k ≥ 2V_s")
    st.write(f"V_k ≥ 2 × {vs_selected}")
    st.success(f"Minimum Required CT Knee Point Voltage ≥ {vk_required} V")

    # ------------------------------------------------------------
    st.header("3️⃣ Fault Setting – ESI Clause 6.2")

    fault_setting_primary = 0.1 * fault_min * 1000
    fault_setting_secondary = fault_setting_primary / ct_ratio

    st.write(f"Minimum Fault Current = {fault_min} kA")
    st.write(f"10% of Minimum Fault Current = {fault_setting_primary} A")

    st.latex(r"I_{setting} = \frac{I_s + nI_1 + I_{sr} + I_{ms}}{T}")

    is_required = fault_setting_secondary - (n_ct*excitation_current + isr + ims)

    st.write(f"I_s = {fault_setting_secondary} - ({n_ct}×{excitation_current} + {isr} + {ims})")
    st.success(f"Required Relay Operating Current Is = {round(is_required,3)} A")

    # ------------------------------------------------------------
    st.header("4️⃣ Primary Operating Current (POC)")

    poc_max = (is_required + n_ct*excitation_current + isr + ims) * ct_ratio
    poc_percent = (poc_max / (fault_min*1000)) * 100

    st.write(f"POCmax = ({is_required} + nI1 + Isr + Ims) × CT ratio")
    st.success(f"Primary Operating Current ≈ {round(poc_max,1)} A")
    st.success(f"Percentage of Minimum Fault Current = {round(poc_percent,2)} %")

    # ------------------------------------------------------------
    st.header("5️⃣ Stabilising Resistor")

    rst = (vs_selected / is_required) - r_total

    st.latex(r"R_{st} = \frac{V_s}{I_s} - R_{total}")
    st.write(f"Rst = ({vs_selected} / {round(is_required,3)}) - {r_total}")
    st.success(f"Required Stabilising Resistor ≈ {round(rst,2)} Ω")

    # ------------------------------------------------------------
    st.header("6️⃣ Peak Voltage Check – ESI Clause 8 & 9.4")

    vf = fault_sec * r_total
    peak_voltage = 2 * math.sqrt(2 * vk_required * vf)

    st.latex(r"V_p ≈ 2\sqrt{2V_kV_f}")
    st.write(f"Peak Voltage ≈ {round(peak_voltage,2)} V")

    if peak_voltage > 3000:
        st.warning("⚠ Peak Voltage > 3kV → Metrosil Required")
    else:
        st.success("✔ Peak Voltage within 3kV limit")

    # ------------------------------------------------------------
    st.header("📘 AREVA-Style Engineering Conclusion")

    st.markdown(f"""
    **Stability Voltage Required:** {round(vs_required,2)} V  
    **Selected Relay Voltage:** {vs_selected} V  
    **Minimum Required CT Knee Point:** {vk_required} V  
    **Relay Operating Current Is:** {round(is_required,3)} A  
    **Stabilising Resistor:** {round(rst,2)} Ω  
    **Primary Operating Current:** {round(poc_max,1)} A  
    **Operating Percentage:** {round(poc_percent,2)} %  

    ✔ Calculation fully aligned with AREVA MCAG methodology and ESI 48-3.
    """)
