import pandas as pd
import streamlit as st
import altair as alt

DASHBOARD_TITLE = "Fehlstunden"
DATE_OUTPUT_FORMAT = "%d.%m.%Y"
DATE_INPUT_FORMAT = "%d.%m.%y"

REQUIRED_COLUMNS = [
    "Datum",
    "Abwesenheitsgrund",
    "Fehlstd.",
    "Status"
]

EXCLUDED_ABSENCE_REASONS = [
    "Verspätung",
    "Beurlaubung",
    "schulische Veranstaltung"
]

EXCLUDED_NAMES = [
    "Dahmen Michael",
    "Phiri Sarah",
    "Krauth Valentin",
    "Gerdes Juri"
]


def load_data(uploaded_file) -> pd.DataFrame:
    """Lädt die hochgeladene XLS-Datei."""
    try:
        return pd.read_excel(uploaded_file, engine="xlrd")
    except Exception as exc:
        st.error(f"Die Excel-Datei konnte nicht geladen werden: {exc}")
        st.stop()


def validate_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    """Prüft, ob alle benötigten Spalten vorhanden sind."""
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(
            "Folgende benötigte Spalten fehlen: "
            + ", ".join(missing_columns)
        )
        st.stop()


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Bereinigt, filtert und konvertiert die Rohdaten."""
    df = df.copy()
    group_column = df.columns[0]

    excluded_reasons_clean = [value.strip().lower() for value in EXCLUDED_ABSENCE_REASONS]
    df = df[
        ~df["Abwesenheitsgrund"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(excluded_reasons_clean)
    ].copy()

    excluded_names_clean = [name.strip().lower() for name in EXCLUDED_NAMES]
    if excluded_names_clean:
        df = df[
            ~df[group_column]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(excluded_names_clean)
        ].copy()

    df["Status"] = df["Status"].astype(str).str.strip()
    df["Fehlstd."] = pd.to_numeric(df["Fehlstd."], errors="coerce").fillna(0)

    df["Datum"] = pd.to_datetime(
        df["Datum"],
        format=DATE_INPUT_FORMAT,
        errors="coerce"
    )

    df = df.dropna(subset=["Datum"]).copy()

    if df.empty:
        st.warning("Nach dem Filtern sind keine gültigen Daten mehr vorhanden.")
        st.stop()

    return df


def init_date_state(min_date, max_date) -> None:
    """Initialisiert den Datumsbereich im Session State."""
    st.session_state.setdefault("start_date", min_date)
    st.session_state.setdefault("end_date", max_date)


def render_date_filter(min_date, max_date):
    """Zeigt den Datums-Slider an und gibt den gewählten Bereich zurück."""
    st.subheader("Zeitraum")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("Letzten 7 Tage"):
            st.session_state.start_date = max(min_date, max_date - pd.Timedelta(days=6))
            st.session_state.end_date = max_date

    with col2:
        if st.button("Letzten 14 Tage"):
            st.session_state.start_date = max(min_date, max_date - pd.Timedelta(days=13))
            st.session_state.end_date = max_date

    with col3:
        if st.button("Letzter Monat"):
            st.session_state.start_date = max(min_date, max_date - pd.Timedelta(days=29))
            st.session_state.end_date = max_date

    with col4:
        if st.button("2. Halbjahr"):
            start_2_hj = pd.to_datetime("08.02.2026", format="%d.%m.%Y").date()
            end_2_hj = pd.to_datetime("31.08.2026", format="%d.%m.%Y").date()
            st.session_state.start_date = max(min_date, start_2_hj)
            st.session_state.end_date = min(max_date, end_2_hj)

    with col5:
        if st.button("Reset"):
            st.session_state.start_date = min_date
            st.session_state.end_date = max_date

    start_date, end_date = st.slider(
        label="",
        min_value=min_date,
        max_value=max_date,
        value=(st.session_state.start_date, st.session_state.end_date),
        format="DD.MM.YYYY"
    )

    st.session_state.start_date = start_date
    st.session_state.end_date = end_date

    return start_date, end_date


def filter_by_date(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Filtert die Daten nach dem gewählten Datumsbereich."""
    return df[
        (df["Datum"] >= pd.to_datetime(start_date)) &
        (df["Datum"] <= pd.to_datetime(end_date))
    ].copy()


def aggregate_data(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Gruppiert und berechnet alle gewünschten Kennzahlen."""
    if df.empty:
        return pd.DataFrame()

    result = (
        df.groupby(group_column)
        .agg(
            anzahl_eindeutiger_tage=("Datum", "nunique"),
            fehlstunden_gesamt=("Fehlstd.", "sum"),
            datum_von=("Datum", "min"),
            datum_bis=("Datum", "max")
        )
        .reset_index()
    )

    fehlstunden_entschuldigt = (
        df[df["Status"].str.lower() == "entsch."]
        .groupby(group_column)["Fehlstd."]
        .sum()
        .rename("fehlstunden_entschuldigt")
    )

    fehlstunden_offen = (
        df[df["Status"].str.lower() == "offen"]
        .groupby(group_column)["Fehlstd."]
        .sum()
        .rename("fehlstunden_offen")
    )

    result = result.merge(fehlstunden_entschuldigt, on=group_column, how="left")
    result = result.merge(fehlstunden_offen, on=group_column, how="left")

    result["fehlstunden_entschuldigt"] = result["fehlstunden_entschuldigt"].fillna(0)
    result["fehlstunden_offen"] = result["fehlstunden_offen"].fillna(0)

    result["schnitt"] = (
        result["fehlstunden_gesamt"] / result["anzahl_eindeutiger_tage"]
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    result["prozent_offen_von_gesamt"] = (
        result["fehlstunden_offen"] / result["fehlstunden_gesamt"] * 100
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    result["datum_von"] = result["datum_von"].dt.strftime(DATE_OUTPUT_FORMAT)
    result["datum_bis"] = result["datum_bis"].dt.strftime(DATE_OUTPUT_FORMAT)

    return result


def format_result(result: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Ordnet Spalten an und benennt sie für die Anzeige um."""
    if result.empty:
        return pd.DataFrame(
            columns=[
                "Name",
                "Anzahl eindeutiger Tage",
                "Fehlstunden gesamt",
                "Schnitt",
                "Fehlstunden entschuldigt",
                "Fehlstunden offen",
                "Prozent",
                "Datum von",
                "Datum bis"
            ]
        )

    formatted = result[
        [
            group_column,
            "anzahl_eindeutiger_tage",
            "fehlstunden_gesamt",
            "schnitt",
            "fehlstunden_entschuldigt",
            "fehlstunden_offen",
            "prozent_offen_von_gesamt",
            "datum_von",
            "datum_bis"
        ]
    ].rename(columns={
        group_column: "Name",
        "anzahl_eindeutiger_tage": "Anzahl eindeutiger Tage",
        "fehlstunden_gesamt": "Fehlstunden gesamt",
        "schnitt": "Schnitt",
        "fehlstunden_entschuldigt": "Fehlstunden entschuldigt",
        "fehlstunden_offen": "Fehlstunden offen",
        "prozent_offen_von_gesamt": "Prozent",
        "datum_von": "Datum von",
        "datum_bis": "Datum bis"
    })

    formatted["Prozent"] = formatted["Prozent"].map(lambda x: f"{x:.1f} %")

    return formatted


def render_bar_chart(aggregated_df: pd.DataFrame, group_column: str) -> None:
    """Gestapeltes Balkendiagramm: Gesamt = entschuldigt + offen"""
    if aggregated_df.empty:
        return

    chart_data = aggregated_df[
        [group_column, "fehlstunden_entschuldigt", "fehlstunden_offen"]
    ].rename(columns={group_column: "Name"})

    chart_data = chart_data.melt(
        id_vars="Name",
        value_vars=["fehlstunden_entschuldigt", "fehlstunden_offen"],
        var_name="Kategorie",
        value_name="Fehlstunden"
    )

    chart_data["Kategorie"] = chart_data["Kategorie"].replace({
        "fehlstunden_entschuldigt": "Entschuldigt",
        "fehlstunden_offen": "Offen"
    })

    name_order = aggregated_df.sort_values(
        by="fehlstunden_gesamt",
        ascending=False
    )[group_column].tolist()

    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            y=alt.Y("Name:N", sort=name_order, title="Name"),
            x=alt.X(
                "Fehlstunden:Q",
                stack="zero",
                title="Fehlstunden gesamt"
            ),
            color=alt.Color(
                "Kategorie:N",
                sort=["Entschuldigt", "Offen"],
                title=""
            ),
            tooltip=[
                "Name",
                "Kategorie",
                alt.Tooltip("Fehlstunden:Q", format=".1f")
            ]
        )
        .properties(height=max(300, len(name_order) * 28))
    )

    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title=DASHBOARD_TITLE, layout="wide")
    st.title(DASHBOARD_TITLE)

    uploaded_file = st.file_uploader(
        "Bitte eine Excel-Datei (.xls) hochladen",
        type=["xls"]
    )

    if uploaded_file is None:
        st.info("Bitte lade eine .xls-Datei hoch, um die Analyse zu starten.")
        st.stop()

    df = load_data(uploaded_file)
    validate_columns(df, REQUIRED_COLUMNS)
    df = prepare_data(df)

    group_column = df.columns[0]

    min_date = df["Datum"].min().date()
    max_date = df["Datum"].max().date()

    init_date_state(min_date, max_date)
    start_date, end_date = render_date_filter(min_date, max_date)

    filtered_df = filter_by_date(df, start_date, end_date)
    aggregated_df = aggregate_data(filtered_df, group_column)
    final_result = format_result(aggregated_df, group_column)

    st.subheader(f"Ergebnisse: {len(final_result)} SuS")
    st.dataframe(final_result, hide_index=True, use_container_width=True)

    st.subheader("Fehlstunden (gestapelt)")
    render_bar_chart(aggregated_df, group_column)


if __name__ == "__main__":
    main()
