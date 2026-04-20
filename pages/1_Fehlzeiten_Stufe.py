import altair as alt
import streamlit as st
from utils import (
    aggregate_class_data,
    apply_date_filter,
    build_monthly_trend_data,
    calculate_class_metrics,
    format_class_result,
    get_prepared_data,
    setup_page,
    show_date_caption,
)

setup_page("Fehlzeiten | Stufe")

df = get_prepared_data(exclude_names=True)
df, start_date, end_date = apply_date_filter(df, "class")
summary_df = aggregate_class_data(df)
display_df = format_class_result(summary_df)
metrics = calculate_class_metrics(summary_df)

show_date_caption(start_date, end_date)

cols = st.columns(5)
cols[0].metric("Anzahl SuS", metrics["student_count"])
cols[1].metric("Ø Tage je SuS", f"{metrics['avg_days']:.1f}")
cols[2].metric("Ø Std./Tag", f"{metrics['avg_hours_per_day']:.1f}")
cols[3].metric("Median Tage", f"{metrics['median_days']:.1f}")
cols[4].metric(
    "SuS mit offenen Fehlzeiten",
    metrics["students_with_open_absences"],
    f"{metrics['open_absence_share']:.1f}%",
)

st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Datum von": st.column_config.DateColumn("Datum von", format="DD.MM.YYYY"),
        "Datum bis": st.column_config.DateColumn("Datum bis", format="DD.MM.YYYY"),
    },
)

st.divider()
st.subheader("Monatsverlauf")
chart_df, max_total = build_monthly_trend_data(df)

chart = (
    alt.Chart(chart_df)
    .mark_bar()
    .encode(
        x=alt.X("Monat:N", title="Monat", sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Fehlzeiten gesamt:Q", title="Fehlstunden gesamt"),
        tooltip=[
            alt.Tooltip("Monat:N"),
            alt.Tooltip("Fehlzeiten gesamt:Q", format=".1f"),
            alt.Tooltip("Tage mit Fehlzeiten:Q", format=".0f"),
            alt.Tooltip("SuS betroffen:Q", format=".0f"),
            alt.Tooltip("Ø / Tag:Q", format=".1f"),
        ],
    )
    .properties(height=360)
)

st.altair_chart(chart, use_container_width=True)
st.dataframe(
    chart_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Fehlzeiten gesamt": st.column_config.ProgressColumn(
            "Fehlzeiten gesamt",
            min_value=0.0,
            max_value=max_total if max_total > 0 else 1.0,
            format="%.1f",
        )
    },
)
