import streamlit as st
import pandas as pd
import math

# -----------------------------
# ENGINE CLASS (Integrated)
# -----------------------------

STANDARD_VS = [24, 36, 48, 60, 75, 85, 100, 120, 150, 200, 300, 380, 400]
STANDARD_RST = [1500, 2000, 2500, 3000, 4000, 5000, 6000, 7500, 8000, 9500, 10000]

class REFDesignOptimizer:

    def __init__(self, mva, hv_kv, stability_factor,
                 ct_taps, rct, rl, relay_va, ir,
                 existing_vk=None):

        self.mva = mva
        self.hv_kv = hv_kv
        self.stability_factor = stability_factor
        self.ct_taps = ct_taps
        self.rct = rct
        self.rl = rl
        self.relay_va = relay_va
        self.ir = ir
        self.existing_vk = existing_vk

    def calculate_ifl(self):
        return (self.mva * 1000) / (math.sqrt(3) * self.hv_kv)

    def calculate_fault_current(self, ifl):
        return self.stability_factor * ifl

    def relay_resistance(self):
        return self.relay_va / (self.ir ** 2)

    def loop_resistance(self):
        return self.rct + self.rl + self.relay_resistance()

    def evaluate(self):

        ifl = self.calculate_ifl()
        if_primary = self.calculate_fault_current(ifl)

        results = []

        for ct in self.ct_taps:

            if_sec = if_primary / ct
            vs_actual = if_sec * self.loop_resistance()

            vs_selected = next((v for v in STANDARD_VS if v >= vs_actual), STANDARD_VS[-1])
            rst_actual = vs_selected / self.ir
            rst_selected = next((r for r in STANDARD_RST if r >= rst_actual), STANDARD_RST[-1])

            vsa = (self.relay_va / self.ir) + (self.ir * rst_selected)
            vk_min = 2 * vsa
            vk_recommended = 1.5 * vk_min

            results.append({
                "CT Ratio": ct,
                "IF Secondary (A)": round(if_sec, 3),
                "Vs Required (V)": round(vs_actual, 2),
                "Vs Selected (V)": vs_selected,
                "Rst Required (Ohm)": round(rst_actual, 2),
                "Rst Selected (Ohm)": rst_selected,
                "Vk Min (V)": round(vk_min, 2),
                "Vk Recommended (V)": round(vk_recommended, 2)
            })

        return results


# -----------------------------
# STREAMLIT UI
# -----------------------------

st.set_page_config(page_title="Transformer REF Optimizer", layout="wide")
st.title("⚡ Transformer High Impedance REF Design Optimizer")

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

if st.button("Calculate REF Settings"):

    ct_taps = [int(x.strip()) for x in ct_tap_input.split(",")]

    optimizer = REFDesignOptimizer(
        mva, hv_kv, stability_factor,
        ct_taps, rct, rl, relay_va, ir
    )

    results = optimizer.evaluate()

    df = pd.DataFrame(results)

    st.subheader("CT Comparison Results")
    st.dataframe(df)

    best = results[0]
    st.success(f"Recommended CT Ratio: {best['CT Ratio']}")

    st.header("Formulas Used")

    with st.expander("Full Load Current"):
        st.latex(r"I_{FL} = \frac{MVA \times 1000}{\sqrt{3} \times V}")

    with st.expander("Voltage Setting"):
        st.latex(r"V_s = I_{F(sec)} \times R_{loop}")

    with st.expander("Stabilizing Resistor"):
        st.latex(r"R_{st} = \frac{V_s}{I_r}")
