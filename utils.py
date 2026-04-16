from __future__ import annotations

import calendar
from datetime import date
from html import escape
from io import BytesIO
from typing import Iterable

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

EXCLUDED_ABSENCE_REASONS = [
    "Verspätung",
    "Beurlaubung",
    "schulische Veranstaltung",
    "Auslandsaufenthalt",
]

EXCLUDED_NAMES = [
    "Dahmen Michael",
    "Phiri Sarah",
    "Krauth Valentin",
    "Gerdes Juri",
]

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
            padding: 0.5rem 0.8rem;
            background: rgba(255, 255, 255, 0.02);
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
        .date-filter-label {
            margin: 0.2rem 0 0.5rem 0;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    exclude_names: bool = True,
    exclude_absence_reasons: bool = True,
) -> pd.DataFrame:
    prepared_df = df.copy()

    student_col = col("student_name")
    date_col = col("date")
    reason_col = col("absence_reason")
    hours_col = col("hours")
    status_col = col("status")

    if exclude_absence_reasons:
        excluded_reasons = [value.strip().lower() for value in EXCLUDED_ABSENCE_REASONS]
        prepared_df = prepared_df[
            ~normalize_text(prepared_df[reason_col]).isin(excluded_reasons)
        ].copy()

    if exclude_names:
        excluded_names = [name.strip().lower() for name in EXCLUDED_NAMES]
        prepared_df = prepared_df[
            ~normalize_text(prepared_df[student_col]).isin(excluded_names)
        ].copy()

    prepared_df[status_col] = normalize_text(prepared_df[status_col])
    prepared_df[hours_col] = pd.to_numeric(prepared_df[hours_col], errors="coerce").fillna(0)
    prepared_df[date_col] = pd.to_datetime(
        prepared_df[date_col],
        format=DATE_INPUT_FORMAT,
        errors="coerce",
    )

    prepared_df = prepared_df.dropna(subset=[date_col]).copy()

    if prepared_df.empty:
        st.warning("Nach dem Filtern sind keine gültigen Daten mehr vorhanden.")
        st.stop()

    return prepared_df



def get_prepared_data(
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


def _date_state_key(prefix: str, name: str) -> str:
    return f"{prefix}_{name}"



def _start_picker_key(prefix: str) -> str:
    return f"{prefix}_start_picker"



def _end_picker_key(prefix: str) -> str:
    return f"{prefix}_end_picker"



def _default_preset_name() -> str:
    return PRESET_ORDER[-1]



def _all_fixed_dates() -> Iterable[date]:
    for config in PRESET_DATE_RANGES.values():
        if config["type"] == "fixed":
            yield parse_fixed_date(config["start"])
            yield parse_fixed_date(config["end"])



def get_preset_range(preset_name: str) -> tuple[date, date]:
    config = PRESET_DATE_RANGES[preset_name]
    if config["type"] == "relative":
        end_date = today_date()
        start_date = end_date - pd.Timedelta(days=config["days"])
    else:
        start_date = parse_fixed_date(config["start"])
        end_date = parse_fixed_date(config["end"])
    return start_date, end_date



def _picker_bounds(min_date: date, max_date: date) -> tuple[date, date]:
    fixed_dates = list(_all_fixed_dates())
    picker_min = min([min_date, *fixed_dates]) if fixed_dates else min_date
    picker_max = max([max_date, today_date(), *fixed_dates]) if fixed_dates else max(max_date, today_date())
    return picker_min, picker_max



def _sync_picker_state(prefix: str) -> None:
    st.session_state[_start_picker_key(prefix)] = st.session_state[_date_state_key(prefix, "start_date")]
    st.session_state[_end_picker_key(prefix)] = st.session_state[_date_state_key(prefix, "end_date")]



def _match_preset_for_range(start_date: date, end_date: date) -> str | None:
    for preset_name in PRESET_ORDER:
        preset_start, preset_end = get_preset_range(preset_name)
        if start_date == preset_start and end_date == preset_end:
            return preset_name
    return None



def init_date_state(prefix: str, min_date: date, max_date: date) -> None:
    start_key = _date_state_key(prefix, "start_date")
    end_key = _date_state_key(prefix, "end_date")
    preset_key = _date_state_key(prefix, "selected_preset")

    if start_key not in st.session_state or end_key not in st.session_state:
        default_preset = _default_preset_name()
        default_start, default_end = get_preset_range(default_preset)
        st.session_state[start_key] = default_start
        st.session_state[end_key] = default_end
        st.session_state[preset_key] = default_preset
        _sync_picker_state(prefix)
        return

    picker_min, picker_max = _picker_bounds(min_date, max_date)
    start_date = st.session_state[start_key]
    end_date = st.session_state[end_key]
    start_date = max(picker_min, min(start_date, picker_max))
    end_date = max(picker_min, min(end_date, picker_max))

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    st.session_state[start_key] = start_date
    st.session_state[end_key] = end_date
    st.session_state[preset_key] = _match_preset_for_range(start_date, end_date)
    _sync_picker_state(prefix)



def reset_date_state(prefix: str, min_date: date, max_date: date) -> None:
    del min_date, max_date
    default_preset = _default_preset_name()
    start_date, end_date = get_preset_range(default_preset)
    st.session_state[_date_state_key(prefix, "start_date")] = start_date
    st.session_state[_date_state_key(prefix, "end_date")] = end_date
    st.session_state[_date_state_key(prefix, "selected_preset")] = default_preset
    _sync_picker_state(prefix)



def apply_preset(prefix: str, preset_name: str) -> None:
    start_date, end_date = get_preset_range(preset_name)
    st.session_state[_date_state_key(prefix, "start_date")] = start_date
    st.session_state[_date_state_key(prefix, "end_date")] = end_date
    st.session_state[_date_state_key(prefix, "selected_preset")] = preset_name
    _sync_picker_state(prefix)



def render_date_filter(prefix: str, min_date: date, max_date: date) -> tuple[date, date]:
    init_date_state(prefix, min_date, max_date)
    picker_min, picker_max = _picker_bounds(min_date, max_date)

    st.subheader("Zeitraum")
    selected_preset = st.session_state.get(_date_state_key(prefix, "selected_preset"))

    preset_cols = st.columns(len(PRESET_ORDER))
    for index, preset_name in enumerate(PRESET_ORDER):
        button_type = "primary" if preset_name == selected_preset else "secondary"
        if preset_cols[index].button(
            preset_name,
            key=f"{prefix}_preset_{index}",
            type=button_type,
            use_container_width=True,
        ):
            apply_preset(prefix, preset_name)
            st.rerun()

    input_col1, input_col2 = st.columns(2)
    current_start = st.session_state[_date_state_key(prefix, "start_date")]
    current_end = st.session_state[_date_state_key(prefix, "end_date")]

    with input_col1:
        selected_start = st.date_input(
            "Von",
            value=st.session_state.get(_start_picker_key(prefix), current_start),
            min_value=picker_min,
            max_value=picker_max,
            key=_start_picker_key(prefix),
            format=DATE_PICKER_INPUT_FORMAT,
        )

    with input_col2:
        selected_end = st.date_input(
            "Bis",
            value=st.session_state.get(_end_picker_key(prefix), current_end),
            min_value=picker_min,
            max_value=picker_max,
            key=_end_picker_key(prefix),
            format=DATE_PICKER_INPUT_FORMAT,
        )

    if selected_start > selected_end:
        st.warning("Das Startdatum darf nicht nach dem Enddatum liegen.")
        return current_start, current_end

    if selected_start != current_start or selected_end != current_end:
        st.session_state[_date_state_key(prefix, "start_date")] = selected_start
        st.session_state[_date_state_key(prefix, "end_date")] = selected_end
        st.session_state[_date_state_key(prefix, "selected_preset")] = _match_preset_for_range(
            selected_start,
            selected_end,
        )
        return selected_start, selected_end

    return current_start, current_end



def filter_by_date(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    date_col = col("date")
    return df[
        (df[date_col] >= pd.to_datetime(start_date))
        & (df[date_col] <= pd.to_datetime(end_date))
    ].copy()


# =========================================================
# SCHÜLER-FILTER
# =========================================================


def render_student_filter(df: pd.DataFrame, key: str = "student_select") -> str:
    student_col = col("student_name")
    student_names = sorted(df[student_col].dropna().astype(str).unique().tolist())

    if not student_names:
        st.warning("Keine Schüler*innen in den Daten gefunden.")
        st.stop()

    return st.selectbox("Schüler*in auswählen", options=student_names, index=0, key=key)



def filter_by_student(df: pd.DataFrame, student_name: str) -> pd.DataFrame:
    student_col = col("student_name")
    return df[df[student_col].astype(str) == student_name].copy()


# =========================================================
# KLASSENÜBERSICHT / SCHÜLERANSICHT
# =========================================================


def aggregate_class_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    student_col = col("student_name")
    date_col = col("date")
    hours_col = col("hours")
    status_col = col("status")

    summary_df = (
        df.groupby(student_col)
        .agg(
            unique_days=(date_col, "nunique"),
            total_hours=(hours_col, "sum"),
            date_from=(date_col, "min"),
            date_to=(date_col, "max"),
        )
        .reset_index()
    )

    excused_hours = (
        df[df[status_col] == STATUS_VALUES["excused"]]
        .groupby(student_col)[hours_col]
        .sum()
        .rename("excused_hours")
    )
    open_hours = (
        df[df[status_col] == STATUS_VALUES["open"]]
        .groupby(student_col)[hours_col]
        .sum()
        .rename("open_hours")
    )

    summary_df = summary_df.merge(excused_hours, on=student_col, how="left")
    summary_df = summary_df.merge(open_hours, on=student_col, how="left")
    summary_df[["excused_hours", "open_hours"]] = summary_df[["excused_hours", "open_hours"]].fillna(0)

    summary_df["avg_hours_per_day"] = (
        summary_df["total_hours"] / summary_df["unique_days"]
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)
    summary_df["open_percent"] = (
        summary_df["open_hours"] / summary_df["total_hours"] * 100
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    return summary_df



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



def calculate_student_metrics(df: pd.DataFrame) -> dict[str, float | int]:
    if df.empty:
        return {
            "excused_hours": 0.0,
            "open_hours": 0.0,
            "total_hours": 0.0,
            "days_count": 0,
            "avg_hours_per_day": 0.0,
        }

    hours_col = col("hours")
    status_col = col("status")
    date_col = col("date")

    excused_hours = df.loc[df[status_col] == STATUS_VALUES["excused"], hours_col].sum()
    open_hours = df.loc[df[status_col] == STATUS_VALUES["open"], hours_col].sum()
    total_hours = df[hours_col].sum()
    days_count = int(df[date_col].nunique())
    avg_hours_per_day = total_hours / days_count if days_count > 0 else 0.0

    return {
        "excused_hours": float(excused_hours),
        "open_hours": float(open_hours),
        "total_hours": float(total_hours),
        "days_count": days_count,
        "avg_hours_per_day": float(avg_hours_per_day),
    }



def aggregate_student_by_date(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(STUDENT_DAILY_TABLE_LABELS.values()))

    date_col = col("date")
    hours_col = col("hours")
    status_col = col("status")

    daily_df = df.groupby(date_col).agg(total_hours=(hours_col, "sum")).reset_index()

    excused_df = (
        df[df[status_col] == STATUS_VALUES["excused"]]
        .groupby(date_col)[hours_col]
        .sum()
        .rename("excused_hours")
        .reset_index()
    )
    open_df = (
        df[df[status_col] == STATUS_VALUES["open"]]
        .groupby(date_col)[hours_col]
        .sum()
        .rename("open_hours")
        .reset_index()
    )

    daily_df = daily_df.merge(excused_df, on=date_col, how="left")
    daily_df = daily_df.merge(open_df, on=date_col, how="left")
    daily_df[["excused_hours", "open_hours"]] = daily_df[["excused_hours", "open_hours"]].fillna(0)

    daily_df = daily_df.rename(
        columns={
            date_col: STUDENT_DAILY_TABLE_LABELS["date"],
            "excused_hours": STUDENT_DAILY_TABLE_LABELS["excused_hours"],
            "open_hours": STUDENT_DAILY_TABLE_LABELS["open_hours"],
            "total_hours": STUDENT_DAILY_TABLE_LABELS["total_hours"],
        }
    )

    return daily_df.sort_values(STUDENT_DAILY_TABLE_LABELS["date"])


# =========================================================
# MONATSVERLAUF
# =========================================================


def build_monthly_absence_table(df: pd.DataFrame, include_students: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    if df.empty:
        empty_df = pd.DataFrame()
        return empty_df, empty_df, 0.0

    date_col = col("date")
    hours_col = col("hours")
    name_col = col("student_name")

    analysis_df = df[[date_col, hours_col, name_col]].copy()
    analysis_df[hours_col] = pd.to_numeric(analysis_df[hours_col], errors="coerce").fillna(0)
    analysis_df["month"] = analysis_df[date_col].dt.to_period("M").dt.to_timestamp()

    agg_map = {
        "total_absence_hours": (hours_col, "sum"),
        "unique_absence_days": (date_col, "nunique"),
    }
    if include_students:
        agg_map["unique_students"] = (name_col, "nunique")

    monthly_df = analysis_df.groupby("month").agg(**agg_map).reset_index()
    all_months = pd.date_range(
        analysis_df[date_col].min().replace(day=1),
        analysis_df[date_col].max().replace(day=1),
        freq="MS",
    )
    monthly_df = (
        monthly_df.set_index("month")
        .reindex(all_months, fill_value=0)
        .rename_axis("month")
        .reset_index()
    )

    if "unique_students" not in monthly_df.columns:
        monthly_df["unique_students"] = 1

    monthly_df["avg_absence_hours_per_day"] = (
        monthly_df["total_absence_hours"] / monthly_df["unique_absence_days"]
    ).replace([float("inf"), -float("inf")], 0).fillna(0)
    monthly_df["Monat"] = monthly_df["month"].apply(format_month_label)

    display_columns = ["Monat", "Fehlzeiten gesamt", "Tage mit Fehlzeiten"]
    rename_map = {
        "total_absence_hours": "Fehlzeiten gesamt",
        "unique_absence_days": "Tage mit Fehlzeiten",
        "unique_students": "SuS betroffen",
        "avg_absence_hours_per_day": "Ø / Tag",
    }
    if include_students:
        display_columns.append("SuS betroffen")
    display_columns.append("Ø / Tag")

    display_df = monthly_df.rename(columns=rename_map)[display_columns].copy()
    display_df["Fehlzeiten gesamt"] = display_df["Fehlzeiten gesamt"].round(1)
    display_df["Tage mit Fehlzeiten"] = display_df["Tage mit Fehlzeiten"].astype(int)
    if include_students:
        display_df["SuS betroffen"] = display_df["SuS betroffen"].astype(int)
    display_df["Ø / Tag"] = display_df["Ø / Tag"].round(1)

    max_avg_value = float(display_df["Ø / Tag"].max()) if not display_df.empty else 0.0
    return monthly_df, display_df, max_avg_value


# =========================================================
# VERSPÄTUNGEN
# =========================================================


def filter_tardiness_data(df: pd.DataFrame) -> pd.DataFrame:
    reason_col = col("absence_reason")
    minutes_col = col("minutes")

    tardiness_df = df.copy()
    tardiness_df[minutes_col] = pd.to_numeric(tardiness_df[minutes_col], errors="coerce").fillna(0)
    tardiness_df = tardiness_df[normalize_text(tardiness_df[reason_col]) == "verspätung"].copy()
    return tardiness_df[(tardiness_df[minutes_col] > 0) & (tardiness_df[minutes_col] < 45)].copy()



def aggregate_tardiness_by_student(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    student_col = col("student_name")
    date_col = col("date")
    minutes_col = col("minutes")

    summary_df = (
        df.groupby(student_col)
        .agg(
            tardiness_count=(date_col, "count"),
            avg_minutes_per_tardy=(minutes_col, "mean"),
        )
        .reset_index()
        .rename(columns={student_col: "student_name"})
    )
    summary_df["tardiness_count"] = summary_df["tardiness_count"].astype(int)
    summary_df["avg_minutes_per_tardy"] = summary_df["avg_minutes_per_tardy"].round(1)
    return summary_df



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

    date_col = col("date")
    hours_col = col("hours")
    group_df = df.copy()

    agg_map = {
        "eintraege": (date_col, "size"),
        "fehlstunden": (hours_col, "sum"),
    }
    if include_student_count:
        agg_map["sus"] = (col("student_name"), "nunique")

    grouped = group_df.groupby(date_col).agg(**agg_map).reset_index()

    lookup: dict[date, dict[str, float | int]] = {}
    for _, row in grouped.iterrows():
        current_date = row[date_col].date()
        entry = {
            "eintraege": int(row["eintraege"]),
            "fehlstunden": float(row["fehlstunden"]),
        }
        if include_student_count:
            entry["sus"] = int(row["sus"])
        lookup[current_date] = entry
    return lookup



def build_calendar_html(start_date: date, end_date: date, absence_lookup: dict[date, dict], include_student_count: bool = True) -> str:
    months = get_month_sequence(start_date, end_date)
    rows_html: list[str] = []

    for month_start in months:
        month_label = format_month_label(month_start)
        year = month_start.year
        month = month_start.month
        last_day_of_month = calendar.monthrange(year, month)[1]

        cells: list[str] = []
        for day in range(1, 32):
            if day > last_day_of_month:
                cells.append('<td><div class="day-cell day-empty"></div></td>')
                continue

            current_date = date(year, month, day)
            if current_date < start_date or current_date > end_date:
                cells.append('<td><div class="day-cell day-empty"></div></td>')
                continue

            holiday_name = get_holiday_name(current_date)
            formatted_day = format_day_with_weekday(current_date)

            if current_date in absence_lookup:
                info = absence_lookup[current_date]
                cell_class = "day-red"
                holiday_suffix = f" | {holiday_name}" if holiday_name else ""
                if include_student_count:
                    title = (
                        f"{formatted_day} · Fehlzeiten{holiday_suffix} | "
                        f"SuS: {info['sus']} | Einträge: {info['eintraege']} | "
                        f"Fehlstunden: {info['fehlstunden']:.1f}"
                    )
                else:
                    title = (
                        f"{formatted_day} · Fehlzeiten{holiday_suffix} | "
                        f"Einträge: {info['eintraege']} | Fehlstunden: {info['fehlstunden']:.1f}"
                    )
            elif holiday_name:
                cell_class = "day-blue"
                title = f"{formatted_day} · {holiday_name}"
            elif current_date.weekday() >= 5:
                cell_class = "day-gray"
                title = f"{formatted_day} · Wochenende"
            else:
                cell_class = "day-green"
                title = f"{formatted_day} · Keine Fehlzeiten"

            safe_title = escape(title, quote=True)
            cells.append(f'<td><div class="day-cell {cell_class}" title="{safe_title}">{day}</div></td>')

        rows_html.append(f'<tr><td class="calendar-month">{month_label}</td>{"".join(cells)}</tr>')

    return f"""
    <style>
    .calendar-legend {{
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin: 0.4rem 0 1rem 0;
        align-items: center;
    }}
    .calendar-legend-item {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 0.95rem;
    }}
    .calendar-box {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid rgba(0, 0, 0, 0.08);
        display: inline-block;
    }}
    .calendar-grid {{
        border-collapse: separate;
        border-spacing: 4px;
        width: 100%;
        table-layout: fixed;
    }}
    .calendar-grid td {{
        text-align: center;
        vertical-align: middle;
    }}
    .calendar-grid .calendar-month {{
        width: 90px;
        min-width: 90px;
        text-align: left !important;
        font-weight: 600;
        padding-right: 0.45rem;
        white-space: nowrap;
        color: rgba(49, 51, 63, 0.95);
    }}
    .day-cell {{
        width: 24px;
        height: 24px;
        border-radius: 5px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.68rem;
        font-weight: 700;
        border: 1px solid rgba(0,0,0,0.08);
        box-sizing: border-box;
    }}
    .day-green {{ background: #dcfce7; color: #166534; }}
    .day-red {{ background: #fecaca; color: #991b1b; }}
    .day-gray {{ background: #e5e7eb; color: #4b5563; }}
    .day-blue {{ background: #dbeafe; color: #1d4ed8; }}
    .day-empty {{ background: transparent; border: none; }}
    .calendar-wrap {{ overflow-x: auto; padding-bottom: 0.5rem; }}
    </style>
    <div class="calendar-legend">
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#dcfce7"></span> Unterrichtstag ohne Fehlzeiten</span>
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#fecaca"></span> Tag mit Fehlzeiten</span>
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#dbeafe"></span> Ferien (NRW)</span>
        <span class="calendar-legend-item"><span class="calendar-box" style="background:#e5e7eb"></span> Wochenende</span>
    </div>
    <div class="calendar-wrap">
        <table class="calendar-grid">
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """
