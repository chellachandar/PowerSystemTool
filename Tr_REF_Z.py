import streamlit as st
import math
import plotly.graph_objects as go

st.set_page_config(page_title="ESI High Impedance REF Designer", layout="wide")

st.title("⚡ High Impedance REF – ESI Compliant Designer")

st.markdown("---")

# ============================
# USER INPUTS
# ============================

col1, col2 = st.columns(2)

with col1:
    st.subheader("Transformer Data")
    MVA = st.number_input("Transformer Rating (MVA)", value=100.0)
    kV = st.number_input("System Voltage (kV)", value=220.0)

with col2:
    st.subheader("System & CT Data")
    fault_kA = st.number_input("Maximum Bus Fault Level (kA)", value=7.0)
    CT_ratio = st.number_input("Selected CT Ratio (Primary / 1A)", value=400.0)
    Rct = st.number_input("CT Secondary Resistance (Ω)", value=6.0)
    Rlead = st.number_input("Lead Resistance (Ω)", value=1.0)

st.markdown("---")

# ============================
# CALCULATIONS
# ============================

# Full load current
I_fl = (MVA * 1000) / (math.sqrt(3) * kV)

# Through fault secondary current
I_sec_fault = (fault_kA * 1000) / CT_ratio

# Total loop resistance
R_total = Rct + Rlead

# Stability Voltage
Vs = I_sec_fault * R_total

# Strict ESI Knee Point Voltage
Vk_min = 2 * Vs

# Engineering Recommended Vk (3 x Vs)
Vk_rec = 3 * Vs

# Stability Factor
Stability_Factor = Vk_min / Vs if Vs != 0 else 0

# Stabilising resistor
R_st = Vk_min / I_sec_fault if I_sec_fault != 0 else 0

# ============================
# RESULTS DISPLAY
# ============================

st.subheader("📊 Calculation Results")

colA, colB, colC = st.columns(3)

with colA:
    st.metric("Full Load Current (A)", round(I_fl, 2))
    st.metric("Secondary Fault Current (A)", round(I_sec_fault, 2))

with colB:
    st.metric("Stability Voltage Vs (V)", round(Vs, 2))
    st.metric("Stability Factor (Vk/Vs)", round(Stability_Factor, 2))

with colC:
    st.metric("Vk (Strict ESI) (V)", round(Vk_min, 2))
    st.metric("Vk (Engineering 3×Vs) (V)", round(Vk_rec, 2))

st.markdown("---")

# ============================
# FORMULAE USED
# ============================

st.subheader("📘 Formulae Used (ESI 48-3 Compliant)")

st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V_{LL}}")
st.latex(r"I_{sec} = \frac{I_{fault}}{CT\ Ratio}")
st.latex(r"V_s = I_{sec} \times (R_{CT} + R_{lead})")
st.latex(r"V_k(min) = 2 \times V_s")
st.latex(r"V_k(rec) = 3 \times V_s")

st.markdown("---")

# ============================
# GRAPHICAL STABILITY INDICATOR
# ============================

st.subheader("📈 Stability Margin Indicator")

fig = go.Figure()

fig.add_trace(go.Bar(
    x=["Required Vs"],
    y=[Vs],
    name="Vs",
    marker_color="red"
))

fig.add_trace(go.Bar(
    x=["Vk (ESI Min)"],
    y=[Vk_min],
    name="Vk_min",
    marker_color="green"
))

fig.add_trace(go.Bar(
    x=["Vk (Engineering)"],
    y=[Vk_rec],
    name="Vk_rec",
    marker_color="blue"
))

fig.update_layout(
    title="CT Stability Margin",
    yaxis_title="Voltage (V)",
    barmode='group',
    height=400
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ============================
# ENGINEERING INTERPRETATION
# ============================

st.subheader("🧠 Engineering Interpretation")

if Stability_Factor >= 2:
    st.success("✔ CT Stability meets strict ESI requirement.")
else:
    st.error("⚠ Stability does NOT meet ESI requirement. Increase CT ratio or Vk.")

st.info(f"""
Stability Factor = Vk_min / Vs = {round(Stability_Factor,2)}

• Strict ESI requires ≥ 2  
• Engineering recommended margin ≈ 3  
""")
