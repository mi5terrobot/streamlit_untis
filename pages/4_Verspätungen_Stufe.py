import streamlit as st
from utils import (
    aggregate_tardiness_by_student,
    apply_date_filter,
    filter_tardiness_data,
    format_tardiness_result,
    get_prepared_data,
    setup_page,
    show_date_caption,
)

setup_page("Verspätungen | Stufe")

df = get_prepared_data(exclude_names=True, exclude_absence_reasons=False)
df = filter_tardiness_data(df)

if df.empty:
    st.warning("Keine gültigen Verspätungen gefunden.")
    st.stop()

df, start_date, end_date = apply_date_filter(df, "tardiness")
summary_df = aggregate_tardiness_by_student(df)

if summary_df.empty:
    st.info("Im gewählten Zeitraum wurden keine gültigen Verspätungen gefunden.")
    st.stop()

min_tardiness = int(summary_df["tardiness_count"].min())
max_tardiness = int(summary_df["tardiness_count"].max())
threshold = st.slider(
    "Mindestens so viele Verspätungen",
    min_value=min_tardiness,
    max_value=max_tardiness,
    value=max(min_tardiness, min(5, max_tardiness)),
)

display_df = format_tardiness_result(summary_df[summary_df["tardiness_count"] >= threshold].copy())

if display_df.empty:
    st.info("Keine SuS erfüllen den gewählten Filter.")
    st.stop()

show_date_caption(start_date, end_date)
st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Anzahl": st.column_config.ProgressColumn(
            "Anzahl Verspätungen",
            min_value=0,
            max_value=max_tardiness if max_tardiness > 0 else 1,
            format="%d",
        ),
        "Ø Minuten": st.column_config.NumberColumn("Ø Minuten", format="%.1f"),
    },
)
