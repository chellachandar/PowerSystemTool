import streamlit as st
import math

st.set_page_config(page_title="High Impedance Differential – Learning Mode", layout="wide")

st.title("⚡ High Impedance Differential Protection – Learning Mode")

st.markdown("""
This tool demonstrates:

• Theoretical calculated values  
• Practical engineering selections  
• Recalculated final design values  
• Thermal and transient checks  

⚠ Designed for learning purposes.  
Final design must always be verified with the selected relay manufacturer's application manual.
""")

# ------------------------------------------------------------
# INPUT DATA
# ------------------------------------------------------------

st.header("🔹 Input Data")

col1, col2, col3 = st.columns(3)

with col1:
    fault_max = st.number_input("Maximum Fault Current (kA)", value=40.0)
    fault_min = st.number_input("Minimum Fault Current (kA)", value=18.9)
    ct_ratio = st.number_input("CT Ratio (Primary / 1A)", value=2000)

with col2:
    r_ct = st.number_input("CT Secondary Resistance Rct (Ω)", value=6.0)
    r_lead = st.number_input("Lead Resistance Rl (Ω)", value=1.175)
    r_relay = st.number_input("Relay Internal Resistance (Ω)", value=1.0)

with col3:
    vk_actual = st.number_input("Actual CT Knee Point Vk (V)", value=450.0)
    io_actual = st.number_input("CT Excitation Current Io at Vs (A)", value=0.003)
    supervision_va = st.number_input("Supervision Relay Burden (VA)", value=0.32)

# ------------------------------------------------------------
# CALCULATION
# ------------------------------------------------------------

if st.button("Run Step-by-Step Design"):

    # --------------------------------------------------------
    # 1️⃣ Secondary Fault Current
    # --------------------------------------------------------

    st.header("1️⃣ Secondary Through Fault Current")

    fault_sec = (fault_max * 1000) / ct_ratio

    st.latex(r"I_F = \frac{I_{fmax}}{CT\ ratio}")
    st.write(f"I_F = ({fault_max} × 1000) / {ct_ratio}")
    st.success(f"I_F = {round(fault_sec,2)} A")

    # --------------------------------------------------------
    # 2️⃣ Stability Voltage
    # --------------------------------------------------------

    st.header("2️⃣ Stability Voltage")

    r_total = r_ct + r_lead

    st.latex(r"V_s' = I_F (R_{ct} + R_l)")
    st.write(f"V_s' = {fault_sec} × ({r_ct} + {r_lead})")

    vs_required = fault_sec * r_total
    st.success(f"Required Stability Voltage Vs' = {round(vs_required,2)} V")

    vs_selected = math.ceil(vs_required / 10) * 10
    st.info(f"Selected Relay Voltage Vs = {vs_selected} V")

    # --------------------------------------------------------
    # 3️⃣ Relay Operating Current
    # --------------------------------------------------------

    st.header("3️⃣ Relay Operating Current")

    fault_setting_primary = 0.1 * fault_min * 1000
    fault_setting_secondary = fault_setting_primary / ct_ratio

    isr = supervision_va / vs_selected

    st.latex(r"I_s = I_{setting} - (nI_o + I_{sr})")

    is_calc = fault_setting_secondary - (7 * io_actual + isr)

    st.write(f"I_s = {fault_setting_secondary} − (7×{io_actual} + {round(isr,5)})")
    st.success(f"Calculated Relay Operating Current = {round(is_calc,4)} A")

    available_taps = [0.5, 0.75, 1.0, 1.25, 1.5]
    is_selected = min(available_taps, key=lambda x: abs(x - is_calc))

    st.info(f"Selected Practical Relay Tap = {is_selected} A")

    # --------------------------------------------------------
    # 4️⃣ Stabilising Resistor
    # --------------------------------------------------------

    st.header("4️⃣ Stabilising Resistor")

    st.latex(r"R_{st(calc)} = \frac{V_s}{I_s}")

    rst_calc = vs_selected / is_selected

    st.write(f"Rst(calc) = {vs_selected} / {is_selected}")
    st.success(f"Calculated Rst = {round(rst_calc,2)} Ω")

    standard_resistors = [150, 180, 190, 200, 220, 270]
    rst_selected = min(standard_resistors, key=lambda x: abs(x - rst_calc))

    st.info(f"Selected Standard Resistor = {rst_selected} Ω")

    # --------------------------------------------------------
    # 5️⃣ Prospective Voltage
    # --------------------------------------------------------

    st.header("5️⃣ Prospective Voltage")

    R_total_peak = r_ct + (2 * r_lead) + rst_selected + r_relay

    st.latex(r"V_f = I_F (R_{ct} + 2R_l + R_{st} + R_{relay})")

    st.write(f"V_f = {fault_sec} × ({r_ct} + 2×{r_lead} + {rst_selected} + {r_relay})")

    Vf = fault_sec * R_total_peak

    st.success(f"Prospective Voltage Vf = {round(Vf,1)} V")

    # --------------------------------------------------------
    # 6️⃣ Peak Voltage
    # --------------------------------------------------------

    st.header("6️⃣ Transient Peak Voltage")

    st.latex(r"V_p = 2\sqrt{2V_k(V_f - V_k)}")

    Vp = 2 * math.sqrt(2 * vk_actual * (Vf - vk_actual))

    st.write(f"V_p = 2√(2 × {vk_actual} × ({round(Vf,1)} − {vk_actual}))")
    st.success(f"Peak Voltage = {round(Vp,0)} V  ({round(Vp/1000,3)} kV)")

    # --------------------------------------------------------
    # 7️⃣ RMS Voltage & Short-Time Power (Worksheet Method)
    # --------------------------------------------------------

    st.header("7️⃣ RMS Voltage & Short-Time Power (Worksheet Method)")

    st.markdown("""
    RMS voltage is calculated using the theoretical (calculated) resistor value.
    This follows the classical high-impedance worksheet method.
    """)

    st.latex(r"V_{rms} = \sqrt{V_k \times R_{calc} \times I_{sec}}")

    V_rms = math.sqrt(vk_actual * rst_calc * fault_sec)

    st.write(f"V_rms = √({vk_actual} × {round(rst_calc,1)} × {fault_sec})")
    st.success(f"RMS Voltage = {round(V_rms,0)} V")

    st.latex(r"P_{1s} = \frac{V_{rms}^2}{R_{selected}}")

    P_half = (V_rms ** 2) / rst_selected

    st.write(f"P1s = {round(V_rms,0)}² / {rst_selected}")
    st.success(f"Short-Time Power ≈ {round(P_half,0)} W")

    # --------------------------------------------------------
    # 8️⃣ Continuous Power
    # --------------------------------------------------------

    st.header("8️⃣ Continuous Power Rating")

    st.latex(r"P_{cont} = I_s^2 R_{selected}")

    P_cont = (is_selected ** 2) * rst_selected

    st.write(f"Pcont = ({is_selected})² × {rst_selected}")
    st.success(f"Continuous Power ≈ {round(P_cont,1)} W")

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    st.header("📘 Final Learning Summary")

    st.markdown(f"""
    Required Stability Voltage: **{round(vs_required,1)} V**  
    Selected Relay Voltage: **{vs_selected} V**  
    Calculated Relay Current: **{round(is_calc,3)} A**  
    Selected Relay Tap: **{is_selected} A**  
    Calculated Resistor: **{round(rst_calc,1)} Ω**  
    Selected Resistor: **{rst_selected} Ω**  
    Prospective Voltage Vf: **{round(Vf,0)} V**  
    Peak Voltage: **{round(Vp/1000,3)} kV**  
    RMS Voltage (Worksheet Method): **{round(V_rms,0)} V**  
    Short-Time Power: **{round(P_half,0)} W**
    """)

    st.warning("""
    ⚠ LIMITATIONS FOR LEARNERS:

    • Worksheet method mixes calculated and selected values.
    • Practical relay manuals may use slightly different transient factors.
    • Thermal rating depends on manufacturer time-current curves.
    • Always verify final settings using the selected relay manufacturer's application guide.
    • This tool demonstrates methodology — not a substitute for protection approval.
    """)
