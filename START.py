import streamlit as st
from utils import DASHBOARD_TITLE, SCHOOL_YEAR_LABEL, load_data, setup_page, validate_columns

setup_page("EF | 25/26 | Fehlzeiten")
st.title(DASHBOARD_TITLE)
st.subheader(SCHOOL_YEAR_LABEL)

uploaded_file = st.file_uploader("Excel-Datei (.xls)", type=["xls"])

if not uploaded_file:
    st.info("Bitte eine .xls-Datei hochladen.")
    st.stop()

raw_df = load_data(uploaded_file)
validate_columns(raw_df)
st.session_state["raw_df"] = raw_df
st.success("Datei geladen. Du kannst jetzt links eine Unterseite auswählen.")
