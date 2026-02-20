import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Transformer REF Optimizer", layout="wide")

st.title("⚡ Transformer High Impedance REF Design Optimizer")

# =============================
# INPUT SECTION
# =============================

st.header("Transformer Data")

col1, col2 = st.columns(2)

with col1:
    mva = st.number_input("Transformer MVA", value=100.0)
    hv_kv = st.number_input("HV Voltage (kV)", value=132.0)
    stability_factor = st.number_input("Stability Factor", value=8.0)

with col2:
    rct = st.number_input("CT Resistance (Ohm)", value=6.0)
    rl = st.number_input("Lead Resistance (Ohm)", value=1.0)
    relay_va = st.number_input("Relay Burden (VA)", value=0.2)
    ir = st.number_input("Relay Pickup Current (A)", value=0.1)

ct_input = st.text_input("CT Ratios (comma separated)", "400,600,800")
existing_vk = st.number_input("Existing CT Knee Point Vk (Optional, 0 if unknown)", value=0.0)

# =============================
# CALCULATION SECTION
# =============================

if st.button("Calculate REF Settings"):

    ct_ratios = [int(x.strip()) for x in ct_input.split(",")]

    # Step 1: IFL
    ifl = (mva * 1000) / (math.sqrt(3) * hv_kv)

    # Step 2: Through Fault
    ithrough = stability_factor * ifl

    # Step 3: Relay Resistance
    rrelay = relay_va / (ir ** 2)

    # Step 4: Loop Resistance
    rloop = rct + rl + rrelay

    results = []

    for ct in ct_ratios:

        isec = ithrough / ct

        vs = isec * rloop

        rst = vs / ir

        vsa = (relay_va / ir) + (ir * rst)

        vk_min = 2 * vsa
        vk_rec = 1.5 * vk_min

        stability_margin = None
        verdict = "OK"

        if existing_vk > 0:
            stability_margin = existing_vk / vk_min
            verdict = "PASS" if existing_vk > vk_min else "FAIL"

        results.append({
            "CT Ratio": ct,
            "IFL (A)": round(ifl,2),
            "Through Fault (A)": round(ithrough,2),
            "Secondary Fault (A)": round(isec,3),
            "Vs Required (V)": round(vs,2),
            "Rst Required (Ohm)": round(rst,2),
            "Vk Min Required (V)": round(vk_min,2),
            "Vk Recommended (V)": round(vk_rec,2),
            "Stability Margin": round(stability_margin,2) if stability_margin else "—",
            "Verdict": verdict
        })

    df = pd.DataFrame(results)

    st.subheader("CT Comparison Results")
    st.dataframe(df)

    best = df.iloc[0]
    st.success(f"Recommended CT Ratio: {best['CT Ratio']}")

    # =============================
    # FORMULAS DISPLAY
    # =============================

    st.header("Formulas Used")

    with st.expander("Full Load Current"):
        st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V}")

    with st.expander("Through Fault Current"):
        st.latex(r"I_{through} = Stability\ Factor \times I_{FL}")

    with st.expander("Secondary Fault Current"):
        st.latex(r"I_{sec} = \frac{I_{through}}{CT\ Ratio}")

    with st.expander("Voltage Requirement"):
        st.latex(r"V_s = I_{sec} \times (R_{CT} + R_{lead} + R_{relay})")

    with st.expander("Stabilizing Resistor"):
        st.latex(r"R_{st} = \frac{V_s}{I_r}")

    with st.expander("Minimum Knee Point Voltage"):
        st.latex(r"V_k > 2 \times V_{sa}")

    with st.expander("Recommended Knee Point Voltage"):
        st.latex(r"V_k(recommended) = 1.5 \times V_k(min)")
