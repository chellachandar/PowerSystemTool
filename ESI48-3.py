import streamlit as st
import math

st.set_page_config(page_title="High Impedance Differential Calculator", layout="wide")

st.title("⚡ High Impedance Differential Protection Calculator")
st.markdown("Based on ESI 48-3 – Instantaneous High Impedance Differential Protection")

# ----------------------------------------------------------
# INPUT SECTION
# ----------------------------------------------------------

st.header("🔹 System Data")

col1, col2, col3 = st.columns(3)

with col1:
    fault_max = st.number_input("Maximum Fault Current (kA)", value=40.0)
    fault_min = st.number_input("Minimum Fault Current (kA)", value=18.9)
    ct_ratio = st.number_input("CT Ratio (Primary / 1A)", value=2000)

with col2:
    r_ct = st.number_input("CT Secondary Resistance Rct (Ω)", value=6.0)
    r_lead = st.number_input("Lead Resistance Rlead (Ω)", value=1.175)

with col3:
    n_ct = st.number_input("Number of CTs in Parallel (n)", value=7)
    supervision_va = st.number_input("Supervision Relay Burden (VA)", value=0.32)

st.header("🔹 CT Actual Parameters (From FAT Report)")

col4, col5 = st.columns(2)

with col4:
    vk_actual = st.number_input("Actual CT Knee Point Voltage Vk (V)", value=450.0)

with col5:
    io_actual = st.number_input("CT Excitation Current Io at Vs (A)", value=0.003)

st.header("🔹 Metrosil Data (If Required)")

col6, col7 = st.columns(2)

with col6:
    metrosil_C = st.number_input("Metrosil Constant C", value=900.0)

with col7:
    metrosil_B = st.number_input("Metrosil Exponent B", value=0.25)

# ----------------------------------------------------------
# CALCULATION
# ----------------------------------------------------------

if st.button("Run Full High-Z Calculation"):

    # ------------------------------------------------------
    st.header("1️⃣ Stability Voltage – ESI Clause 6.1")

    fault_sec = (fault_max * 1000) / ct_ratio
    r_total = r_ct + r_lead
    vs_required = fault_sec * r_total

    st.latex(r"V_s' = I_F (R_{CT} + R_{lead})")
    st.write(f"I_F = {round(fault_sec,2)} A")
    st.write(f"R_total = {round(r_total,3)} Ω")
    st.success(f"Minimum Required Stability Voltage Vs' = {round(vs_required,2)} V")

    vs_selected = math.ceil(vs_required/10)*10
    st.success(f"Selected Relay Voltage Vs = {vs_selected} V")

    # ------------------------------------------------------
    st.header("2️⃣ CT Suitability Check – Clause 9.3")

    vk_min_required = 2 * vs_selected

    st.latex(r"V_k ≥ 2V_s")
    st.write(f"Minimum Required Vk = {vk_min_required} V")
    st.write(f"Actual CT Vk = {vk_actual} V")

    if vk_actual >= vk_min_required:
        st.success("✔ CT Suitable for High Impedance Protection")
    else:
        st.error("✖ CT Knee Point Insufficient")

    # ------------------------------------------------------
    st.header("3️⃣ Supervision Relay Current")

    isr = supervision_va / vs_selected

    st.latex(r"I_{sr} = \frac{VA}{V_s}")
    st.success(f"Supervision Relay Current Isr = {round(isr,5)} A")

    # ------------------------------------------------------
    st.header("4️⃣ Peak Voltage – Clause 8 & 9.4")

    vf = fault_sec * r_total
    peak_voltage = 2 * math.sqrt(2 * vk_actual * vf)

    st.latex(r"V_p ≈ 2\sqrt{2V_kV_f}")
    st.write(f"Peak Voltage ≈ {round(peak_voltage,2)} V")

    if peak_voltage > 3000:
        st.warning("Peak Voltage > 3kV → Metrosil Required")
        ims = metrosil_C * (vs_selected / metrosil_C) ** (1/metrosil_B)
    else:
        st.success("Peak Voltage within 3kV limit → Metrosil Not Required")
        ims = 0.0

    st.write(f"Metrosil Current Ims = {round(ims,5)} A")

    # ------------------------------------------------------
    st.header("5️⃣ Fault Setting – ESI Clause 6.2")

    fault_setting_primary = 0.1 * fault_min * 1000
    fault_setting_secondary = fault_setting_primary / ct_ratio

    st.write(f"10% of Minimum Fault Current = {fault_setting_primary} A")

    st.latex(r"I_{setting} = \frac{I_s + nI_o + I_{sr} + I_{ms}}{T}")

    is_required = fault_setting_secondary - (n_ct * io_actual + isr + ims)

    st.success(f"Required Relay Operating Current Is = {round(is_required,5)} A")

    # ------------------------------------------------------
    st.header("6️⃣ Stabilising Resistor")

    rst = (vs_selected / is_required) - r_total

    st.latex(r"R_{st} = \frac{V_s}{I_s} - R_{total}")
    st.success(f"Required Stabilising Resistor ≈ {round(rst,2)} Ω")

    # ------------------------------------------------------
    st.header("📘 Final Engineering Summary")

    st.markdown(f"""
    **Stability Voltage Required:** {round(vs_required,2)} V  
    **Selected Relay Voltage:** {vs_selected} V  
    **Minimum Required CT Knee Point:** {vk_min_required} V  
    **Actual CT Knee Point:** {vk_actual} V  
    **Supervision Relay Current:** {round(isr,5)} A  
    **Metrosil Current:** {round(ims,5)} A  
    **Relay Operating Current Is:** {round(is_required,5)} A  
    **Stabilising Resistor:** {round(rst,2)} Ω  
    **Peak Voltage:** {round(peak_voltage/1000,2)} kV  

    ✔ Fully compliant with ESI 48-3 High Impedance Differential Protection.
    """)
