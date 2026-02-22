import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from comtrade import Comtrade
from datetime import timedelta
import warnings
import tempfile
import os

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")
st.title("⚡ DR File Analyzer (COMTRADE)")

# ------------------------------
# File Upload Section
# ------------------------------
st.sidebar.header("Upload COMTRADE Files")

cfg_file = st.sidebar.file_uploader("Upload .cfg file", type=["cfg"])
dat_file = st.sidebar.file_uploader("Upload .dat file", type=["dat"])

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

        # ---------------------------------
        # Analog Channel Extraction
        # ---------------------------------
        df = rec.to_dataframe().reset_index()
        time_vector = df["time"]

        analog_ids = rec.analog_channel_ids
        digital_ids = rec.digital_channel_ids

        analog_data = pd.DataFrame(rec.analog).T
        analog_data.columns = analog_ids
        analog_data["time"] = time_vector

        # ---------------------------------
        # Digital Channel Processing
        # ---------------------------------
        digital_data = pd.DataFrame(rec.status).T
        digital_data.columns = digital_ids
        digital_data["time"] = time_vector

        # Remove all-zero digital channels
        digital_data = digital_data.loc[:, (digital_data != 0).any()]

        # ---------------------------------
        # Plotting
        # ---------------------------------
        num_digital = len(digital_data.columns) - 1

        fig = make_subplots(
            rows=num_digital + 2,
            cols=1,
            shared_xaxes=True,
            subplot_titles=["Analog Channels", "Currents"] + list(digital_data.columns[:-1])
        )

        # Add Analog Channels
        for col in analog_ids:
            fig.add_trace(
                go.Scatter(
                    x=analog_data["time"],
                    y=analog_data[col],
                    mode="lines",
                    name=col
                ),
                row=1,
                col=1
            )

        # Add Digital Channels
        for i, col in enumerate(digital_data.columns[:-1]):
            fig.add_trace(
                go.Scatter(
                    x=digital_data["time"],
                    y=digital_data[col],
                    mode="lines",
                    name=col
                ),
                row=i + 3,
                col=1
            )

        fig.update_layout(
            height=300 + num_digital * 150,
            showlegend=False,
            title="DR Event Analysis"
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload both .cfg and .dat files.")
