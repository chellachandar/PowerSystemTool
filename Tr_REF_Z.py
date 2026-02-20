import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="ESI REF Optimizer - Professional", layout="wide")

st.title("⚡ ESI 48-3 Compliant High Impedance REF Optimizer")

# =====================================================
# INPUT SECTION
# =====================================================

st.header("Transformer & System Data")

col1, col2 = st.columns(2)

with col1:
    mva = st.number_input("Transformer MVA", value=100.0)
    hv_kv = st.number_input("HV Voltage (kV)", value=220.0)
    bus_fault_ka = st.number_input("System Bus Fault Level (kA)", value=7.0)

with col2:
    rct = st.number_input("CT Secondary Resistance (Ω)", value=6.0)
    rlead = st.number_input("Lead Resistance (Ω)", value=1.0)
    ir = st.number_input("Relay Pickup Current (A)", value=0.1)
    existing_vk = st.number_input("Existing CT Knee Point Vk (Optional)", value=0.0)

ct_input = st.text_input("Available CT Ratios (comma separated)", "400,600,800")

# =====================================================
# CALCULATION SECTION
# =====================================================

if st.button("Calculate REF Settings"):

    ct_ratios = sorted([int(x.strip()) for x in ct_input.split(",")])

    # 1️⃣ Full Load Current
    ifl = (mva * 1000) / (math.sqrt(3) * hv_kv)

    # 2️⃣ Through Fault Current
    ifault = bus_fault_ka * 1000

    # HI-REF practical warning
    if bus_fault_ka > 25:
        st.warning("⚠ Fault level very high. High Impedance REF may become impractical. Consider Low Impedance REF.")

    results = []

    for ct in ct_ratios:

        load_ok = ct >= ifl

        isec_fault = ifault / ct

        # Stability Voltage (ESI)
        vs = isec_fault * (rct + rlead)

        # Strict ESI Knee Point
        vk_min = 2 * vs

        # Engineering Recommended
        vk_eng = 3 * vs

        # Correct Stabilising Resistor (Conservative)
        rst = vk_min / ir

        # Resistor Power Rating (worst case at Vk)
        resistor_power = (vk_min ** 2) / rst if rst != 0 else 0

        # Peak Voltage (Worst Case External Fault)
        # Vp ≈ 2√2 × Vk
        peak_voltage = 2 * math.sqrt(2) * vk_min

        metrosil_required = peak_voltage > 3000

        # Stability factor
        stability_factor = vk_min / vs if vs != 0 else 0

        # Existing Vk validation
        margin = None
        verdict = "—"

        if existing_vk > 0:
            margin = existing_vk / vk_min
            verdict = "PASS" if existing_vk >= vk_min else "FAIL"

        results.append({
            "CT Ratio": ct,
            "Load Adequate": "YES" if load_ok else "NO",
            "Secondary Fault (A)": round(isec_fault, 2),
            "Stability Voltage Vs (V)": round(vs, 2),
            "Vk (Strict ESI) (V)": round(vk_min, 2),
            "Vk (Engineering) (V)": round(vk_eng, 2),
            "Stabilising Resistor (Ω)": round(rst, 2),
            "Resistor Power (W)": round(resistor_power, 2),
            "Peak Voltage (V)": round(peak_voltage, 2),
            "Metrosil Required": "YES" if metrosil_required else "NO",
            "CT Class Requirement": f"PX, Vk ≥ {round(vk_eng,0)} V",
            "Stability Factor": round(stability_factor, 2),
            "Margin (if Vk entered)": round(margin, 2) if margin else "—",
            "Verdict": verdict
        })

    df = pd.DataFrame(results)

    st.subheader("CT Comparison Results")
    st.dataframe(df)

    # =====================================================
    # CT AUTO SELECTION LOGIC
    # =====================================================

    df_valid = df[
        (df["Load Adequate"] == "YES") &
        ((df["Verdict"] != "FAIL") if existing_vk > 0 else True)
    ]

    if not df_valid.empty:
        recommended_ct = df_valid.iloc[0]
        st.success(f"Recommended CT Ratio: {recommended_ct['CT Ratio']}")
    else:
        st.error("⚠ No CT satisfies load or Vk requirements.")

    # =====================================================
    # DERIVED SYSTEM VALUES
    # =====================================================

    st.subheader("Derived System Parameters")

    colA, colB = st.columns(2)

    with colA:
        st.metric("Full Load Current (A)", round(ifl, 2))
        st.metric("Through Fault Current (A)", round(ifault, 2))

    with colB:
        st.metric("Bus Fault Level (kA)", bus_fault_ka)

    st.markdown("---")

    # =====================================================
    # FORMULAE DISPLAY
    # =====================================================

    st.subheader("📘 Formulae Used (ESI 48-3 Basis)")

    st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V}")
    st.latex(r"I_{sec} = \frac{I_{fault}}{CT}")
    st.latex(r"V_s = I_{sec} (R_{CT} + R_{lead})")
    st.latex(r"V_k(min) = 2 V_s")
    st.latex(r"V_k(eng) = 3 V_s")
    st.latex(r"R_{st} = \frac{V_k(min)}{I_r}")
    st.latex(r"P_{resistor} = \frac{V_k(min)^2}{R_{st}}")
    st.latex(r"V_{peak} \approx 2\sqrt{2} V_k")
