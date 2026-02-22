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
st.title("⚡ Protection Performance Research Platform – Stable Build")

st.sidebar.header("Upload COMTRADE Files")
cfg_file = st.sidebar.file_uploader("Upload .CFG", type=["cfg"])
dat_file = st.sidebar.file_uploader("Upload .DAT", type=["dat"])


# ============================================================
# Utility Functions
# ============================================================

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


def calculate_rms(signal, window_samples):
    rms = np.zeros_like(signal)
    for i in range(window_samples, len(signal)):
        window = signal[i-window_samples:i]
        rms[i] = np.sqrt(np.mean(window**2))
    return rms


def symmetrical_components(Ia, Ib, Ic):
    a = np.exp(1j * 2*np.pi/3)
    I0 = (Ia + Ib + Ic) / 3
    I1 = (Ia + a*Ib + a**2*Ic) / 3
    I2 = (Ia + a**2*Ib + a*Ic) / 3
    return I0, I1, I2


# ============================================================
# MAIN EXECUTION
# ============================================================

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

        # =====================================================
        # ANALOG PROCESSING (ROBUST MULTI-VENDOR)
        # =====================================================

        analog_ids = make_unique(rec.analog_channel_ids)
        analog_df = pd.DataFrame(rec.analog).T
        analog_df.columns = analog_ids
        analog_df["time"] = time_vector

        voltage_channels = []
        current_channels = []

        for idx, ch in enumerate(rec.cfg.analog_channels):

            ch_str = str(ch).upper()
            name = analog_ids[idx].upper()

            # Current detection
            if (" A" in ch_str or "(A" in ch_str or
                "AMP" in ch_str or name.startswith("I")):
                current_channels.append(analog_ids[idx])

            # Voltage detection
            elif (" V" in ch_str or "(V" in ch_str or
                  name.startswith("V")):
                voltage_channels.append(analog_ids[idx])

        voltage_channels = voltage_channels[:4]
        current_channels = current_channels[:4]

        # =====================================================
        # RMS ENGINE (RESEARCH SAFE)
        # =====================================================

        sampling_interval = time_vector[1] - time_vector[0]
        sampling_freq = 1 / sampling_interval
        window_samples = int(sampling_freq / 50)

        rms_currents = {}
        for ch in current_channels:
            rms_currents[ch] = calculate_rms(
                analog_df[ch].values,
                window_samples
            )

        # =====================================================
        # ADAPTIVE FAULT DETECTION
        # =====================================================

        combined_rms = np.max(
            np.vstack([rms_currents[ch] for ch in current_channels]),
            axis=0
        )

        prefault_samples = int(0.2 * len(time_vector))
        prefault_rms = np.mean(combined_rms[:prefault_samples])
        threshold = 1.5 * prefault_rms

        fault_indices = np.where(combined_rms > threshold)[0]

        if len(fault_indices) > 0:
            fault_start = time_vector[fault_indices[0]]
            fault_end = time_vector[fault_indices[-1]]
            fault_duration = fault_end - fault_start
        else:
            fault_start = None
            fault_end = None
            fault_duration = 0

        # =====================================================
        # SYMMETRICAL COMPONENT ANALYSIS
        # =====================================================

        if len(current_channels) >= 3 and len(fault_indices) > 0:

            fw = slice(fault_indices[0], fault_indices[-1])

            Ia = analog_df[current_channels[0]].values[fw]
            Ib = analog_df[current_channels[1]].values[fw]
            Ic = analog_df[current_channels[2]].values[fw]

            I0, I1, I2 = symmetrical_components(Ia, Ib, Ic)

            I0_mag = np.mean(np.abs(I0))
            I1_mag = np.mean(np.abs(I1))
            I2_mag = np.mean(np.abs(I2))

            if I0_mag > 0.1 * I1_mag:
                fault_type = "Ground Fault"
            elif I2_mag > 0.1 * I1_mag:
                fault_type = "Phase-to-Phase Fault"
            else:
                fault_type = "Three Phase Fault"

        else:
            fault_type = "Not Determined"

        # =====================================================
        # DIGITAL PROCESSING
        # =====================================================

        digital_ids = make_unique(rec.digital_channel_ids)
        digital_df = pd.DataFrame(rec.status).T
        digital_df.columns = digital_ids
        digital_df["time"] = time_vector

        digital_df = digital_df.loc[:, (digital_df != 0).any(axis=0)]
        digital_channels = [c for c in digital_df.columns if c != "time"]

        st.sidebar.header("Trip Channel Selection")

        trip_channel = st.sidebar.selectbox(
            "Select Trip Digital",
            digital_channels
        )

        trip_signal = digital_df[trip_channel].values
        trip_indices = np.where(trip_signal == 1)[0]

        if len(trip_indices) > 0 and fault_start is not None:
            trip_start = time_vector[trip_indices[0]]
            operate_time = trip_start - fault_start
        else:
            trip_start = None
            operate_time = None

        # =====================================================
        # PLOTTING
        # =====================================================

        total_rows = 2 + len(digital_channels)

        fig = make_subplots(
            rows=total_rows,
            cols=1,
            shared_xaxes=True,
            subplot_titles=["Voltages (4)",
                            "Currents (4 - RMS)"] + digital_channels
        )

        # Voltages
        for col in voltage_channels:
            fig.add_trace(
                go.Scatter(x=time_vector,
                           y=analog_df[col].values,
                           mode="lines",
                           name=col),
                row=1, col=1
            )

        # RMS Currents
        for col in current_channels:
            fig.add_trace(
                go.Scatter(x=time_vector,
                           y=rms_currents[col],
                           mode="lines",
                           name=f"{col} RMS"),
                row=2, col=1
            )

        # Digital Channels
        for i, col in enumerate(digital_channels):
            fig.add_trace(
                go.Scatter(x=time_vector,
                           y=digital_df[col].values,
                           mode="lines",
                           name=col),
                row=i+3, col=1
            )
            fig.update_yaxes(range=[-0.25, 1.25],
                             showticklabels=False,
                             row=i+3, col=1)

        fig.update_layout(
            height=650 + len(digital_channels)*80,
            showlegend=False,
            title="Protection Research Analysis"
        )

        st.plotly_chart(fig, use_container_width=True)

        # =====================================================
        # SUMMARY
        # =====================================================

        st.subheader("📊 Protection Performance Summary")

        summary = pd.DataFrame({
            "Metric": [
                "Fault Start (s)",
                "Fault End (s)",
                "Fault Duration (s)",
                "Relay Operate Time (ms)",
                "Fault Type"
            ],
            "Value": [
                fault_start,
                fault_end,
                fault_duration,
                operate_time*1000 if operate_time else None,
                fault_type
            ]
        })

        st.table(summary)

        st.download_button(
            "Download Event Summary CSV",
            summary.to_csv(index=False),
            file_name="event_summary.csv"
        )

else:
    st.info("Upload both .CFG and .DAT files to begin analysis.")
