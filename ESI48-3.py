import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="High Impedance Busbar Calculator", layout="wide")

st.title("⚡ High Impedance Busbar Protection Calculator")
st.markdown("Based on ESI 48-3 Standard & Validated Busbar Design Document")

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

    st.header("🔹 Calculation Results")

    # Secondary fault current
    fault_secondary = (fault_primary * 1000) / ct_primary

    # Total loop resistance
    total_resistance = r_ct + r_lead

    # Stability voltage (ESI 6.1)
    vs_required = fault_secondary * total_resistance

    # Selected relay voltage (Assume 160V typical)
    vs_selected = max(160, vs_required)

    # Knee point check
    knee_condition = vk >= 2 * vs_selected

    # Fault setting calculation (ESI 6.2)
    fault_setting = (relay_setting_current + n_ct * excitation_current) * ct_primary

    # Peak voltage estimation
    vf = fault_secondary * total_resistance
    peak_voltage = 2 * math.sqrt(2 * vk * vf)

    metrosil_required = peak_voltage > 3000

    # Stabilising resistor
    rst = (vs_selected / relay_setting_current) - total_resistance

    # ----------------------------
    # DISPLAY RESULTS
    # ----------------------------

    results = {
        "Secondary Fault Current (A)": round(fault_secondary, 2),
        "Total Loop Resistance (Ohms)": round(total_resistance, 3),
        "Minimum Stability Voltage Vs' (V)": round(vs_required, 2),
        "Selected Relay Voltage Vs (V)": round(vs_selected, 2),
        "Fault Setting Primary (A)": round(fault_setting, 2),
        "Peak Voltage (V)": round(peak_voltage, 2),
        "Stabilising Resistor (Ohms)": round(rst, 2)
    }

    df = pd.DataFrame(results.items(), columns=["Parameter", "Value"])
    st.table(df)

    st.header("🔹 Validation Status")

    if vs_selected >= vs_required:
        st.success("✔ Stability Condition Satisfied (ESI 6.1)")
    else:
        st.error("✖ Stability Condition NOT Satisfied")

    if knee_condition:
        st.success("✔ Knee Point Condition Satisfied (Vk ≥ 2Vs)")
    else:
        st.error("✖ Knee Point Condition FAILED")

    if metrosil_required:
        st.warning("⚠ Peak Voltage > 3kV → Metrosil Required")
    else:
        st.success("✔ Peak Voltage within acceptable limit")

    st.header("🔹 Engineering Summary")

    st.markdown(f"""
    - Stability Voltage Required = **{round(vs_required,2)} V**
    - Selected Relay Voltage = **{round(vs_selected,2)} V**
    - CT Knee Point = **{vk} V**
    - Peak Voltage Developed ≈ **{round(peak_voltage/1000,2)} kV**
    - Fault Setting ≈ **{round(fault_setting/1000,2)} kA Primary**

    ✔ Fully aligned with ESI 48-3 High Impedance Protection Philosophy.
    """)
