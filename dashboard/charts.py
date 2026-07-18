import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _is_valid(val):
    try:
        return val is not None and not math.isnan(float(val)) and not math.isinf(float(val))
    except (TypeError, ValueError):
        return False


def _template(dark):
    return "plotly_dark" if dark else "plotly_white"


def build_overview_chart(data, symbol, ema_short, ema_long, dark=False):
    """Candlestick chart with short/long EMA overlays for the Overview tab."""
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'], name="Price"
    ))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA_1'], line=dict(color='orange', width=1), name=f'EMA {ema_short}'))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA_2'], line=dict(color='blue', width=1), name=f'EMA {ema_long}'))

    fig.update_layout(
        title=f"{symbol} Price Action",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template=_template(dark),
        height=600,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig


def build_multi_indicator_chart(data, selected_indicators, ema_short=20, ema_long=50, dark=False):
    """Candlestick chart with optional overlays and oscillator subplot rows."""
    rows = 1
    if "RSI" in selected_indicators: rows += 1
    if "MACD" in selected_indicators: rows += 1
    if "ADX" in selected_indicators: rows += 1

    row_heights = [0.5] + [0.15] * (rows - 1)

    fig_multi = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=row_heights
    )

    fig_multi.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'], name="Price"
    ), row=1, col=1)

    if "EMAs (20, 50, 100, 200)" in selected_indicators:
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_1'], line=dict(color='orange', width=1.5), name=f"EMA {ema_short}"), row=1, col=1)
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_2'], line=dict(color='blue', width=1.5), name=f"EMA {ema_long}"), row=1, col=1)
        # EMA_50/EMA_100/EMA_200 are fixed spans; skip one if the adjustable
        # Short/Long EMA Span already lands on it, to avoid a duplicate, identical line.
        if ema_short != 50 and ema_long != 50:
            fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_50'], line=dict(color='deepskyblue', width=1.5), name="EMA 50"), row=1, col=1)
        if ema_short != 100 and ema_long != 100:
            fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_100'], line=dict(color='purple', width=1.5), name="EMA 100"), row=1, col=1)
        if ema_short != 200 and ema_long != 200:
            fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_200'], line=dict(color='gray', width=1.5), name="EMA 200"), row=1, col=1)

    if "Bollinger Bands" in selected_indicators:
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], line=dict(color='rgba(173, 216, 230, 0.4)', width=1), name="BB Upper"), row=1, col=1)
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], line=dict(color='rgba(173, 216, 230, 0.4)', width=1), fill='tonexty', name="BB Lower"), row=1, col=1)

    if "Support/Resistance" in selected_indicators:
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['Resistance'], line=dict(color='red', width=1, dash='dash'), name="20D Res"), row=1, col=1)
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['Support'], line=dict(color='green', width=1, dash='dash'), name="20D Sup"), row=1, col=1)

    current_row = 2
    if "RSI" in selected_indicators:
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='magenta', width=1.5), name="RSI"), row=current_row, col=1)
        fig_multi.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
        fig_multi.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
        fig_multi.update_yaxes(title_text="RSI", row=current_row, col=1)
        current_row += 1

    if "MACD" in selected_indicators:
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='cyan', width=1), name="MACD"), row=current_row, col=1)
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['Signal_Line'], line=dict(color='orange', width=1), name="Signal"), row=current_row, col=1)
        hist_colors = ['green' if x >= 0 else 'red' for x in data['MACD_Hist']]
        fig_multi.add_trace(go.Bar(x=data.index, y=data['MACD_Hist'], marker_color=hist_colors, name="Histogram"), row=current_row, col=1)
        fig_multi.update_yaxes(title_text="MACD", row=current_row, col=1)
        current_row += 1

    if "ADX" in selected_indicators:
        fig_multi.add_trace(go.Scatter(x=data.index, y=data['ADX'], line=dict(color='yellow', width=1.5), name="ADX"), row=current_row, col=1)
        fig_multi.add_hline(y=25, line_dash="dash", line_color="gray", row=current_row, col=1)
        fig_multi.update_yaxes(title_text="ADX", row=current_row, col=1)
        current_row += 1

    fig_multi.update_layout(
        height=400 + (rows * 150),
        template=_template(dark),
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig_multi


def build_volatility_scale_figure(lowest_dd, avg_dd, avg_du, highest_du, dark=False):
    """Build the intraday drawdown/drawup scale bar figure.

    Returns None if any input is not a finite number, so the caller can
    decide how to warn the user instead of this function touching Streamlit.
    """
    if not all(_is_valid(v) for v in [lowest_dd, avg_dd, avg_du, highest_du]):
        return None

    lowest_dd = float(lowest_dd)
    avg_dd = float(avg_dd)
    avg_du = float(avg_du)
    highest_du = float(highest_du)

    fig = go.Figure()

    # Red segment (drawdown zone): width = abs(lowest_dd), starts at lowest_dd
    fig.add_trace(go.Bar(
        x=[abs(lowest_dd)],
        y=[""],
        base=[lowest_dd],
        orientation="h",
        marker=dict(
            color="rgba(204,34,34,0.85)",
            line=dict(width=0),
        ),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Green segment (drawup zone): width = highest_du, starts at 0
    fig.add_trace(go.Bar(
        x=[highest_du],
        y=[""],
        base=[0],
        orientation="h",
        marker=dict(
            color="rgba(31,173,74,0.85)",
            line=dict(width=0),
        ),
        showlegend=False,
        hoverinfo="skip",
    ))

    zero_line_color = "#ffffff" if dark else "#333333"
    label_color = "#ffffff" if dark else "#000000"

    markers = [
        (lowest_dd, "#ff3333"),
        (avg_dd, "#ff9999"),
        (0.0, zero_line_color),
        (avg_du, "#99ffb0"),
        (highest_du, "#1fad4a"),
    ]
    for x_val, color in markers:
        fig.add_vline(
            x=x_val,
            line=dict(color=color, width=2, dash="dot"),
        )

    label_data = [
        (lowest_dd, label_color, f"Lowest DD<br><b>{lowest_dd:.2f}%</b>"),
        (avg_dd, label_color, f"Avg DD<br><b>{avg_dd:.2f}%</b>"),
        (0.0, label_color, "Open<br><b>0.00%</b>"),
        (avg_du, label_color, f"Avg DU<br><b>+{avg_du:.2f}%</b>"),
        (highest_du, label_color, f"Highest DU<br><b>+{highest_du:.2f}%</b>"),
    ]

    for x_val, color, text in label_data:
        fig.add_annotation(
            x=x_val,
            y=0,
            yref="paper",
            text=text,
            showarrow=False,
            font=dict(color=color, size=11),
            align="center",
            yanchor="top",
            yshift=-8,
        )

    grid_color = "rgba(255,255,255,0.3)" if dark else "rgba(0,0,0,0.3)"
    tick_color = "rgba(255,255,255,0.5)" if dark else "rgba(0,0,0,0.6)"

    padding = abs(highest_du - lowest_dd) * 0.05
    fig.update_layout(
        template=_template(dark),
        barmode="overlay",
        height=110,
        margin=dict(l=0, r=0, t=10, b=60),
        xaxis=dict(
            range=[lowest_dd - padding, highest_du + padding],
            showgrid=False,
            zeroline=True,
            zerolinecolor=grid_color,
            zerolinewidth=2,
            tickformat=".1f",
            ticksuffix="%",
            tickfont=dict(color=tick_color, size=10),
        ),
        yaxis=dict(visible=False),
    )

    return fig
