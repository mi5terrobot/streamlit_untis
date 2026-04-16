import altair as alt
import streamlit as st
from utils import (
    aggregate_student_by_date,
    apply_base_styles,
    build_monthly_absence_table,
    calculate_student_metrics,
    col,
    filter_by_date,
    filter_by_student,
    get_prepared_data,
    render_date_filter,
    render_student_filter,
    reset_date_state,
)

st.set_page_config(page_title="Fehlzeiten | Schüler:innen", layout="wide")
apply_base_styles()

st.title("Fehlzeiten | Schüler:innen")

prepared_df = get_prepared_data(exclude_names=True)
selected_student = render_student_filter(prepared_df, key="student_page_select")
student_df = filter_by_student(prepared_df, selected_student)

if student_df.empty:
    st.warning("Für diese Schüler*in sind keine Daten vorhanden.")
    st.stop()

current_student_key = "student_current_name"
min_date = student_df[col("date")].min().date()
max_date = student_df[col("date")].max().date()
if st.session_state.get(current_student_key) != selected_student:
    st.session_state[current_student_key] = selected_student
    reset_date_state("student", min_date, max_date)

start_date, end_date = render_date_filter("student", min_date, max_date)
filtered_df = filter_by_date(student_df, start_date, end_date)
metrics = calculate_student_metrics(filtered_df)

metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
metric_col1.metric("Anzahl Tage", f"{metrics['days_count']:.0f}")
metric_col2.metric("Fehlstunden gesamt", f"{metrics['total_hours']:.0f}")
metric_col3.metric("Schnitt", f"{metrics['avg_hours_per_day']:.1f}")
metric_col4.metric("Fehlstunden entsch.", f"{metrics['excused_hours']:.0f}")
metric_col5.metric("Fehlstunden offen", f"{metrics['open_hours']:.0f}")

st.subheader(selected_student)
result_df = aggregate_student_by_date(filtered_df)
st.dataframe(
    result_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Datum": st.column_config.DateColumn("Datum", format="DD.MM.YYYY"),
    },
)

st.divider()
st.subheader("Monatsverlauf")
if filtered_df.empty:
    st.info("Im gewählten Zeitraum wurden keine Daten gefunden.")
    st.stop()

monthly_df, display_df, max_avg_value = build_monthly_absence_table(filtered_df, include_students=False)
st.caption(f"Zeitraum: {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}")
st.markdown("**Verlauf des Schnitts pro Tag**")

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
            alt.Tooltip("avg_absence_hours_per_day:Q", title="Ø / Tag", format=".1f"),
        ],
    )
    .properties(height=380)
)

st.altair_chart(chart, use_container_width=True)
st.markdown("**Monatstabelle**")
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
        "Ø / Tag": st.column_config.ProgressColumn(
            "Ø / Tag",
            min_value=0.0,
            max_value=max_avg_value if max_avg_value > 0 else 1.0,
            format="%.1f",
            width="medium",
        ),
        "Fehlzeiten gesamt": st.column_config.NumberColumn("Fehlzeiten gesamt", format="%.1f"),
        "Tage mit Fehlzeiten": st.column_config.NumberColumn("Tage", format="%d"),
    },
)
