import pandas as pd
import streamlit as st
from utils import (
    apply_date_filter,
    build_absence_lookup,
    build_calendar_html,
    col,
    get_prepared_data,
    render_student_filter,
    setup_page,
    show_date_caption,
)

setup_page("Fehlzeiten | Jahreskalender | Stufe")

df = get_prepared_data(exclude_names=True)
df, start_date, end_date = apply_date_filter(df, "calendar_class")
selected_student = render_student_filter(df, key="calendar_student", include_all=True)

if selected_student != "Alle":
    df = df[df[col("student_name")] == selected_student].copy()

absence_lookup = build_absence_lookup(df, include_student_count=selected_student == "Alle")

show_date_caption(start_date, end_date)
cols = st.columns(5)
cols[0].metric("Tage im Zeitraum", len(pd.date_range(start_date, end_date, freq="D")))
cols[1].metric("Tage mit Fehlzeiten", len(absence_lookup))
cols[2].metric("Schüler:innen", int(df[col("student_name")].dropna().nunique()))
cols[3].metric("Fehlstunden gesamt", f"{df[col('hours')].sum():.1f}")
cols[4].metric(
    "Ø Fehlstunden / Tag",
    f"{(df[col('hours')].sum() / len(absence_lookup)):.1f}" if absence_lookup else "0.0",
)

st.markdown(
    build_calendar_html(start_date, end_date, absence_lookup, include_student_count=selected_student == "Alle"),
    unsafe_allow_html=True,
)
