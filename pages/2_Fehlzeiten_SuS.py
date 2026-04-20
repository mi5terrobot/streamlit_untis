import altair as alt
import streamlit as st
from utils import (
    aggregate_student_by_date,
    apply_date_filter,
    build_monthly_absence_table,
    build_student_vs_class_monthly_chart_data,
    calculate_student_metrics,
    filter_by_date,
    filter_by_student,
    get_prepared_data,
    render_student_filter,
    setup_page,
    show_date_caption,
)

setup_page("Fehlzeiten | Schüler:innen")

all_df = get_prepared_data(exclude_names=True)
selected_student = render_student_filter(all_df, key="student_page")
student_df = filter_by_student(all_df, selected_student)
student_df, start_date, end_date = apply_date_filter(student_df, f"student_{selected_student}")
class_df = filter_by_date(all_df, start_date, end_date)

metrics = calculate_student_metrics(student_df)
show_date_caption(start_date, end_date)

cols = st.columns(5)
cols[0].metric("Anzahl Tage", metrics["days_count"])
cols[1].metric("Fehlstunden gesamt", f"{metrics['total_hours']:.0f}")
cols[2].metric("Ø / Tag", f"{metrics['avg_hours_per_day']:.1f}")
cols[3].metric("entsch.", f"{metrics['excused_hours']:.0f}")
cols[4].metric("offen", f"{metrics['open_hours']:.0f}")

st.subheader(selected_student)
st.dataframe(
    aggregate_student_by_date(student_df),
    hide_index=True,
    use_container_width=True,
    column_config={"Datum": st.column_config.DateColumn("Datum", format="DD.MM.YYYY")},
)

st.divider()
st.subheader("Monatsverlauf")
_, display_df, max_avg_value = build_monthly_absence_table(student_df, include_students=False)
student_chart_df, class_chart_df = build_student_vs_class_monthly_chart_data(student_df, class_df, selected_student)

student_line = (
    alt.Chart(student_chart_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("Monat:N", title="Monat", sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Wert:Q", title="Ø Fehlstunden pro Tag"),
        tooltip=[
            alt.Tooltip("Monat:N"),
            alt.Tooltip("Reihe:N"),
            alt.Tooltip("Wert:Q", title="Ø / Tag", format=".1f"),
            alt.Tooltip("Fehlzeiten gesamt:Q", format=".1f"),
            alt.Tooltip("Tage mit Fehlzeiten:Q", format=".0f"),
        ],
    )
)

class_line = (
    alt.Chart(class_chart_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("Monat:N", title="Monat", sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Wert:Q", title="Ø Fehlstunden pro Tag"),
        strokeDash=alt.value([6, 4]),
        tooltip=[
            alt.Tooltip("Monat:N"),
            alt.Tooltip("Reihe:N"),
            alt.Tooltip("Wert:Q", title="Ø / Tag", format=".1f"),
            alt.Tooltip("Fehlzeiten gesamt:Q", format=".1f"),
            alt.Tooltip("Tage mit Fehlzeiten:Q", format=".1f"),
        ],
    )
)

st.altair_chart(alt.layer(student_line, class_line).properties(height=360), use_container_width=True)
st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Ø / Tag": st.column_config.ProgressColumn(
            "Ø / Tag",
            min_value=0.0,
            max_value=max_avg_value if max_avg_value > 0 else 1.0,
            format="%.1f",
        )
    },
)
