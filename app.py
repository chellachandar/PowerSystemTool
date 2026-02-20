import streamlit as st
import math

st.set_page_config(page_title="Power System Fault Calculator", layout="centered")

st.title("⚡ Power System Fault Analysis Tool")

st.subheader("Input Parameters")

fault_mva = st.number_input("Fault Level (MVA)", value=10000.0)
voltage_kv = st.number_input("System Voltage (kV)", value=220.0)
xr_ratio = st.number_input("X/R Ratio", value=15.0)

st.subheader("Formulas Used")

st.latex(r"I_{sym} = \frac{Fault\ MVA}{\sqrt{3} \times V_{LL}}")
st.latex(r"Z = \frac{V_{LL}^2}{Fault\ MVA}")
st.latex(r"R = \frac{Z}{\sqrt{1+(X/R)^2}}")
st.latex(r"X = R \times (X/R)")
st.latex(r"I_{peak} = \sqrt{2} \times I_{sym} \times (1 + e^{-\pi/(X/R)})")

if st.button("Calculate"):

    # Convert units properly
    V = voltage_kv * 1000
    S = fault_mva * 10**6

    # Symmetrical fault current (A)
    I_sym = S / (math.sqrt(3) * V)

    # System impedance (Ohms)
    Z = (V**2) / S

    # Resistance and Reactance
    R = Z / math.sqrt(1 + xr_ratio**2)
    X = R * xr_ratio

    # Peak current
    I_peak = math.sqrt(2) * I_sym * (1 + math.exp(-math.pi / xr_ratio))

    st.subheader("Results")

    st.success(f"Symmetrical Fault Current: {I_sym/1000:.2f} kA")
    st.success(f"Peak Fault Current: {I_peak/1000:.2f} kA")

    st.info(f"System Impedance (Z): {Z:.4f} Ohms")
    st.info(f"System Resistance (R): {R:.4f} Ohms")
    st.info(f"System Reactance (X): {X:.4f} Ohms")

    st.subheader("Engineering Impact")

    if xr_ratio > 20:
        st.warning("High X/R ratio → Higher DC offset → Higher breaker making duty.")
    elif xr_ratio > 10:
        st.info("Moderate X/R ratio → Standard transient conditions.")
    else:
        st.success("Low X/R ratio → Faster DC decay → Lower mechanical stress.")
