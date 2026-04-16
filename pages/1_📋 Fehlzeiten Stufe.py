import streamlit as st
from utils import (
    aggregate_class_data,
    apply_base_styles,
    col,
    filter_by_date,
    format_class_result,
    get_prepared_data,
    render_date_filter,
)

st.set_page_config(page_title="Fehlzeiten | Stufe", layout="wide")
apply_base_styles()

st.title("Fehlzeiten | Stufe")

prepared_df = get_prepared_data(exclude_names=True)
min_date = prepared_df[col("date")].min().date()
max_date = prepared_df[col("date")].max().date()

start_date, end_date = render_date_filter("class", min_date, max_date)
filtered_df = filter_by_date(prepared_df, start_date, end_date)
display_df = format_class_result(aggregate_class_data(filtered_df))

st.caption(f"Zeitraum: {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}")
st.subheader(f"Ergebnisse: {len(display_df)} SuS")
st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Datum von": st.column_config.DateColumn("Datum von", format="DD.MM.YYYY"),
        "Datum bis": st.column_config.DateColumn("Datum bis", format="DD.MM.YYYY"),
    },
)
