import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import comtrade as ct
import re

st.set_page_config(page_title="COMTRADE Analyzer", layout="wide")
st.title("⚡ COMTRADE Fault Record Analyzer")

cfg_file = st.file_uploader("Upload CFG file", type=["cfg"])
dat_file = st.file_uploader("Upload DAT file", type=["dat"])

if cfg_file and dat_file:

    with open("temp.cfg", "wb") as f:
        f.write(cfg_file.read())

    with open("temp.dat", "wb") as f:
        f.write(dat_file.read())

    rec = ct.Comtrade()
    rec.load("temp.cfg", "temp.dat")

    time = np.array(rec.time)

    # --------------------------------------------------
    # PROPER METADATA EXTRACTION
    # --------------------------------------------------

    substation = getattr(rec, "station_name", "Not Available")
    recorder = getattr(rec, "rec_dev_id", "Not Available")

    st.markdown("### 📋 Record Information")
    st.write(f"**Substation:** {substation}")
    st.write(f"**Recorder ID:** {recorder}")
    st.write(f"**System Frequency:** {getattr(rec, 'frequency', 'NA')} Hz")

    analog_names = rec.analog_channel_ids
    analog_data = np.array(rec.analog)

    if analog_data.shape[0] != len(analog_names):
        analog_data = analog_data.T

    # --------------------------------------------------
    # SELECT PHASE VOLTAGES & CURRENTS
    # --------------------------------------------------

    voltage_channels = [n for n in analog_names if re.search(r'V[A-CN]|U[A-CN]', n.upper())][:4]
    current_channels = [n for n in analog_names if re.search(r'I[A-CN]', n.upper())][:4]

    # --------------------------------------------------
    # FAULT DETECTION USING RMS DEVIATION
    # --------------------------------------------------

    fault_start = None
    fault_end = None

    if current_channels:

        idx_list = [analog_names.index(n) for n in current_channels]
        current_matrix = analog_data[idx_list]

        # Sliding RMS window
        window = int(0.02 / (time[1] - time[0]))  # 20ms window

        rms_values = []
        for i in range(len(time) - window):
            segment = current_matrix[:, i:i+window]
            rms = np.sqrt(np.mean(segment**2))
            rms_values.append(rms)

        rms_values = np.array(rms_values)

        baseline = np.mean(rms_values[:window])
        threshold = baseline * 1.5

        active = np.where(rms_values > threshold)[0]

        if len(active) > 0:
            fault_start = time[active[0]]
            fault_end = time[active[-1]]
            fault_duration = fault_end - fault_start

            st.success(f"🔴 Fault Start: {fault_start:.6f} s")
            st.success(f"🔵 Fault End: {fault_end:.6f} s")
            st.success(f"⏱ Fault Duration: {fault_duration:.6f} s")

    # --------------------------------------------------
    # ANALOG PLOT
    # --------------------------------------------------

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Voltages", "Currents")
    )

    # Voltages
    for name in voltage_channels:
        idx = analog_names.index(name)
        fig.add_trace(
            go.Scatter(x=time, y=analog_data[idx], name=name),
            row=1, col=1
        )

    # Currents
    for name in current_channels:
        idx = analog_names.index(name)
        fig.add_trace(
            go.Scatter(x=time, y=analog_data[idx], name=name),
            row=2, col=1
        )

    # Mark fault window
    if fault_start and fault_end:
        fig.add_vrect(
            x0=fault_start,
            x1=fault_end,
            fillcolor="red",
            opacity=0.15,
            line_width=0
        )

    fig.update_layout(
        height=750,
        legend=dict(
            orientation="v",
            x=1.02,
            y=1
        )
    )

    fig.update_xaxes(title_text="Time (s)", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------
    # DIGITAL CHANNELS (CHANGED ONLY)
    # --------------------------------------------------

    status_raw = rec.status
    status_names = rec.status_channel_ids

    if status_raw and len(status_raw) > 0:

        status_array = np.array(status_raw)

        if status_array.shape[0] != len(status_names):
            status_array = status_array.T

        changed = []

        for i, name in enumerate(status_names):
            sig = status_array[i]
            if np.max(sig) != np.min(sig):
                changed.append((name, sig))

        if changed:

            st.subheader("Digital Signals (Changed Only)")

            fig_d = make_subplots(
                rows=len(changed),
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.01
            )

            for i, (name, sig) in enumerate(changed):
                fig_d.add_trace(
                    go.Scatter(
                        x=time,
                        y=sig,
                        mode="lines",
                        name=name,
                        line=dict(shape="hv")
                    ),
                    row=i+1,
                    col=1
                )

                fig_d.update_yaxes(
                    range=[-0.2, 1.2],
                    row=i+1,
                    col=1
                )

            fig_d.update_layout(height=250 + 90*len(changed))

            st.plotly_chart(fig_d, use_container_width=True)

else:
    st.info("Upload matching CFG and DAT files to begin.")
