import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="ESI REF Optimizer", layout="wide")

st.title("⚡ ESI 48-3 Compliant High Impedance REF Optimizer")

# =====================================================
# INPUT SECTION
# =====================================================

st.header("Transformer & System Data")

col1, col2 = st.columns(2)

with col1:
    mva = st.number_input("Transformer MVA", value=100.0)
    hv_kv = st.number_input("HV Voltage (kV)", value=132.0)
    bus_fault_ka = st.number_input("System Bus Fault Level (kA)", value=8.0)

with col2:
    rct = st.number_input("CT Secondary Resistance (Ohm)", value=6.0)
    rlead = st.number_input("Lead Resistance (Ohm)", value=1.0)
    relay_va = st.number_input("Relay Burden (VA)", value=0.2)
    ir = st.number_input("Relay Pickup Current (A)", value=0.1)

ct_input = st.text_input("CT Ratios (comma separated)", "400,600,800")
existing_vk = st.number_input("Existing CT Knee Point Vk (Optional)", value=0.0)

# =====================================================
# CALCULATION SECTION
# =====================================================

if st.button("Calculate REF Settings"):

    ct_ratios = [int(x.strip()) for x in ct_input.split(",")]

    # 1️⃣ Full Load Current
    ifl = (mva * 1000) / (math.sqrt(3) * hv_kv)

    # 2️⃣ Through Fault Current
    ifault = bus_fault_ka * 1000

    results = []

    for ct in ct_ratios:

        # Load adequacy check
        load_ok = ct >= ifl

        # Secondary through fault
        isec = ifault / ct

        # ESI Stability Voltage (CORRECT)
        vs = isec * (rct + rlead)

        # Stabilising resistor
        rst = vs / ir

        # Minimum Vk
        vk_min = 2 * vs

        # Recommended Vk
        vk_rec = 1.5 * vk_min

        stability_margin = None
        verdict = "—"

        if existing_vk > 0:
            stability_margin = existing_vk / vk_min
            verdict = "PASS" if existing_vk >= vk_min else "FAIL"

        results.append({
            "CT Ratio": ct,
            "Load Adequate": "YES" if load_ok else "NO",
            "Full Load Current (A)": round(ifl,2),
            "Through Fault (A)": round(ifault,2),
            "Secondary Fault (A)": round(isec,3),
            "Stability Voltage Vs (V)": round(vs,2),
            "Stabilising Resistor Rst (Ω)": round(rst,2),
            "Vk Minimum (V)": round(vk_min,2),
            "Vk Recommended (V)": round(vk_rec,2),
            "Stability Margin": round(stability_margin,2) if stability_margin else "—",
            "Verdict": verdict
        })

    df = pd.DataFrame(results)

    st.subheader("CT Comparison Results")
    st.dataframe(df)

    # Filter valid CTs
    df_valid = df[df["Load Adequate"] == "YES"]

    if not df_valid.empty:
        recommended_ct = df_valid.iloc[0]["CT Ratio"]
        st.success(f"Recommended CT Ratio (Load Adequate): {recommended_ct}")
    else:
        st.error("⚠ No CT ratio satisfies full load current requirement.")

    # =====================================================
    # FORMULAS SECTION
    # =====================================================

    st.header("Formulas Used (ESI 48-3 Basis)")

    with st.expander("Full Load Current"):
        st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V}")

    with st.expander("Through Fault Current"):
        st.latex(r"I_f = Fault\ Level\ (kA) \times 1000")

    with st.expander("Secondary Fault Current"):
        st.latex(r"I_{sec} = \frac{I_f}{CT\ Ratio}")

    with st.expander("Stability Voltage (ESI Correct)"):
        st.latex(r"V_s = I_{sec} \times (R_{CT} + R_{lead})")

    with st.expander("Stabilising Resistor"):
        st.latex(r"R_{st} = \frac{V_s}{I_r}")

    with st.expander("Minimum Knee Point Voltage"):
        st.latex(r"V_k \ge 2 \times V_s")

    with st.expander("Recommended Knee Point"):
        st.latex(r"V_k(recommended) = 1.5 \times V_k(min)")
