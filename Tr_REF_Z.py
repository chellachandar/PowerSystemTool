import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go

st.set_page_config(page_title="High Impedance REF Designer", layout="wide")

st.title("⚡ High Impedance REF – ESI 48-3 Compliant")

# =====================================================
# INPUT SECTION
# =====================================================

st.header("Transformer & System Data")

col1, col2 = st.columns(2)

with col1:
    MVA = st.number_input("Transformer Rating (MVA)", value=100.0)
    kV = st.number_input("System Voltage (kV)", value=220.0)
    fault_kA = st.number_input("Maximum Bus Fault Level (kA)", value=7.0)

with col2:
    Rct = st.number_input("CT Secondary Resistance (Ω)", value=6.0)
    Rlead = st.number_input("Lead Resistance (Ω)", value=1.0)
    relay_va = st.number_input("Relay Burden (VA)", value=0.2)
    Ir = st.number_input("Relay Pickup Current (A)", value=0.1)

ct_input = st.text_input("Available CT Ratios (comma separated)", "400,600,800")
existing_vk = st.number_input("Existing CT Knee Point Vk (Optional)", value=0.0)

st.markdown("---")

# =====================================================
# CALCULATION ENGINE
# =====================================================

if st.button("Calculate REF Settings"):

    CT_ratios = sorted([int(x.strip()) for x in ct_input.split(",")])

    # 1️⃣ Full Load Current
    I_FL = (MVA * 1000) / (math.sqrt(3) * kV)

    # 2️⃣ Through Fault Current (Assigned Maximum)
    I_fault = fault_kA * 1000

    results = []

    for CT in CT_ratios:

        load_ok = CT >= I_FL

        I_sec_fault = I_fault / CT

        # ESI Stability Voltage (Correct formula)
        Vs = I_sec_fault * (Rct + Rlead)

        # Strict ESI Knee Point
        Vk_min = 2 * Vs

        # Engineering Recommendation
        Vk_eng = 3 * Vs

        # Stabilising resistor (using strict ESI Vk)
        Rst = Vk_min / Ir

        # Stability factor
        Stability_Factor = Vk_min / Vs if Vs != 0 else 0

        # If existing Vk provided
        margin = None
        verdict = "—"

        if existing_vk > 0:
            margin = existing_vk / Vk_min
            verdict = "PASS" if existing_vk >= Vk_min else "FAIL"

        results.append({
            "CT Ratio": CT,
            "Load Adequate": "YES" if load_ok else "NO",
            "Secondary Fault (A)": round(I_sec_fault, 2),
            "Stability Voltage Vs (V)": round(Vs, 2),
            "Vk (Strict ESI) (V)": round(Vk_min, 2),
            "Vk (Engineering) (V)": round(Vk_eng, 2),
            "Stabilising Resistor (Ω)": round(Rst, 2),
            "Stability Factor": round(Stability_Factor, 2),
            "Margin (if Vk entered)": round(margin, 2) if margin else "—",
            "Verdict": verdict
        })

    df = pd.DataFrame(results)

    st.subheader("CT Comparison Results")
    st.dataframe(df)

    # =====================================================
    # AUTO CT SELECTION LOGIC
    # =====================================================

    df_valid = df[df["Load Adequate"] == "YES"]

    if not df_valid.empty:
        # Choose lowest CT that satisfies load
        recommended = df_valid.iloc[0]
        st.success(f"Recommended CT Ratio: {recommended['CT Ratio']}")
    else:
        st.error("⚠ No CT ratio satisfies full load current requirement.")
        recommended = None

    # =====================================================
    # GRAPHICAL STABILITY INDICATOR
    # =====================================================

    if recommended is not None:

        Vs_val = recommended["Stability Voltage Vs (V)"]
        Vk_min_val = recommended["Vk (Strict ESI) (V)"]
        Vk_eng_val = recommended["Vk (Engineering) (V)"]

        st.subheader("📈 Stability Margin Indicator")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=["Vs"],
            y=[Vs_val],
            name="Vs",
            marker_color="red"
        ))

        fig.add_trace(go.Bar(
            x=["Vk (ESI)"],
            y=[Vk_min_val],
            name="Vk_min",
            marker_color="green"
        ))

        fig.add_trace(go.Bar(
            x=["Vk (Engineering)"],
            y=[Vk_eng_val],
            name="Vk_eng",
            marker_color="blue"
        ))

        fig.update_layout(
            title="CT Stability Comparison",
            yaxis_title="Voltage (V)",
            barmode="group",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # =====================================================
    # DISPLAY DERIVED VALUES
    # =====================================================

    st.subheader("Derived System Parameters")

    colA, colB = st.columns(2)

    with colA:
        st.metric("Full Load Current (A)", round(I_FL, 2))
        st.metric("Through Fault Current (A)", round(I_fault, 2))

    with colB:
        st.metric("Bus Fault Level (kA)", fault_kA)

    st.markdown("---")

    # =====================================================
    # FORMULAE DISPLAY
    # =====================================================

    st.subheader("📘 Formulae Used (ESI 48-3 Based)")

    st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V_{LL}}")
    st.latex(r"I_{sec} = \frac{I_{fault}}{CT\ Ratio}")
    st.latex(r"V_s = I_{sec} \times (R_{CT} + R_{lead})")
    st.latex(r"V_k(min) = 2 \times V_s")
    st.latex(r"V_k(eng) = 3 \times V_s")
