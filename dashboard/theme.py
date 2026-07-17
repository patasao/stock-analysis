import streamlit as st


def is_dark_theme():
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False  # matches the app's light default
