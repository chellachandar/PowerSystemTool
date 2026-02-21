# -------------------------------
# Prospective Voltage Vf
# -------------------------------

st.header("Prospective Voltage (Including Rst)")

R_total_peak = r_ct + (2 * r_lead) + rst + 1  # 1 ohm relay resistance

Vf = fault_sec * R_total_peak

st.latex(r"V_f = I_F (R_{ct} + 2R_l + R_{st} + R_{relay})")
st.write(f"Vf = {fault_sec} × {round(R_total_peak,2)}")
st.success(f"Prospective Voltage Vf = {round(Vf,2)} V")

# -------------------------------
# Transient Peak Voltage
# -------------------------------

st.header("Transient Peak Voltage (Exact Formula)")

Vp = 2 * math.sqrt(2 * vk_actual * (Vf - vk_actual))

st.latex(r"V_p = 2\sqrt{2V_k(V_f - V_k)}")
st.success(f"Peak Voltage = {round(Vp,2)} V")

if Vp > 3000:
    st.warning("Peak Voltage > 3kV → Metrosil Required")
else:
    st.success("Peak Voltage within 3kV limit")

# -------------------------------
# Resistor Continuous Power
# -------------------------------

st.header("Stabilising Resistor Power Check")

P_cont = (is_required ** 2) * rst

st.latex(r"P_{cont} = I_s^2 R_{st}")
st.success(f"Continuous Power ≈ {round(P_cont,2)} W")

# -------------------------------
# Resistor 1-Second Rating
# -------------------------------

P_1s = (fault_sec ** 2) * rst

st.latex(r"P_{1s} = I_{sec}^2 R_{st}")
st.success(f"1-Second Power ≈ {round(P_1s,2)} W")
