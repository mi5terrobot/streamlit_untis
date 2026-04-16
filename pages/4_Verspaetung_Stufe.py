import streamlit as st
from utils import (
    apply_base_styles,
    col,
    get_prepared_data,
    init_date_state,
    render_date_filter,
    filter_by_date,
    filter_tardiness_data,
    aggregate_tardiness_by_student,
    format_tardiness_result,
)

st.set_page_config(page_title="Verspätungen | Stufe", layout="wide")
apply_base_styles()

st.title("Verspätungen | Stufe")

prepared_df = get_prepared_data(
    exclude_names=True,
    exclude_absence_reasons=False,
)

tardiness_df = filter_tardiness_data(prepared_df)

if tardiness_df.empty:
    st.warning("Keine gültigen Verspätungen gefunden.")
    st.stop()

min_date = tardiness_df[col("date")].min().date()
max_date = tardiness_df[col("date")].max().date()

init_date_state("tardiness", min_date, max_date)
start_date, end_date = render_date_filter("tardiness", min_date, max_date)

filtered_df = filter_by_date(tardiness_df, start_date, end_date)
summary_df = aggregate_tardiness_by_student(filtered_df)

if summary_df.empty:
    st.info("Im gewählten Zeitraum wurden keine gültigen Verspätungen gefunden.")
    st.stop()

min_tardiness = int(summary_df["tardiness_count"].min())
max_tardiness = int(summary_df["tardiness_count"].max())

default_min_tardiness = max(min_tardiness, min(5, max_tardiness))

selected_min_tardiness = st.slider(
    "Mindestens so viele Verspätungen",
    min_value=min_tardiness,
    max_value=max_tardiness,
    value=default_min_tardiness,
)

display_df = format_tardiness_result(
    summary_df.loc[
        summary_df["tardiness_count"] >= selected_min_tardiness
    ].copy()
)

if display_df.empty:
    st.info("Keine SuS erfüllen den gewählten Filter.")
    st.stop()

st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    height=min(35 * (len(display_df) + 1) + 3, 600),
    column_config={
        "Name": st.column_config.TextColumn(
            "Name",
            width="medium",
        ),
        "Anzahl": st.column_config.ProgressColumn(
            "Anzahl Verspätungen",
            min_value=0,
            max_value=max_tardiness,
            format="%d",
            width="large",
        ),
        "Ø Minuten": st.column_config.NumberColumn(
            "Ø Minuten",
            format="%.1f",
            width="small",
        ),
    },
)
