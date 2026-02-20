import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import comtrade as ct
import re

st.set_page_config(page_title="COMTRADE Viewer", layout="wide")

st.title("⚡ COMTRADE Fault Record Viewer")

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

    # -------------------------
    # HEADER INFORMATION
    # -------------------------

    substation = getattr(rec, "station_name", "Unknown")
    feeder = getattr(rec, "rec_dev_id", "Unknown")
    relay = getattr(rec, "device_id", "Unknown")

    st.markdown("### 📋 Record Information")
    st.info(f"""
    **Substation:** {substation}  
    **Feeder:** {feeder}  
    **Relay:** {relay}
    """)

    analog_names = rec.analog_channel_ids
    analog_data = np.array(rec.analog)

    if analog_data.shape[0] != len(analog_names):
        analog_data = analog_data.T

    # -------------------------
    # SELECT 4U & 4I
    # -------------------------

    voltage_channels = []
    current_channels = []

    for name in analog_names:
        name_upper = name.upper()

        if re.search(r'\b(V|U)[A-Z]?\b', name_upper):
            voltage_channels.append(name)

        elif re.search(r'\bI[A-Z]?\b', name_upper):
            current_channels.append(name)

    voltage_channels = voltage_channels[:4]
    current_channels = current_channels[:4]

    # -------------------------
    # ANALOG PLOT
    # -------------------------

    st.subheader("Analog Channels")

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
            go.Scatter(
                x=time,
                y=analog_data[idx],
                mode="lines",
                name=name,
                legendgroup="Voltages"
            ),
            row=1,
            col=1
        )

    # Currents
    for name in current_channels:
        idx = analog_names.index(name)
        fig.add_trace(
            go.Scatter(
                x=time,
                y=analog_data[idx],
                mode="lines",
                name=name,
                legendgroup="Currents"
            ),
            row=2,
            col=1
        )

    # -------------------------
    # Fault Detection (Amplitude Based)
    # -------------------------

    amplitude = np.max(np.abs(analog_data), axis=0)
    threshold = 0.15 * np.max(amplitude)

    active_indices = np.where(amplitude >= threshold)[0]

    if len(active_indices) > 0:
        fault_start = time[active_indices[0]]
        fault_end = time[active_indices[-1]]
        fault_duration = fault_end - fault_start

        fig.add_vline(x=fault_start, line_color="red", line_dash="dash")
        fig.add_vline(x=fault_end, line_color="green", line_dash="dash")

        st.success(f"🔴 Fault Start: {fault_start:.6f} s")
        st.success(f"🔵 Fault End: {fault_end:.6f} s")
        st.success(f"⏱ Fault Duration: {fault_duration:.6f} s")

    fig.update_layout(height=700)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------
    # DIGITAL (Changed Only)
    # -------------------------

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
                vertical_spacing=0.02
            )

            for i, (name, sig) in enumerate(changed):
                fig_d.add_trace(
                    go.Scatter(
                        x=time,
                        y=sig,
                        mode="lines",
                        name=name,
                        line=dict(shape="hv", width=1.5)
                    ),
                    row=i+1,
                    col=1
                )

                fig_d.update_yaxes(
                    range=[-0.2, 1.2],
                    row=i+1,
                    col=1
                )

            fig_d.update_layout(
                height=200 + 100 * len(changed),
                showlegend=True
            )

            st.plotly_chart(fig_d, use_container_width=True)

        else:
            st.info("No digital signals changed state.")

    else:
        st.warning("No digital channels available.")

else:
    st.info("Upload matching CFG and DAT files to begin.")
