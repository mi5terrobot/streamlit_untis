from __future__ import annotations

import calendar
from datetime import date
from html import escape
from io import BytesIO

import pandas as pd
import streamlit as st

# =========================================================
# KONFIGURATION
# =========================================================

DASHBOARD_TITLE = "Fehlzeiten & Verspätungen"
SCHOOL_YEAR_LABEL = "EF (Schuljahr: 2025/2026)"

DATE_INPUT_FORMAT = "%d.%m.%y"
DATE_PICKER_INPUT_FORMAT = "DD.MM.YYYY"
DATE_OUTPUT_FORMAT = "%d.%m.%Y"

COLUMN_KEYS = {
    "student_name": "Schüler*innen",
    "date": "Datum",
    "absence_reason": "Abwesenheitsgrund",
    "hours": "Fehlstd.",
    "minutes": "Fehlmin.",
    "status": "Status",
}

STATUS_VALUES = {
    "excused": "entsch.",
    "open": "offen",
}

CLASS_TABLE_LABELS = {
    "student_name": "Name",
    "unique_days": "Tage",
    "total_hours": "Std. gesamt",
    "avg_hours_per_day": "Std./Tag",
    "excused_hours": "entschuldigt",
    "open_hours": "offen",
    "open_percent": "offen %",
    "date_from": "Datum von",
    "date_to": "Datum bis",
}

STUDENT_DAILY_TABLE_LABELS = {
    "date": "Datum",
    "excused_hours": "Fehlstunden entsch.",
    "open_hours": "Fehlstunden offen",
    "total_hours": "Fehlstunden gesamt",
}

TARDINESS_TABLE_LABELS = {
    "student_name": "Name",
    "tardiness_count": "Anzahl",
    "avg_minutes_per_tardy": "Ø Minuten",
}

REQUIRED_COLUMNS = [
    COLUMN_KEYS["student_name"],
    COLUMN_KEYS["date"],
    COLUMN_KEYS["absence_reason"],
    COLUMN_KEYS["hours"],
    COLUMN_KEYS["status"],
]

EXCLUDED_ABSENCE_REASONS = {
    "verspätung",
    "beurlaubung",
    "schulische veranstaltung",
    "auslandsaufenthalt",
}

EXCLUDED_NAMES = {
    "dahmen michael",
    "phiri sarah",
    "krauth valentin",
    "gerdes juri",
}

PRESET_ORDER = [
    "Heute",
    "Letzte Woche",
    "Letzte 2 Wochen",
    "Letzter Monat",
    "1. Halbjahr",
    "2. Halbjahr",
    "SJ 2025/2026",
]

PRESET_DATE_RANGES = {
    "Heute": {"type": "relative", "days": 0},
    "Letzte Woche": {"type": "relative", "days": 6},
    "Letzte 2 Wochen": {"type": "relative", "days": 13},
    "Letzter Monat": {"type": "relative", "days": 29},
    "1. Halbjahr": {"type": "fixed", "start": "01.08.2025", "end": "07.02.2026"},
    "2. Halbjahr": {"type": "fixed", "start": "08.02.2026", "end": "31.07.2026"},
    "SJ 2025/2026": {"type": "fixed", "start": "01.08.2025", "end": "31.07.2026"},
}

MONTH_LABELS_DE = {
    1: "Jan",
    2: "Feb",
    3: "Mär",
    4: "Apr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Dez",
}

WEEKDAY_LABELS_DE = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag",
}

NRW_HOLIDAY_RANGES = [
    (date(2025, 7, 14), date(2025, 8, 26), "Sommerferien"),
    (date(2025, 10, 13), date(2025, 10, 25), "Herbstferien"),
    (date(2025, 12, 22), date(2026, 1, 6), "Weihnachtsferien"),
    (date(2026, 3, 30), date(2026, 4, 11), "Osterferien"),
    (date(2026, 5, 26), date(2026, 5, 26), "Pfingstferien"),
]


# =========================================================
# ALLGEMEINE HILFSFUNKTIONEN
# =========================================================


def col(key: str) -> str:
    return COLUMN_KEYS[key]


def normalize_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def parse_fixed_date(value: str) -> date:
    return pd.to_datetime(value, format=DATE_OUTPUT_FORMAT).date()


def today_date() -> date:
    return pd.Timestamp.today().date()


def format_month_label(ts: pd.Timestamp) -> str:
    return f"{MONTH_LABELS_DE[ts.month]} {str(ts.year)[-2:]}"


def format_date_range(start_date: date, end_date: date) -> str:
    return f"{start_date.strftime(DATE_OUTPUT_FORMAT)} bis {end_date.strftime(DATE_OUTPUT_FORMAT)}"


def format_day_with_weekday(current_date: date) -> str:
    weekday_name = WEEKDAY_LABELS_DE[current_date.weekday()]
    return f"{weekday_name}, {current_date.strftime(DATE_OUTPUT_FORMAT)}"


def apply_base_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 12px;
            padding: 0.3rem 0.5rem;
            background: rgba(255, 255, 255, 0.02);
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def setup_page(title: str) -> None:
    st.set_page_config(page_title=title, layout="wide")
    apply_base_styles()
    st.title(title)


def show_date_caption(start_date: date, end_date: date) -> None:
    st.caption(f"Zeitraum: {format_date_range(start_date, end_date)}")


# =========================================================
# DATENLADEN / VALIDIEREN / AUFBEREITEN
# =========================================================


@st.cache_data(show_spinner=False)
def load_data_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(BytesIO(file_bytes), engine="xlrd")



def load_data(uploaded_file) -> pd.DataFrame:
    try:
        return load_data_from_bytes(uploaded_file.getvalue())
    except Exception as exc:
        st.error(f"Die Excel-Datei konnte nicht geladen werden: {exc}")
        st.stop()



def validate_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        st.error("Folgende benötigte Spalten fehlen: " + ", ".join(missing_columns))
        st.stop()



def prepare_data(
    df: pd.DataFrame,
    *,
    exclude_names: bool = True,
    exclude_absence_reasons: bool = True,
) -> pd.DataFrame:
    prepared_df = df.copy()

    if exclude_absence_reasons:
        prepared_df = prepared_df[
            ~normalize_text(prepared_df[col("absence_reason")]).isin(EXCLUDED_ABSENCE_REASONS)
        ].copy()

    if exclude_names:
        prepared_df = prepared_df[
            ~normalize_text(prepared_df[col("student_name")]).isin(EXCLUDED_NAMES)
        ].copy()

    prepared_df[col("status")] = normalize_text(prepared_df[col("status")])
    prepared_df[col("hours")] = pd.to_numeric(prepared_df[col("hours")], errors="coerce").fillna(0)
    prepared_df[col("minutes")] = pd.to_numeric(prepared_df.get(col("minutes"), 0), errors="coerce").fillna(0)
    prepared_df[col("date")] = pd.to_datetime(
        prepared_df[col("date")],
        format=DATE_INPUT_FORMAT,
        errors="coerce",
    )
    prepared_df = prepared_df.dropna(subset=[col("date")]).copy()

    if prepared_df.empty:
        st.warning("Nach dem Filtern sind keine gültigen Daten mehr vorhanden.")
        st.stop()

    return prepared_df



def get_prepared_data(
    *,
    exclude_names: bool = True,
    exclude_absence_reasons: bool = True,
) -> pd.DataFrame:
    raw_df = st.session_state.get("raw_df")
    if raw_df is None:
        st.warning("Bitte zuerst auf der Startseite eine .xls-Datei hochladen.")
        st.stop()

    return prepare_data(
        raw_df,
        exclude_names=exclude_names,
        exclude_absence_reasons=exclude_absence_reasons,
    )


# =========================================================
# ZEITRAUM-FILTER
# =========================================================


def get_preset_range(name: str) -> tuple[date, date]:
    preset = PRESET_DATE_RANGES[name]
    if preset["type"] == "relative":
        end_date = today_date()
        start_date = end_date - pd.Timedelta(days=preset["days"])
        return start_date, end_date
    return parse_fixed_date(preset["start"]), parse_fixed_date(preset["end"])



def clamp_date_range(start_date: date, end_date: date, min_date: date, max_date: date) -> tuple[date, date]:
    start_date = max(min_date, min(start_date, max_date))
    end_date = max(min_date, min(end_date, max_date))
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date



def render_date_filter(key: str, min_date: date, max_date: date) -> tuple[date, date]:
    preset_key = f"{key}_preset"
    start_key = f"{key}_start"
    end_key = f"{key}_end"

    if start_key not in st.session_state or end_key not in st.session_state:
        default_start, default_end = clamp_date_range(*get_preset_range("SJ 2025/2026"), min_date, max_date)
        st.session_state[start_key] = default_start
        st.session_state[end_key] = default_end
        st.session_state[preset_key] = "SJ 2025/2026"

    st.subheader("Zeitraum")
    selected_preset = st.radio(
        "Voreinstellung",
        options=PRESET_ORDER,
        key=preset_key,
        horizontal=True,
        label_visibility="collapsed",
    )

    preset_start, preset_end = clamp_date_range(*get_preset_range(selected_preset), min_date, max_date)
    if (preset_start, preset_end) != (st.session_state[start_key], st.session_state[end_key]):
        st.session_state[start_key] = preset_start
        st.session_state[end_key] = preset_end

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Von",
            value=st.session_state[start_key],
            min_value=min_date,
            max_value=max_date,
            key=f"{start_key}_picker",
            format=DATE_PICKER_INPUT_FORMAT,
        )
    with col2:
        end_date = st.date_input(
            "Bis",
            value=st.session_state[end_key],
            min_value=min_date,
            max_value=max_date,
            key=f"{end_key}_picker",
            format=DATE_PICKER_INPUT_FORMAT,
        )

    start_date, end_date = clamp_date_range(start_date, end_date, min_date, max_date)
    st.session_state[start_key] = start_date
    st.session_state[end_key] = end_date
    return start_date, end_date



def filter_by_date(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    date_col = col("date")
    return df[
        (df[date_col] >= pd.to_datetime(start_date))
        & (df[date_col] <= pd.to_datetime(end_date))
    ].copy()



def apply_date_filter(df: pd.DataFrame, key: str) -> tuple[pd.DataFrame, date, date]:
    min_date = df[col("date")].min().date()
    max_date = df[col("date")].max().date()
    start_date, end_date = render_date_filter(key, min_date, max_date)
    return filter_by_date(df, start_date, end_date), start_date, end_date


# =========================================================
# SCHÜLER-FILTER
# =========================================================


def get_student_options(df: pd.DataFrame, include_all: bool = False) -> list[str]:
    student_names = sorted(df[col("student_name")].dropna().astype(str).unique().tolist())
    if include_all:
        return ["Alle", *student_names]
    return student_names



def render_student_filter(df: pd.DataFrame, key: str = "student_select", include_all: bool = False) -> str:
    options = get_student_options(df, include_all=include_all)
    if not options:
        st.warning("Keine Schüler:innen in den Daten gefunden.")
        st.stop()
    return st.selectbox("Schüler:in", options=options, key=key)



def filter_by_student(df: pd.DataFrame, student_name: str) -> pd.DataFrame:
    return df[df[col("student_name")].astype(str) == student_name].copy()


# =========================================================
# AGGREGATIONEN
# =========================================================


def aggregate_class_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    summary_df = (
        df.groupby(col("student_name"), as_index=False)
        .agg(
            unique_days=(col("date"), "nunique"),
            total_hours=(col("hours"), "sum"),
            date_from=(col("date"), "min"),
            date_to=(col("date"), "max"),
        )
    )

    excused = (
        df[df[col("status")] == STATUS_VALUES["excused"]]
        .groupby(col("student_name"))[col("hours")]
        .sum()
        .rename("excused_hours")
    )
    open_hours = (
        df[df[col("status")] == STATUS_VALUES["open"]]
        .groupby(col("student_name"))[col("hours")]
        .sum()
        .rename("open_hours")
    )

    summary_df = summary_df.merge(excused, on=col("student_name"), how="left")
    summary_df = summary_df.merge(open_hours, on=col("student_name"), how="left")
    summary_df[["excused_hours", "open_hours"]] = summary_df[["excused_hours", "open_hours"]].fillna(0)
    summary_df["avg_hours_per_day"] = (summary_df["total_hours"] / summary_df["unique_days"]).fillna(0).round(1)
    summary_df["open_percent"] = (summary_df["open_hours"] / summary_df["total_hours"] * 100).fillna(0).round(1)
    return summary_df.replace([float("inf"), -float("inf")], 0)



def format_class_result(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame(columns=list(CLASS_TABLE_LABELS.values()))

    return summary_df[
        [
            col("student_name"),
            "unique_days",
            "total_hours",
            "avg_hours_per_day",
            "excused_hours",
            "open_hours",
            "open_percent",
            "date_from",
            "date_to",
        ]
    ].rename(
        columns={
            col("student_name"): CLASS_TABLE_LABELS["student_name"],
            "unique_days": CLASS_TABLE_LABELS["unique_days"],
            "total_hours": CLASS_TABLE_LABELS["total_hours"],
            "avg_hours_per_day": CLASS_TABLE_LABELS["avg_hours_per_day"],
            "excused_hours": CLASS_TABLE_LABELS["excused_hours"],
            "open_hours": CLASS_TABLE_LABELS["open_hours"],
            "open_percent": CLASS_TABLE_LABELS["open_percent"],
            "date_from": CLASS_TABLE_LABELS["date_from"],
            "date_to": CLASS_TABLE_LABELS["date_to"],
        }
    )



def calculate_class_metrics(summary_df: pd.DataFrame) -> dict[str, float | int]:
    if summary_df.empty:
        return {
            "student_count": 0,
            "avg_days": 0.0,
            "avg_hours_per_day": 0.0,
            "median_days": 0.0,
            "students_with_open_absences": 0,
            "open_absence_share": 0.0,
        }

    student_count = int(len(summary_df))
    students_with_open_absences = int((summary_df["open_hours"] > 0).sum())
    return {
        "student_count": student_count,
        "avg_days": float(summary_df["unique_days"].mean()),
        "avg_hours_per_day": float(summary_df["avg_hours_per_day"].mean()),
        "median_days": float(summary_df["unique_days"].median()),
        "students_with_open_absences": students_with_open_absences,
        "open_absence_share": float(students_with_open_absences / student_count * 100) if student_count else 0.0,
    }



def calculate_student_metrics(df: pd.DataFrame) -> dict[str, float | int]:
    if df.empty:
        return {
            "excused_hours": 0.0,
            "open_hours": 0.0,
            "total_hours": 0.0,
            "days_count": 0,
            "avg_hours_per_day": 0.0,
        }

    excused_hours = df.loc[df[col("status")] == STATUS_VALUES["excused"], col("hours")].sum()
    open_hours = df.loc[df[col("status")] == STATUS_VALUES["open"], col("hours")].sum()
    total_hours = df[col("hours")].sum()
    days_count = int(df[col("date")].nunique())
    return {
        "excused_hours": float(excused_hours),
        "open_hours": float(open_hours),
        "total_hours": float(total_hours),
        "days_count": days_count,
        "avg_hours_per_day": float(total_hours / days_count) if days_count else 0.0,
    }



def aggregate_student_by_date(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(STUDENT_DAILY_TABLE_LABELS.values()))

    daily_df = df.groupby(col("date"), as_index=False).agg(total_hours=(col("hours"), "sum"))
    excused_df = (
        df[df[col("status")] == STATUS_VALUES["excused"]]
        .groupby(col("date"))[col("hours")]
        .sum()
        .rename("excused_hours")
        .reset_index()
    )
    open_df = (
        df[df[col("status")] == STATUS_VALUES["open"]]
        .groupby(col("date"))[col("hours")]
        .sum()
        .rename("open_hours")
        .reset_index()
    )

    daily_df = daily_df.merge(excused_df, on=col("date"), how="left")
    daily_df = daily_df.merge(open_df, on=col("date"), how="left")
    daily_df[["excused_hours", "open_hours"]] = daily_df[["excused_hours", "open_hours"]].fillna(0)

    return daily_df.rename(
        columns={
            col("date"): STUDENT_DAILY_TABLE_LABELS["date"],
            "excused_hours": STUDENT_DAILY_TABLE_LABELS["excused_hours"],
            "open_hours": STUDENT_DAILY_TABLE_LABELS["open_hours"],
            "total_hours": STUDENT_DAILY_TABLE_LABELS["total_hours"],
        }
    ).sort_values(STUDENT_DAILY_TABLE_LABELS["date"])



def build_monthly_absence_table(df: pd.DataFrame, include_students: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    if df.empty:
        empty = pd.DataFrame(columns=["month", "Monat", "total_absence_hours", "unique_absence_days", "avg_absence_hours_per_day"])
        display_columns = ["Monat", "Fehlzeiten gesamt", "Tage mit Fehlzeiten", "Ø / Tag"]
        if include_students:
            display_columns.insert(3, "SuS betroffen")
        return empty, pd.DataFrame(columns=display_columns), 0.0

    analysis_df = df[[col("date"), col("hours"), col("student_name")]].copy()
    analysis_df["month"] = analysis_df[col("date")].dt.to_period("M").dt.to_timestamp()

    agg_kwargs = {
        "total_absence_hours": (col("hours"), "sum"),
        "unique_absence_days": (col("date"), "nunique"),
    }
    if include_students:
        agg_kwargs["unique_students"] = (col("student_name"), "nunique")

    monthly_df = analysis_df.groupby("month", as_index=False).agg(**agg_kwargs)
    all_months = pd.date_range(monthly_df["month"].min(), monthly_df["month"].max(), freq="MS")
    monthly_df = monthly_df.set_index("month").reindex(all_months, fill_value=0).rename_axis("month").reset_index()

    if "unique_students" not in monthly_df.columns:
        monthly_df["unique_students"] = 0

    monthly_df["avg_absence_hours_per_day"] = (
        monthly_df["total_absence_hours"] / monthly_df["unique_absence_days"].replace(0, pd.NA)
    ).fillna(0)
    monthly_df["Monat"] = monthly_df["month"].apply(format_month_label)

    display_df = pd.DataFrame({
        "Monat": monthly_df["Monat"],
        "Fehlzeiten gesamt": monthly_df["total_absence_hours"].round(1),
        "Tage mit Fehlzeiten": monthly_df["unique_absence_days"].astype(int),
        "Ø / Tag": monthly_df["avg_absence_hours_per_day"].round(1),
    })
    if include_students:
        display_df.insert(3, "SuS betroffen", monthly_df["unique_students"].astype(int))

    max_avg_value = float(display_df["Ø / Tag"].max()) if not display_df.empty else 0.0
    return monthly_df, display_df, max_avg_value



def build_student_vs_class_monthly_chart_data(student_df: pd.DataFrame, class_df: pd.DataFrame, student_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly_df, _, _ = build_monthly_absence_table(student_df, include_students=False)
    if monthly_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    all_students_monthly_df = (
        class_df[[col("student_name"), col("date"), col("hours")]]
        .assign(month=lambda df_: df_[col("date")].dt.to_period("M").dt.to_timestamp())
    )

    student_monthly_stats_df = (
        all_students_monthly_df.groupby(["month", col("student_name")], as_index=False)
        .agg(
            total_absence_hours=(col("hours"), "sum"),
            unique_absence_days=(col("date"), "nunique"),
        )
    )
    student_monthly_stats_df["avg_absence_hours_per_day"] = (
        student_monthly_stats_df["total_absence_hours"]
        / student_monthly_stats_df["unique_absence_days"].replace(0, pd.NA)
    ).fillna(0)

    class_avg_monthly_df = (
        student_monthly_stats_df.groupby("month", as_index=False)
        .agg(
            class_avg_hours=("total_absence_hours", "mean"),
            class_avg_days=("unique_absence_days", "mean"),
            class_avg_per_day=("avg_absence_hours_per_day", "mean"),
        )
    )

    class_avg_monthly_df = monthly_df[["month", "Monat"]].merge(class_avg_monthly_df, on="month", how="left").fillna(0)

    student_chart_df = monthly_df[["Monat", "avg_absence_hours_per_day", "total_absence_hours", "unique_absence_days"]].copy()
    student_chart_df["Reihe"] = student_name
    student_chart_df["Wert"] = student_chart_df["avg_absence_hours_per_day"]
    student_chart_df["Fehlzeiten gesamt"] = student_chart_df["total_absence_hours"]
    student_chart_df["Tage mit Fehlzeiten"] = student_chart_df["unique_absence_days"]

    class_chart_df = class_avg_monthly_df[["Monat", "class_avg_per_day", "class_avg_hours", "class_avg_days"]].copy()
    class_chart_df["Reihe"] = "Klassenschnitt"
    class_chart_df["Wert"] = class_chart_df["class_avg_per_day"]
    class_chart_df["Fehlzeiten gesamt"] = class_chart_df["class_avg_hours"]
    class_chart_df["Tage mit Fehlzeiten"] = class_chart_df["class_avg_days"]

    return student_chart_df, class_chart_df



def build_monthly_trend_data(df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    monthly_df, _, _ = build_monthly_absence_table(df, include_students=True)
    if monthly_df.empty:
        return pd.DataFrame(columns=["Monat", "Fehlzeiten gesamt", "Tage mit Fehlzeiten", "SuS betroffen", "Ø / Tag"]), 0.0

    chart_df = pd.DataFrame({
        "Monat": monthly_df["Monat"],
        "Fehlzeiten gesamt": monthly_df["total_absence_hours"],
        "Tage mit Fehlzeiten": monthly_df["unique_absence_days"],
        "SuS betroffen": monthly_df["unique_students"],
        "Ø / Tag": monthly_df["avg_absence_hours_per_day"],
    })
    max_total = float(chart_df["Fehlzeiten gesamt"].max()) if not chart_df.empty else 0.0
    return chart_df, max_total


# =========================================================
# VERSPÄTUNGEN
# =========================================================


def filter_tardiness_data(df: pd.DataFrame) -> pd.DataFrame:
    tardiness_df = df[normalize_text(df[col("absence_reason")]) == "verspätung"].copy()
    return tardiness_df[(tardiness_df[col("minutes")] > 0) & (tardiness_df[col("minutes")] < 45)].copy()



def aggregate_tardiness_by_student(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby(col("student_name"), as_index=False)
        .agg(
            tardiness_count=(col("date"), "count"),
            avg_minutes_per_tardy=(col("minutes"), "mean"),
        )
        .rename(columns={col("student_name"): "student_name"})
        .assign(
            tardiness_count=lambda x: x["tardiness_count"].astype(int),
            avg_minutes_per_tardy=lambda x: x["avg_minutes_per_tardy"].round(1),
        )
    )



def format_tardiness_result(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame(columns=list(TARDINESS_TABLE_LABELS.values()))

    return summary_df[["student_name", "tardiness_count", "avg_minutes_per_tardy"]].rename(
        columns={
            "student_name": TARDINESS_TABLE_LABELS["student_name"],
            "tardiness_count": TARDINESS_TABLE_LABELS["tardiness_count"],
            "avg_minutes_per_tardy": TARDINESS_TABLE_LABELS["avg_minutes_per_tardy"],
        }
    )


# =========================================================
# KALENDER-ANSICHT
# =========================================================


def get_month_sequence(start_date: date, end_date: date) -> list[pd.Timestamp]:
    months = []
    current_month = pd.Timestamp(start_date).replace(day=1)
    last_month = pd.Timestamp(end_date).replace(day=1)
    while current_month <= last_month:
        months.append(current_month)
        current_month = current_month + pd.offsets.MonthBegin(1)
    return months



def get_holiday_name(current_date: date) -> str | None:
    for start, end, holiday_name in NRW_HOLIDAY_RANGES:
        if start <= current_date <= end:
            return holiday_name
    return None



def build_absence_lookup(df: pd.DataFrame, include_student_count: bool = True) -> dict[date, dict[str, float | int]]:
    if df.empty:
        return {}

    agg_kwargs = {
        "eintraege": (col("date"), "size"),
        "fehlstunden": (col("hours"), "sum"),
    }
    if include_student_count:
        agg_kwargs["sus"] = (col("student_name"), "nunique")

    grouped = df.groupby(col("date"), as_index=False).agg(**agg_kwargs)
    lookup: dict[date, dict[str, float | int]] = {}
    for _, row in grouped.iterrows():
        entry = {
            "eintraege": int(row["eintraege"]),
            "fehlstunden": float(row["fehlstunden"]),
        }
        if include_student_count:
            entry["sus"] = int(row["sus"])
        lookup[row[col("date")].date()] = entry
    return lookup



def build_calendar_html(start_date: date, end_date: date, absence_lookup: dict[date, dict], include_student_count: bool = True) -> str:
    rows_html: list[str] = []

    for month_start in get_month_sequence(start_date, end_date):
        month_label = format_month_label(month_start)
        last_day_of_month = calendar.monthrange(month_start.year, month_start.month)[1]
        cells: list[str] = []

        for day in range(1, 32):
            if day > last_day_of_month:
                cells.append('<td><div class="day-cell day-empty"></div></td>')
                continue

            current_date = date(month_start.year, month_start.month, day)
            if current_date < start_date or current_date > end_date:
                cells.append('<td><div class="day-cell day-empty"></div></td>')
                continue

            holiday_name = get_holiday_name(current_date)
            formatted_day = format_day_with_weekday(current_date)

            if current_date in absence_lookup:
                info = absence_lookup[current_date]
                if include_student_count:
                    title = (
                        f"{formatted_day} · Fehlzeiten"
                        f" | SuS: {info['sus']} | Einträge: {info['eintraege']} | Fehlstunden: {info['fehlstunden']:.1f}"
                    )
                else:
                    title = f"{formatted_day} · Fehlzeiten | Einträge: {info['eintraege']} | Fehlstunden: {info['fehlstunden']:.1f}"
                cell_class = "day-red"
            elif holiday_name:
                title = f"{formatted_day} · {holiday_name}"
                cell_class = "day-blue"
            elif current_date.weekday() >= 5:
                title = f"{formatted_day} · Wochenende"
                cell_class = "day-gray"
            else:
                title = f"{formatted_day} · Keine Fehlzeiten"
                cell_class = "day-green"

            safe_title = escape(title, quote=True)
            cells.append(f'<td><div class="day-cell {cell_class}" title="{safe_title}">{day}</div></td>')

        rows_html.append(f'<tr><td class="calendar-month">{month_label}</td>{"".join(cells)}</tr>')

    return f"""
    <style>
    .calendar-legend {{ display:flex; gap:1rem; flex-wrap:wrap; margin:0.4rem 0 1rem 0; align-items:center; }}
    .calendar-legend-item {{ display:inline-flex; align-items:center; gap:0.45rem; font-size:0.95rem; }}
    .calendar-box {{ width:18px; height:18px; border-radius:4px; display:inline-block; }}
    .calendar-grid {{ border-collapse:separate; border-spacing:4px; width:100%; table-layout:fixed; }}
    .calendar-grid td {{ text-align:center; vertical-align:middle; border:0; }}
    .calendar-grid .calendar-month {{ width:90px; min-width:90px; text-align:left !important; font-weight:600; padding-right:0.45rem; white-space:nowrap; }}
    .day-cell {{ width:24px; height:24px; border-radius:5px; display:inline-flex; align-items:center; justify-content:center; font-size:0.68rem; font-weight:700; border:1px solid rgba(0,0,0,0.08); box-sizing:border-box; }}
    .day-green {{ background:#dcfce7; color:#166534; }}
    .day-red {{ background:#fecaca; color:#991b1b; }}
    .day-gray {{ background:#e5e7eb; color:#4b5563; }}
    .day-blue {{ background:#dbeafe; color:#1d4ed8; }}
    .day-empty {{ background:transparent; border:none; }}
    .calendar-wrap {{ overflow-x:auto; padding-bottom:0.5rem; }}
    </style>
    <div class="calendar-legend">
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#dcfce7"></span> Unterrichtstag ohne Fehlzeiten</span>
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#fecaca"></span> Tag mit Fehlzeiten</span>
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#dbeafe"></span> Ferien (NRW)</span>
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#e5e7eb"></span> Wochenende</span>
    </div>
    <div class="calendar-wrap">
        <table class="calendar-grid"><tbody>{''.join(rows_html)}</tbody></table>
    </div>
    """
