import math
import streamlit as st

st.set_page_config(page_title="P&C Field Calculator", page_icon="⚡", layout="centered")

CT_SERIES = [100, 150, 200, 300, 400, 500, 600, 800, 1000, 1200, 1600, 2000, 2500, 3000, 4000, 5000]
RT3 = math.sqrt(3)

DEFAULTS = {
    "txS": 500.0, "txUp": 400.0, "txUs": 220.0, "txZ": 14.0, "txVin": 11.0, "txInj": "lv",
    "ckU": 400.0, "ckA": 600.0, "ckN": 2, "ckD": 0.95,
    "amps": [
        {"name": "Zebra (ACSR 54/7)", "a": 600.0},
        {"name": "Moose (ACSR 54/7)", "a": 680.0},
        {"name": "Bison (ACSR 54/7)", "a": 445.0},
        {"name": "Panther (ACSR 30/7)", "a": 485.0},
    ],
    "fS": 20000.0, "fU": 400.0, "fXR": 14.0, "fSb": 100.0, "fZ01": 1.0,
    "sSf": 5000.0, "sP": 2000.0, "sQ": 600.0,
    "siZs": 8.0, "siZL": 16.0,
    "lcL": 300.0, "lcQkm": 0.58, "lcK": 70.0,
    "vcUm": 425.0, "vcUt": 400.0, "vcS": 10000.0,
    "setF": "50", "setSb": 100.0, "ctMargin": 120,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def fmt(n, dp=1):
    if n is None or isinstance(n, complex) or not math.isfinite(n):
        return "—"
    return f"{n:,.{dp}f}"


def fI(n):
    if n is None or not math.isfinite(n):
        return "—"
    return fmt(n, 0 if abs(n) >= 1000 else 1)


def pos(n):
    return n if (n is not None and n > 0) else float("nan")


def nneg(n):
    return n if (n is not None and n >= 0) else float("nan")


def suggest_ct(i, margin_pct=120):
    if not math.isfinite(i):
        return "—"
    margin = margin_pct / 100
    for r in CT_SERIES:
        if r >= i * margin:
            return f"{r:,.0f} / 1 A"
    return "> 5000 / 1 A"


def classify_scr(v):
    if not math.isfinite(v):
        return ("—", "#5c6d85", "Enter valid inputs to classify system strength.")
    if v > 3:
        return ("STRONG", "#177a4c", "Strong system — conventional converter control and standard protection "
                                      "settings expected to perform normally.")
    if v >= 2:
        return ("WEAK", "#a86e0a", "Weak system — heightened commutation-failure / voltage-stability risk; "
                                    "review control interactions and protection coordination.")
    return ("VERY WEAK", "#bd3b2f", "Very weak system — high instability risk; detailed EMT studies mandatory, "
                                     "consider synchronous condensers or grid reinforcement.")


def classify_sir(v):
    if not math.isfinite(v):
        return ("—", "#5c6d85", "Enter valid impedances.")
    if v > 4:
        return ("HIGH", "#bd3b2f", "Short line — care with Zone-1 transient overreach; consider reduced reach "
                                    "and CVT transient response.")
    if v >= 0.5:
        return ("MEDIUM", "#177a4c", "Typical line — standard distance protection settings generally valid.")
    return ("LOW", "#a86e0a", "Long line — load encroachment and power-swing blocking considerations dominate.")


def badge(label, color):
    st.markdown(
        f"<span style='background:{color};color:#fff;font-size:11px;font-weight:700;"
        f"letter-spacing:0.06em;padding:4px 10px;border-radius:20px'>{label}</span>",
        unsafe_allow_html=True,
    )


def note(text):
    st.markdown(
        f"<div style='background:#eef3fa;border:1px solid #d4dce8;border-radius:10px;"
        f"padding:10px 14px;font-size:13px;color:#132a47;margin-top:4px'>{text}</div>",
        unsafe_allow_html=True,
    )


st.title("⚡ P&C Field Calculator")
st.caption("Indicative results — verify against detailed studies and rated data")

tab_tx, tab_ck, tab_fl, tab_sc, tab_q, tab_set = st.tabs(
    ["Transformer", "Circuit", "Fault", "SCR / SIR", "Reactive", "Settings"]
)

# ---------------------------------------------------------------- Transformer
with tab_tx:
    st.subheader("Inputs")
    c1, c2, c3 = st.columns(3)
    st.session_state.txS = c1.number_input("Rating S (MVA)", value=st.session_state.txS, key="txS_in")
    st.session_state.txUp = c2.number_input("Primary U₁ (kV)", value=st.session_state.txUp, key="txUp_in")
    st.session_state.txUs = c3.number_input("Secondary U₂ (kV)", value=st.session_state.txUs, key="txUs_in")

    S, Up, Us = pos(st.session_state.txS), pos(st.session_state.txUp), pos(st.session_state.txUs)
    Ip = S * 1000 / (RT3 * Up)
    Is = S * 1000 / (RT3 * Us)

    st.subheader("Results")
    r1, r2 = st.columns(2)
    with r1:
        st.metric("Primary current", f"{fI(Ip)} A")
        st.caption("I₁ = S×1000 / (√3 × U₁)")
    with r2:
        st.metric("Secondary current", f"{fI(Is)} A")
        st.caption("I₂ = S×1000 / (√3 × U₂)")
    r3, r4 = st.columns(2)
    with r3:
        st.metric("Suggested CT — HV", suggest_ct(Ip, st.session_state.ctMargin))
        st.caption(f"Nearest standard ratio ≥ {st.session_state.ctMargin}% of full-load current")
    with r4:
        st.metric("Suggested CT — LV", suggest_ct(Is, st.session_state.ctMargin))
        st.caption("Standard series 100…5000 / 1 A")

    st.subheader("Short-circuit test")
    c1, c2 = st.columns(2)
    st.session_state.txZ = c1.number_input("Impedance Z (%)", value=st.session_state.txZ, key="txZ_in")
    st.session_state.txVin = c2.number_input("Injected voltage (kV)", value=st.session_state.txVin, key="txVin_in")

    st.write("Inject on (other side shorted)")
    b1, b2 = st.columns(2)
    if b1.button("LV side", use_container_width=True,
                  type="primary" if st.session_state.txInj == "lv" else "secondary"):
        st.session_state.txInj = "lv"
        st.rerun()
    if b2.button("HV side", use_container_width=True,
                  type="primary" if st.session_state.txInj == "hv" else "secondary"):
        st.session_state.txInj = "hv"
        st.rerun()

    injLV = st.session_state.txInj == "lv"
    tZ, tVin = pos(st.session_state.txZ), pos(st.session_state.txVin)
    tUr, tIr = (Us, Is) if injLV else (Up, Ip)
    tIinj = tIr * tVin / (tZ / 100 * tUr)
    tIoth = tIinj * (Us / Up if injLV else Up / Us)
    tScP, tScS = Ip / (tZ / 100), Is / (tZ / 100)
    injName, othName = ("LV", "HV") if injLV else ("HV", "LV")

    r5, r6 = st.columns(2)
    with r5:
        st.metric(f"Current — {injName} (injected)", f"{fI(tIinj)} A")
        st.caption("I = Irated × Vinj / (Z% × Urated)")
    with r6:
        st.metric(f"Current — {othName} (shorted)", f"{fI(tIoth)} A")
        st.caption("reflected by turns ratio U₁/U₂")
    st.metric("Through-fault at full voltage", f"HV {fI(tScP)} A · LV {fI(tScS)} A")
    st.caption("Isc = Irated / (Z% / 100) — infinite source assumed")

# ---------------------------------------------------------------- Circuit
with tab_ck:
    st.subheader("Inputs")
    c1, c2 = st.columns(2)
    st.session_state.ckU = c1.number_input("Voltage U (kV)", value=st.session_state.ckU, key="ckU_in")
    st.session_state.ckN = c2.number_input("Conductors / phase", value=st.session_state.ckN, step=1, key="ckN_in")
    c3, c4 = st.columns(2)
    st.session_state.ckA = c3.number_input("Ampacity per conductor (A)", value=st.session_state.ckA, key="ckA_in")
    st.session_state.ckD = c4.number_input("Bundle derating factor", value=st.session_state.ckD, key="ckD_in",
                                            format="%.2f")

    cD = st.session_state.ckD
    dnote = "enter 0–1" if not (0 < cD <= 1) else ("no derating applied" if cD == 1 else f"currently −{fmt((1-cD)*100, 0)}%")
    note(f"Derating covers mutual heating between sub-conductors — typically 0.95–1.00 for twin/quad bundles "
         f"({dnote}). Use 1.00 if rated values already account for bundling.")

    cU, cA, cN = pos(st.session_state.ckU), pos(st.session_state.ckA), round(pos(st.session_state.ckN))
    cDr = st.session_state.ckD
    cDv = cDr if 0 < cDr <= 1 else float("nan")
    cI = cA * cN * cDv
    cS = RT3 * cU * cI / 1000

    st.subheader("Results")
    r1, r2 = st.columns(2)
    with r1:
        st.metric("Total phase current", f"{fI(cI)} A")
        st.caption("I = ampacity × n × kd")
    with r2:
        st.metric("Circuit capability", f"{fmt(cS, 0)} MVA")
        st.caption("S = √3 × U × I / 1000")

    st.subheader("ACSR ampacity reference")
    st.caption("⚠️ Indicative — verify against rated values")
    for i, row in enumerate(st.session_state.amps):
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(row["name"])
        new_a = c2.number_input("A", value=row["a"], key=f"amp_{i}", label_visibility="collapsed")
        st.session_state.amps[i]["a"] = new_a
        if c3.button("Use", key=f"use_{i}"):
            st.session_state.ckA = new_a
            st.rerun()

# ---------------------------------------------------------------- Fault
with tab_fl:
    st.subheader("Inputs")
    c1, c2 = st.columns(2)
    st.session_state.fS = c1.number_input("Fault level Sf (MVA)", value=st.session_state.fS, key="fS_in")
    st.session_state.fU = c2.number_input("Voltage U (kV)", value=st.session_state.fU, key="fU_in")
    c3, c4 = st.columns(2)
    st.session_state.fXR = c3.number_input("X/R ratio", value=st.session_state.fXR, key="fXR_in")
    st.session_state.fSb = c4.number_input("Base MVA", value=st.session_state.fSb, key="fSb_in")
    st.session_state.fZ01 = st.number_input("Z₀ / Z₁ ratio", value=st.session_state.fZ01, key="fZ01_in")

    fS, fU, fXR, fSb = pos(st.session_state.fS), pos(st.session_state.fU), pos(st.session_state.fXR), pos(st.session_state.fSb)
    Z = fU * fU / fS
    th = math.atan(fXR)
    If = fS / (RT3 * fU)
    X, R = Z * math.sin(th), Z * math.cos(th)
    Zpu = fSb / fS
    z01 = pos(st.session_state.fZ01)
    I1 = 3 * If / (2 + z01)

    st.subheader("Results")
    r1, r2 = st.columns(2)
    with r1:
        st.metric("Source impedance Zs", f"{fmt(Z, 3)} Ω")
        st.caption("Zs = U² / Sf")
    with r2:
        st.metric("3-ph fault current", f"{fmt(If, 1)} kA")
        st.caption("If = Sf / (√3 × U)")
    st.metric("1-ph (SLG) fault current", f"{fmt(I1, 1)} kA ({fmt(I1/If*100, 0)}% of 3-ph)")
    st.caption("I1ph = 3 × If₃ / (2 + Z₀/Z₁) — bolted, solidly earthed; fault resistance ignored")
    r3, r4, r5 = st.columns(3)
    with r3:
        st.metric("Reactance X", f"{fmt(X, 3)} Ω")
    with r4:
        st.metric("Resistance R", f"{fmt(R, 3)} Ω")
    with r5:
        st.metric("Impedance angle", f"{fmt(th*180/math.pi, 1)}°")
    st.metric("Per-unit impedance", f"{fmt(Zpu, 4)} pu")
    st.caption("Zpu = Sbase / Sf")

# ---------------------------------------------------------------- SCR / SIR
with tab_sc:
    st.subheader("Short-circuit ratio — HVDC")
    c1, c2 = st.columns(2)
    st.session_state.sSf = c1.number_input("Fault level at PCC (MVA)", value=st.session_state.sSf, key="sSf_in")
    st.session_state.sP = c2.number_input("HVDC rating Pdc (MW)", value=st.session_state.sP, key="sP_in")
    st.session_state.sQ = st.number_input("Filter / shunt Q at PCC (Mvar)", value=st.session_state.sQ, key="sQ_in")

    sSf, sP, sQ = pos(st.session_state.sSf), pos(st.session_state.sP), nneg(st.session_state.sQ)
    scr = sSf / sP
    escr = (sSf - sQ) / sP
    scr_label, scr_color, scr_note = classify_scr(scr)
    escr_label, escr_color, _ = classify_scr(escr)

    r1, r2 = st.columns(2)
    with r1:
        st.write("**SCR**")
        badge(scr_label, scr_color)
        st.metric("", fmt(scr, 2), label_visibility="collapsed")
        st.caption("SCR = Sf / Pdc")
    with r2:
        st.write("**ESCR**")
        badge(escr_label, escr_color)
        st.metric("", fmt(escr, 2), label_visibility="collapsed")
        st.caption("ESCR = (Sf − Qc) / Pdc")
    note(scr_note)

    st.subheader("Source-to-line impedance ratio")
    c1, c2 = st.columns(2)
    st.session_state.siZs = c1.number_input("Source Zs (Ω)", value=st.session_state.siZs, key="siZs_in")
    st.session_state.siZL = c2.number_input("Line ZL (Ω)", value=st.session_state.siZL, key="siZL_in")
    Zs, ZL = pos(st.session_state.siZs), pos(st.session_state.siZL)
    sir = Zs / ZL
    sir_label, sir_color, sir_note = classify_sir(sir)
    st.write("**SIR**")
    badge(sir_label, sir_color)
    st.metric("", fmt(sir, 2), label_visibility="collapsed")
    st.caption("SIR = Zs / ZL")
    note(sir_note)

# ---------------------------------------------------------------- Reactive
with tab_q:
    st.subheader("1 · Energisation — shunt reactor sizing")
    c1, c2 = st.columns(2)
    st.session_state.lcL = c1.number_input("Line length (km)", value=st.session_state.lcL, key="lcL_in")
    st.session_state.lcQkm = c2.number_input("Charging (Mvar/km)", value=st.session_state.lcQkm, key="lcQkm_in",
                                              format="%.2f")
    st.session_state.lcK = st.number_input("Compensation degree k (%)", value=st.session_state.lcK, key="lcK_in")

    lcL, lcQkm, lcK = pos(st.session_state.lcL), pos(st.session_state.lcQkm), pos(st.session_state.lcK)
    lcQc = lcL * lcQkm
    lcQr = lcK / 100 * lcQc

    r1, r2 = st.columns(2)
    with r1:
        st.metric("Line charging Qc", f"{fmt(lcQc, 1)} Mvar")
        st.caption("Qc = (Mvar/km) × length")
    with r2:
        split = fmt(lcQr / 2, 1) if math.isfinite(lcQr) else "—"
        st.metric("Reactor rating", f"{fmt(lcQr, 1)} Mvar")
        st.caption(f"Qr = k × Qc · {split} Mvar per end if split")
    note("Line won't charge / trips on energisation → surplus charging Mvar (Ferranti). Typical 400 kV: "
         "≈0.55–0.60 Mvar/km; compensate 60–80%, split between the two ends. Never 100% — risk of resonance.")

    st.subheader("2 · Voltage correction — measured vs target")
    c1, c2 = st.columns(2)
    st.session_state.vcUm = c1.number_input("Measured U (kV)", value=st.session_state.vcUm, key="vcUm_in")
    st.session_state.vcUt = c2.number_input("Target U (kV)", value=st.session_state.vcUt, key="vcUt_in")
    st.session_state.vcS = st.number_input("Fault level at bus Ssc (MVA)", value=st.session_state.vcS, key="vcS_in")

    vcUm, vcUt, vcS = pos(st.session_state.vcUm), pos(st.session_state.vcUt), pos(st.session_state.vcS)
    dU = (vcUm - vcUt) / vcUt
    vcQ = dU * vcS

    if not math.isfinite(vcQ):
        vc_label, vc_color, vc_note = "—", "#5c6d85", "Enter measured/target voltage and bus fault level."
    elif abs(dU) < 0.005:
        vc_label, vc_color, vc_note = "WITHIN BAND", "#177a4c", "Voltage within ±0.5% of target — no plant needed."
    elif vcQ > 0:
        vc_label, vc_color = "INDUCTIVE — REACTOR", "#a86e0a"
        vc_note = f"Overvoltage (e.g. 425 kV): absorb ≈{fmt(abs(vcQ), 0)} Mvar with a shunt reactor to pull the bus down to target."
    else:
        vc_label, vc_color = "CAPACITIVE — CAP BANK / SVC", "#bd3b2f"
        vc_note = f"Undervoltage (e.g. 380 kV): inject ≈{fmt(abs(vcQ), 0)} Mvar capacitive (cap bank / SVC / STATCOM) to raise the bus to target."

    st.write("**Required plant rating**")
    badge(vc_label, vc_color)
    st.metric("", f"{fmt(abs(vcQ), 1)} Mvar ({fmt(dU*100, 1)}% ΔU)", label_visibility="collapsed")
    st.caption("ΔQ ≈ (Um − Ut)/Ut × Ssc")
    note(vc_note)

# ---------------------------------------------------------------- Settings
with tab_set:
    st.subheader("Defaults")
    st.write("Default frequency")
    b1, b2 = st.columns(2)
    if b1.button("50 Hz", use_container_width=True,
                  type="primary" if st.session_state.setF == "50" else "secondary"):
        st.session_state.setF = "50"
        st.rerun()
    if b2.button("60 Hz", use_container_width=True,
                  type="primary" if st.session_state.setF == "60" else "secondary"):
        st.session_state.setF = "60"
        st.rerun()

    new_sb = st.number_input("Default base MVA", value=st.session_state.setSb, key="setSb_in")
    if new_sb != st.session_state.setSb:
        st.session_state.setSb = new_sb
        st.session_state.fSb = new_sb
        st.rerun()

    st.subheader("Appearance")
    st.caption("Use Streamlit's built-in theme switch (menu ⋮ → Settings → Theme) for dark/light mode.")

    note("Runs entirely in your browser session — no accounts, no analytics, no external network calls made "
         "by this app. Inputs reset when the page is refreshed (Streamlit does not persist state across "
         "sessions like the original offline app's localStorage).")

st.divider()
st.caption("Indicative results — verify against detailed studies and rated data.")
