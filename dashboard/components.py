import streamlit as st

from dashboard.help_text import TECH_HELP

# Background/text color pair per tone. Chosen so text stays legible on its
# own background instead of the old hardcoded black-on-everything approach.
TONE_COLORS = {
    "bullish_strong": ("#1FAD4A", "#FFFFFF"),
    "bullish": ("#3DD16F", "#0B1F13"),
    "moderate": ("#F2A93B", "#1F1300"),
    "weak": ("#F2D93B", "#1F1A00"),
    "bearish": ("#E5484D", "#FFFFFF"),
    "neutral": ("#5B6270", "#FFFFFF"),
}

# Single source of truth for entry_level / exit_level -> tone, replacing the
# three separate ad-hoc color schemes that used to live in app.py.
ENTRY_LEVEL_TONE = {
    "A+": "bullish_strong",
    "A": "bullish",
    "B": "moderate",
    "C": "weak",
    "Avoid": "bearish",
}

EXIT_LEVEL_TONE = {
    "Hold": "neutral",
    "CAUTION": "moderate",
    "SELL / REDUCE": "bearish",
}

# st.badge only accepts a fixed palette (blue/green/orange/red/violet/gray/primary),
# so tones map down to the closest native badge color for the small tab1 teaser.
TONE_BADGE_COLOR = {
    "bullish_strong": "green",
    "bullish": "green",
    "moderate": "orange",
    "weak": "orange",
    "bearish": "red",
    "neutral": "gray",
}


def score_banner(headline, subtext, tone):
    """Render a headline-style colored banner (buy/sell score, growth-scanner card)."""
    bg, fg = TONE_COLORS.get(tone, TONE_COLORS["neutral"])
    st.markdown(
        f"""
        <div style="background-color: {bg}; padding: 16px; border-radius: 10px; text-align: center; color: {fg};">
            <h2 style="margin: 0;">{headline}</h2>
            <p style="margin: 0; font-weight: bold;">{subtext}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def condition_checkbox(label, passed, value_text, help_key):
    st.checkbox(
        f"{label} ({value_text})",
        value=bool(passed),
        disabled=True,
        help=TECH_HELP[help_key],
    )


def quality_warnings(warnings):
    for warning in warnings:
        st.warning(warning)
