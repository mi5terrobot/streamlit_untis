import pandas as pd
import streamlit as st
from utils import (
    apply_base_styles,
    build_absence_lookup,
    build_calendar_html,
    col,
    filter_by_date,
    get_prepared_data,
    render_date_filter,
)

st.set_page_config(page_title="Fehlzeiten | Jahreskalender | Stufe", layout="wide")
apply_base_styles()

st.title("Fehlzeiten | Jahreskalender | Stufe")

prepared_df = get_prepared_data(exclude_names=True)
date_col = col("date")
hours_col = col("hours")

min_date = prepared_df[date_col].min().date()
max_date = prepared_df[date_col].max().date()
start_date, end_date = render_date_filter("calendar_class", min_date, max_date)

filtered_df = filter_by_date(prepared_df, start_date, end_date)
absence_lookup = build_absence_lookup(filtered_df, include_student_count=True)

st.markdown(build_calendar_html(start_date, end_date, absence_lookup, include_student_count=True), unsafe_allow_html=True)

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
summary_col1.metric("Tage im Zeitraum", f"{len(pd.date_range(start_date, end_date, freq='D'))}")
summary_col2.metric("Tage mit Fehlzeiten", f"{len(absence_lookup)}")

fehlstunden_gesamt = pd.to_numeric(filtered_df[hours_col], errors="coerce").fillna(0).sum()
tage_mit_fehlzeiten = len(absence_lookup)
fehlstunden_pro_tag = fehlstunden_gesamt / tage_mit_fehlzeiten if tage_mit_fehlzeiten > 0 else 0.0

summary_col3.metric("Fehlstunden gesamt", f"{fehlstunden_gesamt:.1f}")
summary_col4.metric("Fehlstunden pro Tag", f"{fehlstunden_pro_tag:.1f}")
