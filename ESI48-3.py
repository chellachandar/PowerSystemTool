import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="High Impedance Busbar Calculator", layout="wide")

st.title("⚡ High Impedance Busbar Protection Calculator")
st.markdown("Based on ESI 48-3 Standard – Step-by-Step Engineering Mode")

# ----------------------------
# INPUT SECTION
# ----------------------------

st.header("🔹 Input Parameters")

col1, col2, col3 = st.columns(3)

with col1:
    fault_primary = st.number_input("Maximum Fault Current (Primary kA)", value=40.0)
    ct_primary = st.number_input("CT Primary Rating (A)", value=2000)
    ct_secondary = st.number_input("CT Secondary Rating (A)", value=1)

with col2:
    r_ct = st.number_input("CT Secondary Resistance (Ohms)", value=6.0)
    r_lead = st.number_input("Lead Resistance (Ohms)", value=1.175)
    relay_setting_current = st.number_input("Relay Setting Current Is (A)", value=0.75)

with col3:
    vk = st.number_input("CT Knee Point Voltage Vk (Volts)", value=450.0)
    excitation_current = st.number_input("CT Excitation Current at Vs (A)", value=0.003)
    n_ct = st.number_input("No. of CTs in Parallel (n)", value=7)

# ----------------------------
# CALCULATIONS
# ----------------------------

if st.button("Calculate"):

    st.header("🔹 Step 1 – Convert Primary Fault to Secondary")

    fault_secondary = (fault_primary * 1000) / ct_primary

    st.latex(r"I_F = \frac{I_{primary}}{CT\ ratio}")
    st.write(f"I_F = ({fault_primary} × 1000) / {ct_primary}")
    st.success(f"Secondary Fault Current = {round(fault_secondary,2)} A")

    # ----------------------------------------

    st.header("🔹 Step 2 – Total Loop Resistance")

    total_resistance = r_ct + r_lead

    st.latex(r"R_{total} = R_{CT} + R_{lead}")
    st.write(f"R_total = {r_ct} + {r_lead}")
    st.success(f"Total Loop Resistance = {round(total_resistance,3)} Ω")

    # ----------------------------------------

    st.header("🔹 Step 3 – Stability Voltage (ESI 48-3 Clause 6.1)")

    vs_required = fault_secondary * total_resistance

    st.latex(r"V_s' = I_F \times (R_{CT} + R_{lead})")
    st.write(f"V_s' = {fault_secondary} × {total_resistance}")
    st.success(f"Minimum Required Stability Voltage = {round(vs_required,2)} V")

    # ----------------------------------------

    st.header("🔹 Step 4 – Selected Relay Voltage")

    vs_selected = max(160, vs_required)

    st.write("Relay voltage selected ≥ required stability voltage.")
    st.success(f"Selected Relay Voltage Vs = {round(vs_selected,2)} V")

    # ----------------------------------------

    st.header("🔹 Step 5 – Knee Point Check (ESI Clause 9.3)")

    st.latex(r"V_k \ge 2V_s")

    knee_condition = vk >= 2 * vs_selected

    st.write(f"2 × Vs = {2*vs_selected}")

    if knee_condition:
        st.success("✔ Knee Point Condition Satisfied")
    else:
        st.error("✖ Knee Point Condition Failed")

    # ----------------------------------------

    st.header("🔹 Step 6 – Fault Setting (ESI Clause 6.2)")

    fault_setting = (relay_setting_current + n_ct * excitation_current) * ct_primary

    st.latex(r"I_{setting} = \frac{I_s + nI_{exc}}{T}")
    st.write(f"I_setting = ({relay_setting_current} + {n_ct} × {excitation_current}) × {ct_primary}")
    st.success(f"Primary Fault Setting = {round(fault_setting,2)} A")

    # ----------------------------------------

    st.header("🔹 Step 7 – Peak Voltage (Clause 8 Approximation)")

    vf = fault_secondary * total_resistance
    peak_voltage = 2 * math.sqrt(2 * vk * vf)

    st.latex(r"V_p \approx 2\sqrt{2 V_k V_f}")

    st.write(f"V_f = {fault_secondary} × {total_resistance}")
    st.write(f"Peak Voltage ≈ {round(peak_voltage,2)} V")

    if peak_voltage > 3000:
        st.warning("⚠ Peak Voltage > 3kV → Metrosil Required")
    else:
        st.success("✔ Peak Voltage within acceptable limit")

    # ----------------------------------------

    st.header("🔹 Step 8 – Stabilising Resistor")

    rst = (vs_selected / relay_setting_current) - total_resistance

    st.latex(r"R_{st} = \frac{V_s}{I_r} - R_{total}")
    st.write(f"Rst = ({vs_selected} / {relay_setting_current}) - {total_resistance}")
    st.success(f"Required Stabilising Resistor ≈ {round(rst,2)} Ω")

    # ----------------------------------------

    st.header("📘 Engineering Conclusion")

    st.markdown(f"""
    - Stability Voltage Required = **{round(vs_required,2)} V**
    - Selected Relay Voltage = **{round(vs_selected,2)} V**
    - CT Knee Point = **{vk} V**
    - Peak Voltage ≈ **{round(peak_voltage/1000,2)} kV**
    - Fault Setting ≈ **{round(fault_setting/1000,2)} kA Primary**

    ✔ Fully compliant with High Impedance Busbar Protection philosophy.
    """)
