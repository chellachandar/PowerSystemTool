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
st.title("⚡ Protection Performance Research Platform")

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
    return np.sqrt(
        np.convolve(signal**2,
                    np.ones(window_samples)/window_samples,
                    mode='same')
    )


def symmetrical_components(Ia, Ib, Ic):
    a = np.exp(1j * 2*np.pi/3)
    I0 = (Ia + Ib + Ic) / 3
    I1 = (Ia + a*Ib + a**2*Ic) / 3
    I2 = (Ia + a**2*Ib + a*Ic) / 3
    return I0, I1, I2


# ============================================================
# Main Execution
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
        # ANALOG PROCESSING
        # =====================================================
        analog_ids = make_unique(rec.analog_channel_ids)
        analog_df = pd.DataFrame(rec.analog).T
        analog_df.columns = analog_ids
        analog_df["time"] = time_vector

        # Auto detect 4 Voltages & 4 Currents
        voltage_channels = [c for c in analog_ids if "V" in c.upper()][:4]
        current_channels = [c for c in analog_ids if "I" in c.upper()][:4]

        # =====================================================
        # RMS ENGINE
        # =====================================================
        sampling_interval = time_vector[1] - time_vector[0]
        sampling_freq = 1 / sampling_interval
        window_samples = int(sampling_freq / 50)  # 1-cycle RMS (50 Hz)

        rms_currents = {}
        for ch in current_channels:
            rms_currents[ch] = calculate_rms(
                analog_df[ch].values,
                window_samples
            )

        # =====================================================
        # AUTOMATIC FAULT DETECTION
        # =====================================================
        combined_rms = np.max(
            np.vstack([rms_currents[ch] for ch in current_channels]),
            axis=0
        )

        threshold = 0.2 * np.max(combined_rms)
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
        # SYMMETRICAL COMPONENT ENGINE
        # =====================================================
        if len(current_channels) >= 3:

            Ia = rms_currents[current_channels[0]]
            Ib = rms_currents[current_channels[1]]
            Ic = rms_currents[current_channels[2]]

            I0, I1, I2 = symmetrical_components(Ia, Ib, Ic)

            I0_mag = np.abs(I0)
            I1_mag = np.abs(I1)
            I2_mag = np.abs(I2)

            if np.mean(I0_mag) > 0.1 * np.mean(I1_mag):
                fault_type = "Ground Fault"
            elif np.mean(I2_mag) > 0.1 * np.mean(I1_mag):
                fault_type = "Phase-to-Phase Fault"
            else:
                fault_type = "Three Phase Fault"

        else:
            fault_type = "Insufficient Phase Data"

        # =====================================================
        # DIGITAL PROCESSING
        # =====================================================
        digital_ids = make_unique(rec.digital_channel_ids)
        digital_df = pd.DataFrame(rec.status).T
        digital_df.columns = digital_ids
        digital_df["time"] = time_vector

        digital_df = digital_df.loc[:, (digital_df != 0).any(axis=0)]
        digital_channels = [c for c in digital_df.columns if c != "time"]

        # Trip selection
        st.sidebar.header("Trip Channel Selection")
        trip_channel = st.sidebar.selectbox(
            "Select Trip Digital",
            digital_channels
        )

        trip_signal = digital_df[trip_channel].values
        trip_indices = np.where(trip_signal == 1)[0]

        if len(trip_indices) > 0:
            trip_start = time_vector[trip_indices[0]]
            trip_end = time_vector[trip_indices[-1]]
            operate_time = trip_start - fault_start if fault_start else None
        else:
            trip_start = None
            trip_end = None
            operate_time = None

        # =====================================================
        # PLOTTING
        # =====================================================
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
                row=1, col=1
            )

        # Currents
        for col in current_channels:
            fig.add_trace(
                go.Scatter(
                    x=time_vector,
                    y=rms_currents[col],
                    mode="lines",
                    name=f"{col} (RMS)"
                ),
                row=2, col=1
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
                row=i+3, col=1
            )
            fig.update_yaxes(range=[-0.25, 1.25],
                             showticklabels=False,
                             row=i+3, col=1)

        fig.update_layout(
            height=600 + len(digital_channels)*100,
            showlegend=False,
            title="Protection Research Analysis"
        )

        st.plotly_chart(fig, use_container_width=True)

        # =====================================================
        # RESEARCH SUMMARY TABLE
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
