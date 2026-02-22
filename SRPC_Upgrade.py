# -------------------------------
# CLEAN GLOBAL VERTICAL MARKERS
# -------------------------------

y_min = 0
y_max = 1

# Fault Start - RED
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

    fig.add_annotation(
        x=fault_start,
        y=1.02,
        xref="x",
        yref="paper",
        text="🔴 Fault Start",
        showarrow=False,
        font=dict(color="red", size=12)
    )

# Trip - BLUE
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

    fig.add_annotation(
        x=trip_start,
        y=1.02,
        xref="x",
        yref="paper",
        text="🔵 Trip",
        showarrow=False,
        font=dict(color="blue", size=12)
    )

# CB Open - GREEN
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

    fig.add_annotation(
        x=cb_open_time,
        y=1.02,
        xref="x",
        yref="paper",
        text="🟢 CB Open",
        showarrow=False,
        font=dict(color="green", size=12)
    )
