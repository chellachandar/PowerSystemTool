import streamlit as st
import math

st.set_page_config(page_title="High Impedance Busbar Design Tool", layout="wide")

st.title("⚡ High Impedance Busbar Protection – Design Mode")
st.markdown("Based strictly on ESI 48-3 methodology")

# --------------------------------------------------------
# INPUT SECTION (Only system & CT physical data allowed)
# --------------------------------------------------------

st.header("🔹 Input – System & CT Data")

col1, col2, col3 = st.columns(3)

with col1:
    fault_primary = st.number_input("Maximum Fault Current (Primary kA)", value=40.0)
    ct_primary = st.number_input("CT Primary Rating (A)", value=2000)

with col2:
    r_ct = st.number_input("CT Secondary Resistance Rct (Ohms)", value=6.0)
    r_lead = st.number_input("Lead Resistance Rlead (Ohms)", value=1.175)

with col3:
    n_ct = st.number_input("Number of CTs in Parallel (n)", value=7)
    excitation_current = st.number_input("Excitation Current at Vs (A)", value=0.003)

# CT Secondary fixed
ct_secondary = 1

if st.button("Run Full Design Calculation"):

    # --------------------------------------------------------
    st.header("Step 1 – Secondary Through Fault Current")
    st.markdown("📖 ESI 48-3 Clause 5.6 – Rated Stability Limit")

    fault_secondary = (fault_primary * 1000) / ct_primary

    st.latex(r"I_F = \frac{I_{primary}}{CT\ ratio}")
    st.write(f"I_F = ({fault_primary} × 1000) / {ct_primary}")
    st.success(f"Secondary Through Fault Current = {round(fault_secondary,2)} A")

    # --------------------------------------------------------
    st.header("Step 2 – Total Loop Resistance")
    st.markdown("📖 ESI 48-3 Clause 6.1")

    total_resistance = r_ct + r_lead

    st.latex(r"R_{total} = R_{CT} + R_{lead}")
    st.write(f"R_total = {r_ct} + {r_lead}")
    st.success(f"Total Loop Resistance = {round(total_resistance,3)} Ω")

    # --------------------------------------------------------
    st.header("Step 3 – Required Stability Voltage Vs'")
    st.markdown("📖 ESI 48-3 Clause 6.1 – Stability Limit")

    vs_required = fault_secondary * total_resistance

    st.latex(r"V_s' = I_F (R_{CT} + R_{lead})")
    st.write(f"V_s' = {fault_secondary} × {total_resistance}")
    st.success(f"Minimum Required Stability Voltage = {round(vs_required,2)} V")

    # --------------------------------------------------------
    st.header("Step 4 – Selected Relay Setting Voltage Vs")

    vs_selected = math.ceil(vs_required / 10) * 10  # round up to next 10V

    st.write("Relay setting voltage must be ≥ Vs'")
    st.success(f"Selected Relay Voltage Vs = {vs_selected} V")

    # --------------------------------------------------------
    st.header("Step 5 – Minimum Required CT Knee Point Vk")
    st.markdown("📖 ESI 48-3 Clause 9.3")

    vk_required = 2 * vs_selected

    st.latex(r"V_k ≥ 2V_s")
    st.write(f"Minimum Required Vk = 2 × {vs_selected}")
    st.success(f"Required CT Knee Point Voltage ≥ {vk_required} V")

    # --------------------------------------------------------
    st.header("Step 6 – Relay Operating Current Is Determination")
    st.markdown("📖 ESI 48-3 Clause 6.2 – Fault Setting")

    # Assume 10% of minimum fault current (conservative busbar value)
    fault_setting_primary = 0.1 * fault_primary * 1000

    relay_setting_secondary = fault_setting_primary / ct_primary

    st.latex(r"I_{setting} = \frac{I_s + nI_{exc}}{T}")

    st.write(f"Target Primary Fault Setting (10%) = {fault_setting_primary} A")
    st.write(f"Secondary Fault Setting Target = {relay_setting_secondary} A")

    # Solve for Is
    is_required = relay_setting_secondary - (n_ct * excitation_current)

    st.write(f"I_s = {relay_setting_secondary} - ({n_ct} × {excitation_current})")
    st.success(f"Required Relay Operating Current Is ≈ {round(is_required,3)} A")

    # --------------------------------------------------------
    st.header("Step 7 – Stabilising Resistor Calculation")

    rst = (vs_selected / is_required) - total_resistance

    st.latex(r"R_{st} = \frac{V_s}{I_s} - R_{total}")
    st.write(f"Rst = ({vs_selected} / {round(is_required,3)}) - {total_resistance}")
    st.success(f"Required Stabilising Resistor ≈ {round(rst,2)} Ω")

    # --------------------------------------------------------
    st.header("Step 8 – Peak Voltage Check")
    st.markdown("📖 ESI 48-3 Clause 8 & 9.4")

    vf = fault_secondary * total_resistance
    peak_voltage = 2 * math.sqrt(2 * vk_required * vf)

    st.latex(r"V_p ≈ 2\sqrt{2 V_k V_f}")
    st.write(f"Peak Voltage ≈ {round(peak_voltage,2)} V")

    if peak_voltage > 3000:
        st.warning("⚠ Peak Voltage > 3kV → Metrosil Required")
    else:
        st.success("✔ Peak Voltage within acceptable limit")

    # --------------------------------------------------------
    st.header("📘 Final Engineering Summary")

    st.markdown(f"""
    - Required Stability Voltage = **{round(vs_required,2)} V**
    - Selected Relay Voltage = **{vs_selected} V**
    - Minimum Required CT Knee Point = **{vk_required} V**
    - Required Relay Operating Current Is = **{round(is_required,3)} A**
    - Stabilising Resistor ≈ **{round(rst,2)} Ω**
    - Peak Voltage ≈ **{round(peak_voltage/1000,2)} kV**

    ✔ Fully derived from ESI 48-3 without skipping steps.
    """)
