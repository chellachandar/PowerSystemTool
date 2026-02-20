import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import comtrade as ct
import re
import json
import math

st.set_page_config(page_title="COMTRADE Viewer", layout="wide")

st.title("⚡ COMTRADE Fault Record Viewer")

# -------------------------
# File Upload Section
# -------------------------

cfg_file = st.file_uploader("Upload CFG file", type=["cfg"])
dat_file = st.file_uploader("Upload DAT file", type=["dat"])

if cfg_file and dat_file:

    st.success("Files uploaded successfully")

    # Save to temp memory
    with open("temp.cfg", "wb") as f:
        f.write(cfg_file.read())
    with open("temp.dat", "wb") as f:
        f.write(dat_file.read())

    # -------------------------
    # Load COMTRADE
    # -------------------------

    rec = ct.Comtrade()
    rec.load("temp.cfg", "temp.dat")

    time_full = np.array(rec.time)
    analog_names = [str(x).strip() for x in rec.analog_channel_ids]
    analog_data = np.array(rec.analog)

    # Normalize analog shape
    if analog_data.shape[0] < analog_data.shape[1]:
        analog_data = analog_data
    else:
        analog_data = analog_data.T

    # -------------------------
    # Simple Primary Channel Selection
    # -------------------------

    selected_channels = analog_names[:8]  # simplified selection
    df_analog = pd.DataFrame(
        {analog_names[i]: analog_data[i] for i in range(len(selected_channels))},
        index=time_full
    )

    # -------------------------
    # Plot
    # -------------------------

    fig = make_subplots(rows=1, cols=1)

    for col in df_analog.columns:
        fig.add_trace(
            go.Scatter(
                x=df_analog.index,
                y=df_analog[col],
                mode="lines",
                name=col
            )
        )

    fig.update_layout(
        title="Analog Channels",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------
    # Summary
    # -------------------------

    summary_data = []

    for col in df_analog.columns:
        peak = float(np.max(np.abs(df_analog[col])))
        rms = float(np.sqrt(np.mean(np.square(df_analog[col]))))
        summary_data.append({
            "Channel": col,
            "Peak Instantaneous": peak,
            "RMS": rms
        })

    df_summary = pd.DataFrame(summary_data)

    st.subheader("Channel Summary")
    st.dataframe(df_summary)

    st.json({
        "Total Samples": len(time_full),
        "Channels Plotted": list(df_analog.columns)
    })

else:
    st.info("Upload matching CFG and DAT files to begin.")
