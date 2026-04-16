import altair as alt
import pandas as pd
import streamlit as st
from utils import (
    apply_base_styles,
    col,
    get_prepared_data,
    init_date_state,
    render_date_filter,
    filter_by_date,
)

st.set_page_config(page_title="Fehlzeiten | Monatsverlauf", layout="wide")
apply_base_styles()

st.title("Fehlzeiten | Monatsverlauf")

prepared_df = get_prepared_data(exclude_names=True)

if prepared_df.empty:
    st.warning("Keine Daten vorhanden.")
    st.stop()

min_date = prepared_df[col("date")].min().date()
max_date = prepared_df[col("date")].max().date()

init_date_state("monthly_trend", min_date, max_date)
start_date, end_date = render_date_filter("monthly_trend", min_date, max_date)

filtered_df = filter_by_date(prepared_df, start_date, end_date)

if filtered_df.empty:
    st.info("Im gewählten Zeitraum wurden keine Daten gefunden.")
    st.stop()

date_col = col("date")
hours_col = col("hours")
name_col = col("student_name")

analysis_df = filtered_df[[date_col, hours_col, name_col]].copy()
analysis_df[hours_col] = pd.to_numeric(analysis_df[hours_col], errors="coerce").fillna(0)
analysis_df["month"] = analysis_df[date_col].dt.to_period("M").dt.to_timestamp()

monthly_df = (
    analysis_df.groupby("month")
    .agg(
        total_absence_hours=(hours_col, "sum"),
        unique_absence_days=(date_col, "nunique"),
        unique_students=(name_col, "nunique"),
    )
    .reset_index()
)

all_months = pd.date_range(
    pd.Timestamp(start_date).replace(day=1),
    pd.Timestamp(end_date).replace(day=1),
    freq="MS",
)

monthly_df = (
    monthly_df.set_index("month")
    .reindex(all_months, fill_value=0)
    .rename_axis("month")
    .reset_index()
)

monthly_df["avg_absence_hours_per_day"] = (
    monthly_df["total_absence_hours"] / monthly_df["unique_absence_days"]
).replace([float("inf"), -float("inf")], 0).fillna(0)

monthly_df["Monat"] = monthly_df["month"].dt.strftime("%b %y")

display_df = monthly_df.rename(
    columns={
        "total_absence_hours": "Fehlzeiten gesamt",
        "unique_absence_days": "Tage mit Fehlzeiten",
        "unique_students": "SuS betroffen",
        "avg_absence_hours_per_day": "Ø / Tag",
    }
)[
    [
        "Monat",
        "Fehlzeiten gesamt",
        "Tage mit Fehlzeiten",
        "SuS betroffen",
        "Ø / Tag",
    ]
].copy()

display_df["Fehlzeiten gesamt"] = display_df["Fehlzeiten gesamt"].round(1)
display_df["Tage mit Fehlzeiten"] = display_df["Tage mit Fehlzeiten"].astype(int)
display_df["SuS betroffen"] = display_df["SuS betroffen"].astype(int)
display_df["Ø / Tag"] = display_df["Ø / Tag"].round(1)

max_avg_value = float(display_df["Ø / Tag"].max()) if not display_df.empty else 0.0

st.subheader("Verlauf des Schnitts pro Tag")

chart = (
    alt.Chart(monthly_df)
    .mark_line(point=True)
    .encode(
        x=alt.X(
            "Monat:N",
            title="Monat",
            sort=None,
            axis=alt.Axis(labelAngle=0, labelOverlap="greedy"),
        ),
        y=alt.Y(
            "avg_absence_hours_per_day:Q",
            title="Ø Fehlzeiten pro Tag",
        ),
        tooltip=[
            alt.Tooltip("Monat:N", title="Monat"),
            alt.Tooltip(
                "total_absence_hours:Q",
                title="Fehlzeiten gesamt",
                format=".1f",
            ),
            alt.Tooltip(
                "unique_absence_days:Q",
                title="Tage mit Fehlzeiten",
                format=".0f",
            ),
            alt.Tooltip(
                "unique_students:Q",
                title="SuS betroffen",
                format=".0f",
            ),
            alt.Tooltip(
                "avg_absence_hours_per_day:Q",
                title="Ø / Tag",
                format=".1f",
            ),
        ],
    )
    .properties(height=380)
)

st.altair_chart(chart, use_container_width=True)

st.subheader("Monatstabelle")

st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Monat": st.column_config.TextColumn("Monat"),
        "Fehlzeiten gesamt": st.column_config.NumberColumn(
            "Fehlzeiten gesamt",
            format="%.1f",
        ),
        "Tage mit Fehlzeiten": st.column_config.NumberColumn(
            "Tage",
            format="%d",
        ),
        "SuS betroffen": st.column_config.NumberColumn(
            "SuS",
            format="%d",
        ),
        "Ø / Tag": st.column_config.ProgressColumn(
            "Ø / Tag",
            min_value=0.0,
            max_value=max_avg_value if max_avg_value > 0 else 1.0,
            format="%.1f",
            width="medium",
        ),
    },
)