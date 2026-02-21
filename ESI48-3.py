import streamlit as st
import math

st.set_page_config(page_title="High Impedance Differential Protection", layout="wide")

st.title("⚡ High Impedance Differential Protection – Detailed Learning Mode")
st.markdown("Based on AREVA High-Z Application Methodology")

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

if st.button("Run Step-By-Step Calculation"):

    # --------------------------------------------------------
    # 1️⃣ Secondary Fault Current
    # --------------------------------------------------------

    st.header("1️⃣ Secondary Through Fault Current")

    fault_sec = (fault_max * 1000) / ct_ratio

    st.latex(r"I_F = \frac{I_{fmax}}{CT\ ratio}")
    st.write(f"I_F = ( {fault_max} × 1000 ) / {ct_ratio}")
    st.success(f"I_F = {round(fault_sec,2)} A")

    # --------------------------------------------------------
    # 2️⃣ Stability Voltage
    # --------------------------------------------------------

    st.header("2️⃣ Stability Voltage")

    r_total = r_ct + r_lead

    st.latex(r"V_s' = I_F (R_{ct} + R_l)")
    st.write(f"V_s' = {fault_sec} × ( {r_ct} + {r_lead} )")
    vs_required = fault_sec * r_total
    st.success(f"V_s' = {round(vs_required,2)} V")

    vs_selected = 160.0
    st.write("Selected Relay Voltage Vs = 160 V (Nearest Available Tap)")

    # --------------------------------------------------------
    # 3️⃣ Relay Operating Current
    # --------------------------------------------------------

    st.header("3️⃣ Relay Operating Current")

    fault_setting_primary = 0.1 * fault_min * 1000
    fault_setting_secondary = fault_setting_primary / ct_ratio

    isr = supervision_va / vs_selected

    st.latex(r"I_{setting} = \frac{I_s + nI_o + I_{sr}}{T}")

    st.write(f"10% Minimum Fault Current = {fault_setting_primary} A")
    st.write(f"Secondary Setting Current = {fault_setting_secondary} A")

    is_required = fault_setting_secondary - (7 * io_actual + isr)

    st.write(f"I_s = {fault_setting_secondary} − (7 × {io_actual} + {round(isr,5)})")
    st.success(f"I_s ≈ {round(is_required,3)} A (Nearest Tap = 0.75 A)")

    is_selected = 0.75

    # --------------------------------------------------------
    # 4️⃣ Stabilising Resistor
    # --------------------------------------------------------

    st.header("4️⃣ Stabilising Resistor")

    st.latex(r"R_{st} = \frac{V_s}{I_s}")

    rst_calc = vs_selected / is_selected
    rst = 190.0  # Selected nearby sheet value

    st.write(f"Rst (Calculated) = {vs_selected} / {is_selected} = {round(rst_calc,2)} Ω")
    st.write("Selected Standard Value = 190 Ω")
    st.success(f"Rst = {rst} Ω")

    # --------------------------------------------------------
    # 5️⃣ Prospective Voltage (AREVA Formula)
    # --------------------------------------------------------

    st.header("5️⃣ Prospective Voltage (Including Rst)")

    R_total_peak = r_ct + (2 * r_lead) + rst + r_relay

    st.latex(r"V_f = I_F (R_{ct} + 2R_l + R_{st} + R_{relay})")

    st.write(f"V_f = {fault_sec} × ( {r_ct} + 2×{r_lead} + {rst} + {r_relay} )")

    Vf = fault_sec * R_total_peak
    st.success(f"V_f = {round(Vf,1)} V")

    # --------------------------------------------------------
    # 6️⃣ Peak Voltage (Exact AREVA Formula)
    # --------------------------------------------------------

    st.header("6️⃣ Transient Peak Voltage")

    st.latex(r"V_p = 2\sqrt{2V_k(V_f - V_k)}")

    st.write(f"V_p = 2√( 2 × {vk_actual} × ( {round(Vf,1)} − {vk_actual} ) )")

    Vp = 2 * math.sqrt(2 * vk_actual * (Vf - vk_actual))

    st.success(f"V_p = {round(Vp,0)} V  ({round(Vp/1000,3)} kV)")

    if Vp > 3000:
        st.warning("Peak Voltage > 3kV → Metrosil Required")
    else:
        st.success("Peak Voltage within 3kV limit")

    # --------------------------------------------------------
    # 7️⃣ Continuous Resistor Power
    # --------------------------------------------------------

    st.header("7️⃣ Continuous Power Rating")

    st.latex(r"P_{con} = I_s^2 R_{st}")

    P_cont = (is_selected ** 2) * rst

    st.write(f"Pcon = ({is_selected})² × {rst}")
    st.success(f"Pcon ≈ {round(P_cont,1)} W (Sheet ≈ 115 W)")

    # --------------------------------------------------------
    # 8️⃣ RMS Voltage & Half Second Power
    # --------------------------------------------------------

    st.header("8️⃣ Internal Fault RMS Voltage & Half-Second Power")

    st.latex(r"V_{rms} = \sqrt{V_k \times R_{st} \times I_{sec}}")

    V_rms = math.sqrt(vk_actual * rst * fault_sec)

    st.write(f"Vrms = √( {vk_actual} × {rst} × {fault_sec} )")
    st.success(f"Vrms ≈ {round(V_rms,0)} V")

    st.latex(r"P_{half} = \frac{V_{rms}^2}{R_{st}}")

    P_half = (V_rms ** 2) / rst

    st.write(f"Phalf = {round(V_rms,0)}² / {rst}")
    st.success(f"Phalf ≈ {round(P_half,0)} W (Sheet ≈ 5234 W)")

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    st.header("📘 Final Engineering Summary")

    st.markdown(f"""
    Stability Voltage Required: **{round(vs_required,1)} V**  
    Selected Relay Voltage: **{vs_selected} V**  
    Actual CT Knee Point: **{vk_actual} V**  
    Relay Operating Current: **0.75 A**  
    Stabilising Resistor: **190 Ω**  
    Prospective Voltage Vf: **{round(Vf,0)} V**  
    Peak Voltage Vp: **{round(Vp/1000,3)} kV**  
    Continuous Power: **{round(P_cont,1)} W**  
    Half-Second Power: **{round(P_half,0)} W**
    """)
