import streamlit as st
from utils import (
    apply_base_styles,
    col,
    format_class_result,
    get_prepared_data,
    init_date_state,
    render_date_filter,
    aggregate_class_data,
    filter_by_date,
)

st.set_page_config(page_title="Fehlstunden | Stufe", layout="wide")
apply_base_styles()

st.title("Fehlstunden | Stufe")

prepared_df = get_prepared_data(exclude_names=True)

min_date = prepared_df[col("date")].min().date()
max_date = prepared_df[col("date")].max().date()

init_date_state("class", min_date, max_date)
start_date, end_date = render_date_filter("class", min_date, max_date)

filtered_df = filter_by_date(prepared_df, start_date, end_date)
summary_df = aggregate_class_data(filtered_df)
display_df = format_class_result(summary_df)

st.subheader(f"Ergebnisse: {len(display_df)} SuS")
st.dataframe(display_df, hide_index=True, use_container_width=True)
