import streamlit as st
from utils import (
    DASHBOARD_TITLE,
    SCHOOL_YEAR_LABEL,
    apply_base_styles,
    load_data,
    validate_columns,
)

st.set_page_config(page_title="EF | 25/26 | Fehlzeiten", layout="wide")
apply_base_styles()

st.title(DASHBOARD_TITLE)
st.subheader(SCHOOL_YEAR_LABEL)

uploaded_file = st.file_uploader(
    "Bitte eine Excel-Datei (.xls) hochladen",
    type=["xls"],
)

if uploaded_file is not None:
    raw_df = load_data(uploaded_file)
    validate_columns(raw_df)
    st.session_state["raw_df"] = raw_df
    st.success("Datei geladen. Du kannst jetzt links eine Unterseite auswählen.")
else:
    st.info("Bitte lade eine .xls-Datei hoch, um die Analyse zu starten.")
