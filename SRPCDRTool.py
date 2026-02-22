import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from comtrade import Comtrade
import tempfile
import os
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")
st.title("⚡ COMTRADE DR Analyzer – Protection Edition")

st.sidebar.header("Upload DR Files")

cfg_file = st.sidebar.file_uploader("Upload .CFG file", type=["cfg"])
dat_file = st.sidebar.file_uploader("Upload .DAT file", type=["dat"])


# ----------------------------------------------------------
# Make channel names unique
# ----------------------------------------------------------
def make_unique(names):
    seen = {}
    unique = []
    for name in names:
        if name in seen:
            seen[name] += 1
            unique.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            unique.append(name)
    return unique


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
if cfg_file and dat_file:

    with tempfile.TemporaryDirectory() as tmpdir:

        cfg_path = os.path.join(tmpdir, "temp.cfg")
        dat_path = os.path.join(tmpdir, "temp.dat")

        with open(cfg_path, "wb") as f:
            f.write(cfg_file.read())

        with open(dat_path, "wb") as f:
            f.write(dat_file.read())

        rec = Comtrade()
        rec.load(cfg_path, dat_path)

        st.success("Files Loaded Successfully")

        df = rec.to_dataframe().reset_index()
        time_vector = df["time"].values

        # -------------------------------
        # Analog Processing
        # -------------------------------
        analog_ids = make_unique(rec.analog_channel_ids)
        analog_df = pd.DataFrame(rec.analog).T
        analog_df.columns = analog_ids
        analog_df["time"] = time_vector

        # Auto detect Voltages & Currents
        voltage_channels = [c for c in analog_ids if "V" in c.upper()][:4]
        current_channels = [c for c in analog_ids if "I" in c.upper()][:4]

        # -------------------------------
        # Digital Processing
        # -------------------------------
        digital_ids = make_unique(rec.digital_channel_ids)
        digital_df = pd.DataFrame(rec.status).T
        digital_df.columns = digital_ids
        digital_df["time"] = time_vector

        # Remove zero-only digital channels
        digital_df = digital_df.loc[:, (digital_df != 0).any(axis=0)]

        digital_channels = [c for c in digital_df.columns if c != "time"]

        # -------------------------------
        # Trip Selection
        # -------------------------------
        st.sidebar.header("Trip Analysis")

        trip_channel = st.sidebar.selectbox(
            "Select Trip Digital Channel",
            digital_channels
        )

        trip_signal = digital_df[trip_channel].values

        trip_indices = np.where(trip_signal == 1)[0]

        if len(trip_indices) > 0:
            trip_start = time_vector[trip_indices[0]]
            trip_end = time_vector[trip_indices[-1]]
            fault_duration = trip_end - trip_start
        else:
            trip_start = None
            trip_end = None
            fault_duration = 0

        # -------------------------------
        # Plot Layout
        # -------------------------------
        total_rows = 2 + len(digital_channels)

        fig = make_subplots(
            rows=total_rows,
            cols=1,
            shared_xaxes=True,
            subplot_titles=["Voltages (4)", "Currents (4)"] + digital_channels
        )

        # Voltages
        for col in voltage_channels:
            fig.add_trace(
                go.Scatter(
                    x=time_vector,
                    y=analog_df[col].values,
                    mode="lines",
                    name=col
                ),
                row=1,
                col=1
            )

        # Currents
        for col in current_channels:
            fig.add_trace(
                go.Scatter(
                    x=time_vector,
                    y=analog_df[col].values,
                    mode="lines",
                    name=col
                ),
                row=2,
                col=1
            )

        # Digital
        for i, col in enumerate(digital_channels):
            fig.add_trace(
                go.Scatter(
                    x=time_vector,
                    y=digital_df[col].values,
                    mode="lines",
                    name=col
                ),
                row=i + 3,
                col=1
            )

            fig.update_yaxes(
                range=[-0.25, 1.25],
                row=i + 3,
                col=1,
                showticklabels=False
            )

        fig.update_layout(
            height=600 + len(digital_channels) * 120,
            title="DR Event Analysis",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------
        # Event Summary
        # -------------------------------
        st.subheader("⚡ Trip & Fault Summary")

        col1, col2, col3 = st.columns(3)

        col1.metric("Trip Start (s)", f"{trip_start:.4f}" if trip_start else "Not Found")
        col2.metric("Trip End (s)", f"{trip_end:.4f}" if trip_end else "Not Found")
        col3.metric("Fault Duration (s)", f"{fault_duration:.4f}")

else:
    st.info("Please upload both .CFG and .DAT files.")
