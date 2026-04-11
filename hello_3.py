import pandas as pd
import streamlit as st
import datetime

st.title("Data Filter Dashboard")

date_format_output = "%d.%m.%Y"

# =========================================================
# 📥 UPLOAD (RAW LAYER)
# =========================================================
uploaded_file = st.file_uploader("Upload CSV file", type="csv")

if uploaded_file is None:
    st.info("Please upload a CSV file to start the analysis.")
    st.stop()

df = pd.read_csv(uploaded_file, sep=";")

first_col = df.columns[0]

df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%y", errors="coerce")
df = df.dropna(subset=["Datum"])

# =========================================================
# 📅 BASE DATE RANGE (STABLE SOURCE)
# =========================================================
min_date = df["Datum"].min().date()
max_date = df["Datum"].max().date()

# =========================================================
# ⚡ QUICK DATE BUTTONS (UI LAYER)
# =========================================================
col1, col2, col3 = st.columns(3)

if "start_date" not in st.session_state:
    st.session_state.start_date = min_date
if "end_date" not in st.session_state:
    st.session_state.end_date = max_date

with col1:
    if st.button("Last week"):
        st.session_state.start_date = max_date - datetime.timedelta(days=7)
        st.session_state.end_date = max_date

with col2:
    if st.button("Last 2 weeks"):
        st.session_state.start_date = max_date - datetime.timedelta(days=14)
        st.session_state.end_date = max_date

with col3:
    if st.button("Reset"):
        st.session_state.start_date = min_date
        st.session_state.end_date = max_date

# =========================================================
# 📊 DATE SLIDER (SYNCED UI)
# =========================================================
start_date, end_date = st.slider(
    "Select date range",
    min_value=min_date,
    max_value=max_date,
    value=(st.session_state.start_date, st.session_state.end_date),
    format="DD.MM.YYYY"
)

st.session_state.start_date = start_date
st.session_state.end_date = end_date

# =========================================================
# 🚦 ROW FILTER LAYER (IMPORTANT: BEFORE GROUPBY)
# =========================================================
base_df = df[
    (df["Datum"] >= pd.to_datetime(start_date)) &
    (df["Datum"] <= pd.to_datetime(end_date))
]

# --- Status filter (SAFE, independent) ---
if "Status" in base_df.columns:
    status_options = sorted(base_df["Status"].dropna().unique())

    status_filter = st.multiselect(
        "Status filter",
        options=status_options
    )

    if status_filter:
        base_df = base_df[base_df["Status"].isin(status_filter)]

# --- Exclude filter ---
exclude_values = st.multiselect(
    "Exclude Abwesenheitsgrund",
    options=sorted(base_df["Abwesenheitsgrund"].dropna().unique())
)

if exclude_values:
    base_df = base_df[
        ~base_df["Abwesenheitsgrund"].isin(exclude_values)
    ]

# =========================================================
# 📊 GROUPING (ONLY AFTER ALL ROW FILTERS)
# =========================================================
result = base_df.groupby(first_col).agg(
    unique_dates=("Datum", "nunique"),
    sum_fehlstd=("Fehlstd.", "sum"),
    first_date=("Datum", "min"),
    last_date=("Datum", "max")
).reset_index()

# =========================================================
# 🎚 GROUP FILTER LAYER (SAFE SLIDER)
# =========================================================
if not result.empty:
    min_unique = int(result["unique_dates"].min())
    max_unique = int(result["unique_dates"].max())

    if min_unique == max_unique:
        unique_filter = min_unique
        st.info(f"All groups have {min_unique} unique dates.")
    else:
        unique_filter = st.slider(
            "Minimum unique dates",
            min_value=min_unique,
            max_value=max_unique,
            value=min_unique
        )

    result = result[result["unique_dates"] >= unique_filter]

# =========================================================
# 📈 METRICS (FINAL STATE ONLY)
# =========================================================
col1, col2 = st.columns(2)
col1.metric("Grouped entries", len(result))
col2.metric("Raw entries", len(base_df))

# =========================================================
# 📊 CALCULATIONS
# =========================================================
if not result.empty:
    result["average"] = (
        result["sum_fehlstd"] / result["unique_dates"]
    ).replace([float("inf"), -float("inf")], 0).round(1)

    result["first_date"] = result["first_date"].dt.strftime(date_format_output)
    result["last_date"] = result["last_date"].dt.strftime(date_format_output)

# =========================================================
# 🧾 FINAL COLUMN ORDER + CLEAN DISPLAY
# =========================================================
result = result[
    [
        first_col,
        "unique_dates",
        "sum_fehlstd",
        "average",
        "first_date",
        "last_date"
    ]
]

result = result.rename(columns={
    first_col: "Name",
    "unique_dates": "Anzahl Tage",
    "sum_fehlstd": "Fehlstunden",
    "average": "Std/Tag",
    "first_date": "Beginn",
    "last_date": "Ende"
})

# =========================================================
# 📋 OUTPUT
# =========================================================
st.subheader("Results")
st.dataframe(result, hide_index=True)