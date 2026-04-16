import streamlit as st
from utils import (
    apply_base_styles,
    col,
    get_prepared_data,
    render_student_filter,
    filter_by_student,
    init_date_state,
    reset_date_state,
    render_date_filter,
    filter_by_date,
    calculate_student_metrics,
    aggregate_student_by_date,
)

st.set_page_config(page_title="Fehlstunden | SuS", layout="wide")
apply_base_styles()

st.title("Fehlstunden | Schüler:innen")

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

init_date_state("student", min_date, max_date)
start_date, end_date = render_date_filter("student", min_date, max_date)

filtered_df = filter_by_date(student_df, start_date, end_date)
metrics = calculate_student_metrics(filtered_df)

metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
metric_col1.metric("Anzahl Tage", f"{metrics['days_count']:.0f}")
metric_col2.metric("Fehlstunden gesamt", f"{metrics['total_hours']:.0f}")
metric_col3.metric("Schnitt", f"{metrics['avg_hours_per_day']:.1f}")
metric_col4.metric("Fehlstunden entsch.", f"{metrics['excused_hours']:.0f}")
metric_col5.metric("Fehlstunden offen", f"{metrics['open_hours']:.0f}")

result_df = aggregate_student_by_date(filtered_df)

st.subheader(selected_student)
st.dataframe(result_df, hide_index=True, use_container_width=True)
