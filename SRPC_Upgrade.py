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
st.title("⚡ Protection Performance Benchmarking Platform")

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
# MAIN
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
        # ANALOG PROCESSING (KEEP SIMPLE – WORKING)
        # -------------------------------
        analog_ids = make_unique(rec.analog_channel_ids)
        analog_df = pd.DataFrame(rec.analog).T
        analog_df.columns = analog_ids
        analog_df["time"] = time_vector

        voltage_channels = [c for c in analog_ids if "V" in c.upper()][:4]
        current_channels = [c for c in analog_ids if "I" in c.upper()][:4]

        # -------------------------------
        # FAULT START DETECTION (CURRENT BASED)
        # -------------------------------
        combined_current = np.max(
            np.vstack([np.abs(analog_df[ch].values) for ch in current_channels]),
            axis=0
        )

        prefault_samples = int(0.2 * len(time_vector))
        prefault_mean = np.mean(combined_current[:prefault_samples])

        threshold = 3 * prefault_mean

        above = combined_current > threshold

        if np.any(above):
            fault_start_index = np.argmax(above)
            fault_start = time_vector[fault_start_index]
        else:
            fault_start = None

        # -------------------------------
        # DIGITAL PROCESSING
        # -------------------------------
        digital_ids = make_unique(rec.digital_channel_ids)
        digital_df = pd.DataFrame(rec.status).T
        digital_df.columns = digital_ids
        digital_df["time"] = time_vector

        digital_df = digital_df.loc[:, (digital_df != 0).any(axis=0)]
        digital_channels = [c for c in digital_df.columns if c != "time"]

        # -------------------------------
        # TRIP SELECTION
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
        else:
            trip_start = None

        # -------------------------------
        # CB AUXILIARY OPEN DETECTION
        # -------------------------------
        cb_open_channels = [
            c for c in digital_channels
            if "CB" in c.upper() and "OPN" in c.upper()
        ]

        cb_open_time = None

        for cb_ch in cb_open_channels:
            signal = digital_df[cb_ch].values
            indices = np.where(signal == 1)[0]
            if len(indices) > 0:
                cb_open_time = time_vector[indices[0]]
                break

        # -------------------------------
        # BENCHMARK CALCULATIONS
        # -------------------------------
        if fault_start is not None and trip_start is not None:
            operate_time = trip_start - fault_start
        else:
            operate_time = None

        if trip_start is not None and cb_open_time is not None:
            breaker_time = cb_open_time - trip_start
        else:
            breaker_time = None

        if fault_start is not None and cb_open_time is not None:
            clearing_time = cb_open_time - fault_start
        else:
            clearing_time = None

        # -------------------------------
        # PLOTTING
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

        # Digitals
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
            height=650 + len(digital_channels) * 80,
            title="Protection Performance Analysis",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------
        # PROTECTION PERFORMANCE SUMMARY
        # -------------------------------
        st.subheader("📊 Protection Performance Summary")

        summary = pd.DataFrame({
            "Metric": [
                "Fault Start (s)",
                "Trip Start (s)",
                "CB Open Time (s)",
                "Relay Operate Time (ms)",
                "Breaker Opening Time (ms)",
                "Total Clearing Time (ms)"
            ],
            "Value": [
                fault_start,
                trip_start,
                cb_open_time,
                operate_time * 1000 if operate_time else None,
                breaker_time * 1000 if breaker_time else None,
                clearing_time * 1000 if clearing_time else None
            ]
        })

        st.table(summary)

        st.download_button(
            "Download Event Summary CSV",
            summary.to_csv(index=False),
            file_name="protection_performance_summary.csv"
        )

else:
    st.info("Please upload both .CFG and .DAT files.")
