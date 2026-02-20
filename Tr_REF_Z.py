import streamlit as st
import pandas as pd
from ref_engine import REFDesignOptimizer

st.set_page_config(page_title="Transformer REF Optimizer", layout="wide")

st.title("⚡ Transformer High Impedance REF Design Optimizer")

# ---------------------------
# USER INPUT SECTION
# ---------------------------

st.header("Input Data")

col1, col2 = st.columns(2)

with col1:
    mva = st.number_input("Transformer MVA", value=75.0)
    hv_kv = st.number_input("HV Voltage (kV)", value=132.0)
    stability_factor = st.number_input("Stability Factor (e.g. 16)", value=16.0)

with col2:
    rct = st.number_input("CT Resistance (Ohm)", value=8.0)
    rl = st.number_input("Lead Resistance (Ohm)", value=1.0)
    relay_va = st.number_input("Relay Burden (VA)", value=0.5)
    ir = st.number_input("Relay Pickup Current (A)", value=0.04)

ct_tap_input = st.text_input("CT Ratios (comma separated)", "300,500,800")
existing_vk = st.number_input("Existing CT Knee Point Vk (Optional, 0 if unknown)", value=0.0)

if st.button("Calculate REF Settings"):

    ct_taps = [int(x.strip()) for x in ct_tap_input.split(",")]

    optimizer = REFDesignOptimizer(
        mva=mva,
        hv_kv=hv_kv,
        stability_factor=stability_factor,
        ct_taps=ct_taps,
        rct=rct,
        rl=rl,
        relay_va=relay_va,
        ir=ir,
        existing_vk=existing_vk if existing_vk > 0 else None
    )

    results = optimizer.evaluate()

    df = pd.DataFrame(results)

    st.subheader("CT Comparison Results")

    st.dataframe(df)

    best = results[0]

    st.success(f"Recommended CT Ratio: {best['ct_ratio']}")

    st.markdown("### Selected CT Details")

    st.write(f"Required Vs (Actual): {best['vs_actual']:.2f} V")
    st.write(f"Selected Vs: {best['vs_selected']} V")

    st.write(f"Required Rst (Actual): {best['rst_actual']:.2f} Ω")
    st.write(f"Selected Rst: {best['rst_selected']} Ω")

    st.write(f"Minimum Required Vk: {best['vk_min']:.2f} V")
    st.write(f"Recommended Vk (1.5x): {best['vk_recommended']:.2f} V")

    if existing_vk > 0:
        st.write(f"Peak Voltage: {best['peak_voltage']:.2f} V")
        st.write(f"Metrosil Required: {best['metrosil']}")

    # ---------------------------
    # FORMULA DISPLAY SECTION
    # ---------------------------

    st.header("Formulas Used")

    with st.expander("Full Load Current"):
        st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V}")

    with st.expander("Voltage Setting"):
        st.latex(r"V_s = I_{F(sec)} \times R_{loop}")

    with st.expander("Stabilizing Resistor"):
        st.latex(r"R_{st} = \frac{V_s}{I_r}")

    with st.expander("Minimum Knee Point Voltage"):
        st.latex(r"V_k > 2 \times V_{sa}")

    with st.expander("Peak Voltage"):
        st.latex(r"V_p = 2\sqrt{2V_k(I_fR - V_k)}")
