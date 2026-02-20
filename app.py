import streamlit as st
import math

st.set_page_config(page_title="Power System Tool", layout="centered")

st.title("⚡ Power System Fault Calculator")

st.subheader("Input Parameters")

fault_mva = st.number_input("Fault Level (MVA)", value=5000.0)
voltage_kv = st.number_input("System Voltage (kV)", value=230.0)
xr_ratio = st.number_input("X/R Ratio", value=20.0)

st.subheader("Formula Used")
st.latex(r"I_{sym} = \frac{Fault\ MVA}{\sqrt{3} \times V_{LL}}")

if st.button("Calculate"):

    I_sym = (fault_mva * 10**6) / (math.sqrt(3) * voltage_kv * 10**3)
    I_peak = math.sqrt(2) * I_sym * (1 + math.exp(-math.pi / xr_ratio))

    st.success(f"Symmetrical Fault Current: {I_sym/1000:.2f} kA")
    st.success(f"Peak Fault Current: {I_peak/1000:.2f} kA")
