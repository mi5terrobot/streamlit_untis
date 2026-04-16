import pandas as pd
import streamlit as st


# =========================================================
# KONFIGURATION
# =========================================================

DASHBOARD_TITLE = "Fehlstunden & Verspätungen"
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

PRESET_DATE_RANGES = {
    "Letzte Woche": {"days": 6},
    "Letzte 2 Wochen": {"days": 13},
    "Letzter Monat": {"days": 29},
    "1. Halbjahr": {
        "start": "01.08.2025",
        "end": "07.02.2026",
    },
    "2. Halbjahr": {
        "start": "08.02.2026",
        "end": "31.07.2026",
    },
    "SJ 2025/2026": {
        "start": "01.08.2025",
        "end": "31.07.2026",}
}


# =========================================================
# ALLGEMEINE HILFSFUNKTIONEN
# =========================================================

def col(key: str) -> str:
    return COLUMN_KEYS[key]


def normalize_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def parse_fixed_date(value: str):
    return pd.to_datetime(value, format=DATE_OUTPUT_FORMAT).date()


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
        .reset-button button {
            background-color: #fff1f2;
            color: #9f1239;
            border: 1px solid #fecdd3;
        }
        .reset-button button:hover {
            background-color: #ffe4e6;
            color: #881337;
            border-color: #fda4af;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DATENLADEN / VALIDIEREN / AUFBEREITEN
# =========================================================

def load_data(uploaded_file) -> pd.DataFrame:
    try:
        return pd.read_excel(uploaded_file, engine="xlrd")
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

def _date_state_key(prefix: str, suffix: str) -> str:
    return f"{prefix}_{suffix}"


def init_date_state(prefix: str, min_date, max_date) -> None:
    st.session_state.setdefault(_date_state_key(prefix, "start_date"), min_date)
    st.session_state.setdefault(_date_state_key(prefix, "end_date"), max_date)
    st.session_state.setdefault(_date_state_key(prefix, "selected_preset"), None)


def reset_date_state(prefix: str, min_date, max_date) -> None:
    st.session_state[_date_state_key(prefix, "start_date")] = min_date
    st.session_state[_date_state_key(prefix, "end_date")] = max_date
    st.session_state[_date_state_key(prefix, "selected_preset")] = None
    st.session_state.pop(f"{prefix}_start_input", None)
    st.session_state.pop(f"{prefix}_end_input", None)
    st.session_state.pop(f"{prefix}_preset_control", None)


def clamp_date_state(prefix: str, min_date, max_date) -> None:
    start_date = st.session_state.get(_date_state_key(prefix, "start_date"), min_date)
    end_date = st.session_state.get(_date_state_key(prefix, "end_date"), max_date)

    start_date = max(min_date, min(start_date, max_date))
    end_date = max(min_date, min(end_date, max_date))

    if start_date > end_date:
        start_date, end_date = min_date, max_date

    st.session_state[_date_state_key(prefix, "start_date")] = start_date
    st.session_state[_date_state_key(prefix, "end_date")] = end_date


def _set_date_range(prefix: str, start_date, end_date) -> None:
    st.session_state[_date_state_key(prefix, "start_date")] = start_date
    st.session_state[_date_state_key(prefix, "end_date")] = end_date


def _get_preset_range(preset_config: dict, min_date, max_date):
    if "days" in preset_config:
        start_date = max(min_date, max_date - pd.Timedelta(days=preset_config["days"]))
        end_date = max_date
    else:
        start_date = max(min_date, parse_fixed_date(preset_config["start"]))
        end_date = min(max_date, parse_fixed_date(preset_config["end"]))

    if start_date > end_date:
        start_date, end_date = min_date, max_date

    return start_date, end_date


def render_date_filter(prefix: str, min_date, max_date):
    st.subheader("Zeitraum")

    clamp_date_state(prefix, min_date, max_date)

    start_key = _date_state_key(prefix, "start_date")
    end_key = _date_state_key(prefix, "end_date")
    preset_key = _date_state_key(prefix, "selected_preset")

    selected_preset = st.segmented_control(
        "Schnellauswahl",
        options=list(PRESET_DATE_RANGES.keys()),
        default=st.session_state.get(preset_key),
        key=f"{prefix}_preset_control",
    )

    previous_preset = st.session_state.get(preset_key)

    if selected_preset and selected_preset != previous_preset:
        new_start, new_end = _get_preset_range(
            PRESET_DATE_RANGES[selected_preset],
            min_date,
            max_date,
        )
        _set_date_range(prefix, new_start, new_end)
        st.session_state[preset_key] = selected_preset
        st.session_state[f"{prefix}_start_input"] = new_start
        st.session_state[f"{prefix}_end_input"] = new_end
        st.rerun()

    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "Von",
            value=st.session_state[start_key],
            min_value=min_date,
            max_value=max_date,
            key=f"{prefix}_start_input",
            format=DATE_PICKER_INPUT_FORMAT,
        )

    with date_col2:
        end_date = st.date_input(
            "Bis",
            value=st.session_state[end_key],
            min_value=min_date,
            max_value=max_date,
            key=f"{prefix}_end_input",
            format=DATE_PICKER_INPUT_FORMAT,
        )

    if start_date > end_date:
        st.warning("Das Startdatum darf nicht nach dem Enddatum liegen.")
        return st.session_state[start_key], st.session_state[end_key]

    _set_date_range(prefix, start_date, end_date)

    if selected_preset is not None:
        preset_start, preset_end = _get_preset_range(
            PRESET_DATE_RANGES[selected_preset],
            min_date,
            max_date,
        )
        if start_date != preset_start or end_date != preset_end:
            st.session_state[preset_key] = None

    return start_date, end_date

def filter_by_date(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    date_col = col("date")
    return df[
        (df[date_col] >= pd.to_datetime(start_date))
        & (df[date_col] <= pd.to_datetime(end_date))
    ].copy()


def filter_tardiness_data(df: pd.DataFrame) -> pd.DataFrame:
    reason_col = col("absence_reason")
    minutes_col = col("minutes")

    tardiness_df = df.copy()
    tardiness_df[minutes_col] = pd.to_numeric(
        tardiness_df[minutes_col],
        errors="coerce",
    ).fillna(0)

    tardiness_df = tardiness_df[
        normalize_text(tardiness_df[reason_col]) == "verspätung"
    ].copy()

    tardiness_df = tardiness_df[
        (tardiness_df[minutes_col] > 0) & (tardiness_df[minutes_col] < 45)
    ].copy()

    return tardiness_df


# =========================================================
# SCHÜLER-FILTER
# =========================================================

def render_student_filter(df: pd.DataFrame, key: str = "student_select") -> str:
    student_col = col("student_name")
    student_names = sorted(df[student_col].dropna().astype(str).unique().tolist())

    if not student_names:
        st.warning("Keine Schüler*innen in den Daten gefunden.")
        st.stop()

    return st.selectbox(
        "Schüler*in auswählen",
        options=student_names,
        index=0,
        key=key,
    )


def filter_by_student(df: pd.DataFrame, student_name: str) -> pd.DataFrame:
    student_col = col("student_name")
    return df[df[student_col].astype(str) == student_name].copy()


# =========================================================
# KLASSENÜBERSICHT
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

    summary_df["excused_hours"] = summary_df["excused_hours"].fillna(0)
    summary_df["open_hours"] = summary_df["open_hours"].fillna(0)

    summary_df["avg_hours_per_day"] = (
        summary_df["total_hours"] / summary_df["unique_days"]
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    summary_df["open_percent"] = (
        summary_df["open_hours"] / summary_df["total_hours"] * 100
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    summary_df["date_from"] = summary_df["date_from"].dt.strftime(DATE_OUTPUT_FORMAT)
    summary_df["date_to"] = summary_df["date_to"].dt.strftime(DATE_OUTPUT_FORMAT)

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


# =========================================================
# SCHÜLERANSICHT
# =========================================================

def calculate_student_metrics(df: pd.DataFrame) -> dict:
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

    daily_df = (
        df.groupby(date_col)
        .agg(total_hours=(hours_col, "sum"))
        .reset_index()
    )

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

    daily_df["excused_hours"] = daily_df["excused_hours"].fillna(0)
    daily_df["open_hours"] = daily_df["open_hours"].fillna(0)

    daily_df = daily_df.rename(
        columns={
            date_col: STUDENT_DAILY_TABLE_LABELS["date"],
            "excused_hours": STUDENT_DAILY_TABLE_LABELS["excused_hours"],
            "open_hours": STUDENT_DAILY_TABLE_LABELS["open_hours"],
            "total_hours": STUDENT_DAILY_TABLE_LABELS["total_hours"],
        }
    )

    daily_df = daily_df.sort_values(STUDENT_DAILY_TABLE_LABELS["date"])
    daily_df[STUDENT_DAILY_TABLE_LABELS["date"]] = pd.to_datetime(
        daily_df[STUDENT_DAILY_TABLE_LABELS["date"]]
    ).dt.strftime(DATE_OUTPUT_FORMAT)

    return daily_df


# =========================================================
# VERSPÄTUNGEN
# =========================================================

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

    return summary_df[
        ["student_name", "tardiness_count", "avg_minutes_per_tardy"]
    ].rename(
        columns={
            "student_name": TARDINESS_TABLE_LABELS["student_name"],
            "tardiness_count": TARDINESS_TABLE_LABELS["tardiness_count"],
            "avg_minutes_per_tardy": TARDINESS_TABLE_LABELS["avg_minutes_per_tardy"],
        }
    )
