import streamlit as st

st.set_page_config(page_title="Tertiary Reactor Voltage Impact Calculator", layout="wide")

st.title("🔷 Tertiary Reactor – Mathematical Impact on Voltage Regulation")

st.markdown("This tool calculates the impact of a tertiary reactor on HV bus voltage.")

# -----------------------------
# INPUT SECTION
# -----------------------------

st.sidebar.header("Input Parameters")

V_HV = st.sidebar.number_input("HV Voltage (kV)", value=400.0)
V_T = st.sidebar.number_input("Tertiary Voltage (kV)", value=33.0)
Q_reactor = st.sidebar.number_input("Reactor Rating (MVAr)", value=50.0)
Q_line = st.sidebar.number_input("Line Charging MVAr (MVAr)", value=50.0)
S_sc = st.sidebar.number_input("Grid Short Circuit Level at HV (MVA)", value=10000.0)
base_MVA = st.sidebar.number_input("Base MVA for PU Calculation", value=100.0)

st.header("📌 Step-by-Step Calculation")

# -----------------------------
# STEP 1 – Reactor Reactance
# -----------------------------

st.subheader("1️⃣ Reactor Reactance at Tertiary (Ohms)")

X_R = (V_T**2) / Q_reactor

st.latex(r"X_R = \frac{V_T^2}{Q_R}")
st.write(f"Substitution:")
st.latex(rf"X_R = \frac{{({V_T})^2}}{{{Q_reactor}}}")
st.latex(rf"X_R = {X_R:.3f} \ \Omega")

# -----------------------------
# STEP 2 – Refer to HV Side
# -----------------------------

st.subheader("2️⃣ Reflect Reactance to HV Side")

k = V_T / V_HV
X_R_HV = X_R / (k**2)

st.latex(r"k = \frac{V_T}{V_HV}")
st.latex(rf"k = \frac{{{V_T}}}{{{V_HV}}} = {k:.5f}")

st.latex(r"X_{R,HV} = \frac{X_R}{k^2}")
st.latex(rf"X_{{R,HV}} = \frac{{{X_R:.3f}}}{{({k:.5f})^2}}")
st.latex(rf"X_{{R,HV}} = {X_R_HV:.3f} \ \Omega")

# -----------------------------
# STEP 3 – Equivalent MVAr Check
# -----------------------------

st.subheader("3️⃣ Equivalent Reactive Power Seen at HV")

Q_HV = (V_HV**2) / X_R_HV

st.latex(r"Q_{HV} = \frac{V_{HV}^2}{X_{R,HV}}")
st.latex(rf"Q_{{HV}} = \frac{{({V_HV})^2}}{{{X_R_HV:.3f}}}")
st.latex(rf"Q_{{HV}} = {Q_HV:.2f} \ MVAr")

# -----------------------------
# STEP 4 – System Thevenin Reactance
# -----------------------------

st.subheader("4️⃣ Grid Thevenin Reactance")

X_sys = (V_HV**2) / S_sc

st.latex(r"X_{sys} = \frac{V_{HV}^2}{S_{sc}}")
st.latex(rf"X_{{sys}} = \frac{{({V_HV})^2}}{{{S_sc}}}")
st.latex(rf"X_{{sys}} = {X_sys:.3f} \ \Omega")

# -----------------------------
# STEP 5 – Voltage Rise Without Reactor
# -----------------------------

st.subheader("5️⃣ Voltage Rise WITHOUT Reactor")

deltaV_no = (Q_line * X_sys) / V_HV

st.latex(r"\Delta V_0 = \frac{Q_{line} \cdot X_{sys}}{V_{HV}}")
st.latex(rf"\Delta V_0 = \frac{{{Q_line} \cdot {X_sys:.3f}}}{{{V_HV}}}")
st.latex(rf"\Delta V_0 = {deltaV_no:.3f} \ kV")

# -----------------------------
# STEP 6 – Voltage Rise WITH Reactor
# -----------------------------

st.subheader("6️⃣ Voltage Rise WITH Reactor")

Q_net = Q_line - Q_reactor
deltaV_with = (Q_net * X_sys) / V_HV

st.latex(r"Q_{net} = Q_{line} - Q_R")
st.latex(rf"Q_{{net}} = {Q_line} - {Q_reactor} = {Q_net} \ MVAr")

st.latex(r"\Delta V = \frac{Q_{net} \cdot X_{sys}}{V_{HV}}")
st.latex(rf"\Delta V = \frac{{{Q_net} \cdot {X_sys:.3f}}}{{{V_HV}}}")
st.latex(rf"\Delta V = {deltaV_with:.3f} \ kV")

# -----------------------------
# STEP 7 – Per Unit Calculation
# -----------------------------

st.subheader("7️⃣ Per Unit Representation")

Z_base = (V_HV**2) / base_MVA
X_pu = X_R_HV / Z_base

st.latex(r"Z_{base} = \frac{V_{HV}^2}{Base\ MVA}")
st.latex(rf"Z_{{base}} = \frac{{({V_HV})^2}}{{{base_MVA}}}")
st.latex(rf"Z_{{base}} = {Z_base:.3f} \ \Omega")

st.latex(r"X_{pu} = \frac{X_{R,HV}}{Z_{base}}")
st.latex(rf"X_{{pu}} = \frac{{{X_R_HV:.3f}}}{{{Z_base:.3f}}}")
st.latex(rf"X_{{pu}} = {X_pu:.3f} \ pu")

# -----------------------------
# FINAL ENGINEERING SUMMARY
# -----------------------------

st.header("🔷 Engineering Interpretation")

st.write(f"""
• Voltage rise without reactor: **{deltaV_no:.3f} kV**

• Voltage rise with reactor: **{deltaV_with:.3f} kV**

• Voltage reduction achieved: **{(deltaV_no - deltaV_with):.3f} kV**

• Reactor effectively absorbs: **{Q_reactor:.2f} MVAr**

• Per Unit Reactance: **{X_pu:.3f} pu**
""")

if Q_net == 0:
    st.success("✔ Ferranti effect completely neutralized.")
elif Q_net < 0:
    st.warning("⚠ Over-compensation: Reactor exceeds line charging.")
else:
    st.info("ℹ Partial compensation achieved.")
