import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import comtrade as ct
import math

st.set_page_config(page_title="COMTRADE Fault Analyzer", layout="wide")

st.title("⚡ COMTRADE Fault Record Analyzer")

st.markdown("Upload matching **1.cfg** and **1.dat** files.")

# -----------------------------
# File Upload
# -----------------------------

cfg_file = st.file_uploader("Upload CFG file", type=["cfg"])
dat_file = st.file_uploader("Upload DAT file", type=["dat"])

if cfg_file and dat_file:

    # Save temporarily
    with open("temp.cfg", "wb") as f:
        f.write(cfg_file.read())

    with open("temp.dat", "wb") as f:
        f.write(dat_file.read())

    # -----------------------------
    # Load COMTRADE
    # -----------------------------
    rec = ct.Comtrade()
    rec.load("temp.cfg", "temp.dat")

    time = np.array(rec.time)

    analog_names = rec.analog_channel_ids
    analog_data = np.array(rec.analog)

    # Normalize analog shape
    if analog_data.shape[0] != len(analog_names):
        analog_data = analog_data.T

    # -----------------------------
    # Analog DataFrame
    # -----------------------------
    df_analog = pd.DataFrame(
        {analog_names[i]: analog_data[i] for i in range(len(analog_names))},
        index=time
    )

    # -----------------------------
    # Plot Analog Channels
    # -----------------------------
    st.subheader("Analog Channels")

    fig = go.Figure()

    for col in df_analog.columns:
        fig.add_trace(
            go.Scatter(
                x=df_analog.index,
                y=df_analog[col],
                mode="lines",
                name=col
            )
        )

    # Trigger Marker
    trigger = getattr(rec, "trigger_time", None)
    if trigger:
        fig.add_vline(x=float(trigger), line_color="red", line_dash="dash")

    fig.update_layout(
        height=600,
        title="Analog Waveforms",
        xaxis_title="Time (s)"
    )

    st.plotly_chart(fig, use_container_width=True)

  # -----------------------------
# Digital Channels (Robust Version)
# -----------------------------
status_raw = rec.status
status_names = rec.status_channel_ids

if status_raw and len(status_raw) > 0:

    st.subheader("Digital Channels")

    status_array = np.array(status_raw)

    if status_array.shape[0] != len(status_names):
        status_array = status_array.T

    n_rows = len(status_names)

    # Dynamically adjust spacing
    vertical_spacing = min(0.02, 0.5 / max(1, n_rows))

    fig_d = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=vertical_spacing
    )

    for i in range(n_rows):
        fig_d.add_trace(
            go.Scatter(
                x=time,
                y=status_array[i],
                mode="lines",
                name=status_names[i],
                line=dict(shape="hv", width=1.2),
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
        height=max(300, 80 * n_rows),
        title="Digital Status Signals",
        showlegend=False
    )

    st.plotly_chart(fig_d, use_container_width=True)

else:
    st.warning("No digital channels found in this record.")

    # -----------------------------
    # Event Detection (Simple Amplitude Based)
    # -----------------------------
    amp = np.max(np.abs(analog_data), axis=0)
    threshold = 0.1 * np.max(amp)

    active_indices = np.where(amp >= threshold)[0]

    if len(active_indices) > 0:
        event_start = time[active_indices[0]]
        event_end = time[active_indices[-1]]

        st.success(f"Detected Event Start: {event_start:.6f} s")
        st.success(f"Detected Event End: {event_end:.6f} s")

    # -----------------------------
    # Summary Table
    # -----------------------------
    st.subheader("Analog Channel Summary")

    summary = []

    for col in df_analog.columns:
        peak = float(np.max(np.abs(df_analog[col])))
        rms = float(np.sqrt(np.mean(np.square(df_analog[col]))))

        summary.append({
            "Channel": col,
            "Peak Instantaneous": peak,
            "RMS": rms
        })

    df_summary = pd.DataFrame(summary)

    st.dataframe(df_summary)

    # -----------------------------
    # Metadata
    # -----------------------------
    st.subheader("Record Information")

    st.json({
        "Station": rec.station_name,
        "Total Samples": len(time),
        "Sampling Rate": getattr(rec, "frequency", None),
        "Analog Channels": len(analog_names),
        "Digital Channels": len(status_names) if status_names else 0
    })

else:
    st.info("Please upload matching CFG and DAT files.")
