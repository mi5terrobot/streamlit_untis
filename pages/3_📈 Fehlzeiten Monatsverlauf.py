import altair as alt
import streamlit as st
from utils import (
    apply_base_styles,
    build_monthly_absence_table,
    col,
    filter_by_date,
    get_prepared_data,
    render_date_filter,
)

st.set_page_config(page_title="Fehlzeiten | Monatsverlauf | Stufe", layout="wide")
apply_base_styles()

st.title("Fehlzeiten | Monatsverlauf | Stufe")

prepared_df = get_prepared_data(exclude_names=True)
if prepared_df.empty:
    st.warning("Keine Daten vorhanden.")
    st.stop()

min_date = prepared_df[col("date")].min().date()
max_date = prepared_df[col("date")].max().date()
start_date, end_date = render_date_filter("monthly_trend_class", min_date, max_date)
filtered_df = filter_by_date(prepared_df, start_date, end_date)

if filtered_df.empty:
    st.info("Im gewählten Zeitraum wurden keine Daten gefunden.")
    st.stop()

monthly_df, display_df, max_avg_value = build_monthly_absence_table(filtered_df, include_students=True)
st.caption(f"Zeitraum: {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}")
st.subheader("Verlauf des Schnitts pro Tag")

chart = (
    alt.Chart(monthly_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("Monat:N", title="Monat", sort=None, axis=alt.Axis(labelAngle=0, labelOverlap="greedy")),
        y=alt.Y("avg_absence_hours_per_day:Q", title="Ø Fehlzeiten pro Tag"),
        tooltip=[
            alt.Tooltip("Monat:N", title="Monat"),
            alt.Tooltip("total_absence_hours:Q", title="Fehlzeiten gesamt", format=".1f"),
            alt.Tooltip("unique_absence_days:Q", title="Tage mit Fehlzeiten", format=".0f"),
            alt.Tooltip("unique_students:Q", title="SuS betroffen", format=".0f"),
            alt.Tooltip("avg_absence_hours_per_day:Q", title="Ø / Tag", format=".1f"),
        ],
    )
    .properties(height=380)
)

st.altair_chart(chart, use_container_width=True)
st.subheader("Monatstabelle")
row_height = 35
header_height = 38
max_table_height = 800
table_height = min(len(display_df) * row_height + header_height, max_table_height)

st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    height=table_height,
    column_config={
        "Monat": st.column_config.TextColumn("Monat"),
        "Fehlzeiten gesamt": st.column_config.NumberColumn("Fehlzeiten gesamt", format="%.1f"),
        "Tage mit Fehlzeiten": st.column_config.NumberColumn("Tage", format="%d"),
        "SuS betroffen": st.column_config.NumberColumn("SuS", format="%d"),
        "Ø / Tag": st.column_config.ProgressColumn(
            "Ø / Tag",
            min_value=0.0,
            max_value=max_avg_value if max_avg_value > 0 else 1.0,
            format="%.1f",
            width="medium",
        ),
    },
)
