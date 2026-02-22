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
st.title("⚡ COMTRADE DR Analyzer")

st.sidebar.header("Upload DR Files")

cfg_file = st.sidebar.file_uploader("Upload .CFG file", type=["cfg"])
dat_file = st.sidebar.file_uploader("Upload .DAT file", type=["dat"])


# -----------------------------------------------------------
# Function: Make Channel Names Unique
# -----------------------------------------------------------
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


# -----------------------------------------------------------
# Main Processing
# -----------------------------------------------------------
if cfg_file and dat_file:

    with tempfile.TemporaryDirectory() as tmpdir:

        cfg_path = os.path.join(tmpdir, "temp.cfg")
        dat_path = os.path.join(tmpdir, "temp.dat")

        with open(cfg_path, "wb") as f:
            f.write(cfg_file.read())

        with open(dat_path, "wb") as f:
            f.write(dat_file.read())

        rec = Comtrade()

        try:
            rec.load(cfg_path, dat_path)
        except Exception as e:
            st.error(f"Error loading COMTRADE file: {e}")
            st.stop()

        st.success("Files Loaded Successfully")

        # ---------------------------------------------------
        # Time Vector
        # ---------------------------------------------------
        df = rec.to_dataframe().reset_index()
        time_vector = df["time"]

        # ---------------------------------------------------
        # Analog Channels
        # ---------------------------------------------------
        analog_ids = make_unique(rec.analog_channel_ids)
        analog_data = pd.DataFrame(rec.analog).T

        analog_data.columns = analog_ids
        analog_data["time"] = time_vector

        # Remove empty columns
        analog_data = analog_data.loc[:, (analog_data != 0).any(axis=0)]

        # ---------------------------------------------------
        # Digital Channels
        # ---------------------------------------------------
        digital_ids = make_unique(rec.digital_channel_ids)

        digital_data = pd.DataFrame(rec.status).T
        digital_data.columns = digital_ids
        digital_data["time"] = time_vector

        # Remove zero-only digital channels
        digital_data = digital_data.loc[:, (digital_data != 0).any(axis=0)]

        # ---------------------------------------------------
        # Channel Selection
        # ---------------------------------------------------
        st.sidebar.header("Channel Selection")

        analog_options = [c for c in analog_data.columns if c != "time"]
        selected_analog = st.sidebar.multiselect(
            "Select Analog Channels",
            analog_options,
            default=analog_options[:6] if len(analog_options) >= 6 else analog_options
        )

        digital_options = [c for c in digital_data.columns if c != "time"]
        selected_digital = st.sidebar.multiselect(
            "Select Digital Channels",
            digital_options,
            default=digital_options
        )

        # ---------------------------------------------------
        # Plotting
        # ---------------------------------------------------
        total_rows = 1 + len(selected_digital)

        fig = make_subplots(
            rows=total_rows,
            cols=1,
            shared_xaxes=True,
            subplot_titles=["Analog Channels"] + selected_digital
        )

        # Analog Plot
        for col in selected_analog:
            fig.add_trace(
                go.Scatter(
                    x=analog_data["time"].values,
                    y=analog_data[col].values,
                    mode="lines",
                    name=col
                ),
                row=1,
                col=1
            )

        # Digital Plots
        for i, col in enumerate(selected_digital):
            fig.add_trace(
                go.Scatter(
                    x=digital_data["time"].values,
                    y=digital_data[col].values,
                    mode="lines",
                    name=col
                ),
                row=i + 2,
                col=1
            )

            fig.update_yaxes(
                range=[-0.25, 1.25],
                row=i + 2,
                col=1,
                showticklabels=False
            )

        fig.update_layout(
            height=400 + len(selected_digital) * 120,
            title="DR Event Analysis",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---------------------------------------------------
        # Event Summary
        # ---------------------------------------------------
        st.subheader("Event Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Analog Channels:**", len(analog_options))
            st.write("**Digital Channels:**", len(digital_options))

        with col2:
            if selected_analog:
                max_current = analog_data[selected_analog].abs().max().max()
                st.write("**Maximum Magnitude:**", round(max_current, 3))

else:
    st.info("Please upload both .CFG and .DAT files.")
