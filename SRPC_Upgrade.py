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
# Utility: Make channel names unique
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
# MAIN EXECUTION
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
        # ANALOG PROCESSING
        # -------------------------------
        analog_ids = make_unique(rec.analog_channel_ids)
        analog_df = pd.DataFrame(rec.analog).T
        analog_df.columns = analog_ids
        analog_df["time"] = time_vector

        voltage_channels = [c for c in analog_ids if "V" in c.upper()][:4]
        current_channels = [c for c in analog_ids if "I" in c.upper()][:4]

        # -------------------------------
        # FAULT START DETECTION
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
        # CB AUX OPEN DETECTION
        # -------------------------------
        cb_open_times = []

        for ch in digital_channels:
            if "CB" in ch.upper() and "OPN" in ch.upper():
                signal = digital_df[ch].values
                indices = np.where(signal == 1)[0]
                if len(indices) > 0:
                    cb_open_times.append(time_vector[indices[0]])

        if len(cb_open_times) > 0:
            cb_open_time = min(cb_open_times)
        else:
            cb_open_time = None

        # -------------------------------
        # BENCHMARK CALCULATIONS
        # -------------------------------
        operate_time = (
            trip_start - fault_start
            if fault_start is not None and trip_start is not None
            else None
        )

        breaker_time = (
            cb_open_time - trip_start
            if trip_start is not None and cb_open_time is not None
            else None
        )

        clearing_time = (
            cb_open_time - fault_start
            if fault_start is not None and cb_open_time is not None
            else None
        )

        # -------------------------------
        # SAFE DISPLAY STRINGS ("--")
        # -------------------------------
        fault_str = f"{fault_start:.4f}s" if fault_start is not None else "--"
        trip_str = f"{trip_start:.4f}s" if trip_start is not None else "--"
        cb_str = f"{cb_open_time:.4f}s" if cb_open_time is not None else "--"

        st.markdown("### Protection Performance Analysis")
        st.markdown(
            f"""
            🔴 **Fault Start:** {fault_str} &nbsp;&nbsp;&nbsp;
            🔵 **Trip:** {trip_str} &nbsp;&nbsp;&nbsp;
            🟢 **CB Open:** {cb_str}
            """,
            unsafe_allow_html=True
        )

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
                go.Scatter(x=time_vector,
                           y=analog_df[col].values,
                           mode="lines"),
                row=1, col=1
            )

        # Currents
        for col in current_channels:
            fig.add_trace(
                go.Scatter(x=time_vector,
                           y=analog_df[col].values,
                           mode="lines"),
                row=2, col=1
            )

        # Digital signals
        for i, col in enumerate(digital_channels):
            fig.add_trace(
                go.Scatter(x=time_vector,
                           y=digital_df[col].values,
                           mode="lines"),
                row=i + 3, col=1
            )
            fig.update_yaxes(range=[-0.25, 1.25],
                             showticklabels=False,
                             row=i + 3, col=1)

        # -------------------------------
        # CONTINUOUS VERTICAL LINES
        # -------------------------------
        if fault_start is not None:
            fig.add_shape(
                type="line",
                x0=fault_start,
                x1=fault_start,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="red", width=2, dash="dash")
            )

        if trip_start is not None:
            fig.add_shape(
                type="line",
                x0=trip_start,
                x1=trip_start,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="blue", width=2, dash="dash")
            )

        if cb_open_time is not None:
            fig.add_shape(
                type="line",
                x0=cb_open_time,
                x1=cb_open_time,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="green", width=2, dash="dash")
            )

        fig.update_layout(
            height=650 + len(digital_channels) * 80,
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------
        # SUMMARY TABLE
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
                fault_start if fault_start is not None else "--",
                trip_start if trip_start is not None else "--",
                cb_open_time if cb_open_time is not None else "--",
                operate_time * 1000 if operate_time is not None else "--",
                breaker_time * 1000 if breaker_time is not None else "--",
                clearing_time * 1000 if clearing_time is not None else "--"
            ]
        })

        st.table(summary)

        st.download_button(
            "Download Event Summary CSV",
            summary.to_csv(index=False),
            file_name="protection_performance_summary.csv"
        )
        
        st.markdown(
    """
    ⚠️ **Performance Calculation Disclaimer:**
    The accuracy and availability of protection performance parameters depend entirely on the 
    disturbance recorder configuration within the relay. Missing pickup/start, trip, or breaker auxiliary digital signals will result in incomplete 
    or unavailable timing calculations.
    """
)

else:
    st.info("Please upload both .CFG and .DAT files.")
