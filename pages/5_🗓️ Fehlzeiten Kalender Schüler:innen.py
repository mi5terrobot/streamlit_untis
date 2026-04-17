import pandas as pd
import streamlit as st
from utils import (
    apply_base_styles,
    build_absence_lookup,
    build_calendar_html,
    col,
    filter_by_date,
    filter_by_student,
    get_prepared_data,
    render_date_filter,
    render_student_filter,
    reset_date_state,
)

st.set_page_config(page_title="Fehlzeiten | Jahreskalender | Schüler:innen", layout="wide")
apply_base_styles()

st.title("Fehlzeiten | Jahreskalender | Schüler:innen")

prepared_df = get_prepared_data(exclude_names=True)
date_col = col("date")
hours_col = col("hours")

selected_student = render_student_filter(prepared_df, key="calendar_sus_student")
student_change_key = "calendar_sus_last_student"
student_df = filter_by_student(prepared_df, selected_student)

if student_df.empty:
    st.warning("Für diese Schüler*in wurden keine Fehlzeiten gefunden.")
    st.stop()

min_date = student_df[date_col].min().date()
max_date = student_df[date_col].max().date()
if st.session_state.get(student_change_key) != selected_student:
    reset_date_state("calendar_sus", min_date, max_date)
    st.session_state[student_change_key] = selected_student

start_date, end_date = render_date_filter("calendar_sus", min_date, max_date)
filtered_df = filter_by_date(student_df, start_date, end_date)
absence_lookup = build_absence_lookup(filtered_df, include_student_count=False)

st.markdown(build_calendar_html(start_date, end_date, absence_lookup, include_student_count=False), unsafe_allow_html=True)

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
summary_col1.metric("Tage im Zeitraum", f"{len(pd.date_range(start_date, end_date, freq='D'))}")
summary_col2.metric("Tage mit Fehlzeiten", f"{len(absence_lookup)}")

fehlstunden_gesamt = pd.to_numeric(filtered_df[hours_col], errors="coerce").fillna(0).sum()
tage_mit_fehlzeiten = len(absence_lookup)
fehlstunden_pro_tag = fehlstunden_gesamt / tage_mit_fehlzeiten if tage_mit_fehlzeiten > 0 else 0.0

summary_col3.metric("Fehlstunden gesamt", f"{fehlstunden_gesamt}")
summary_col4.metric("Fehlstunden pro Tag", f"{fehlstunden_pro_tag:.1f}")
