import argparse
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = BASE_DIR / "spotify_data.csv"
DEFAULT_OUTPUT_PATH = BASE_DIR / "spotify_data_cleaned.csv"
DEFAULT_DATABASE_PATH = BASE_DIR / "db.sqlite3"
TABLE_NAME = "spotify_data"

ESSENTIAL_COLUMNS = ["track_id", "track_name", "year", "artist_name"]

INTEGER_COLUMNS = [
    "serial_number",
    "popularity",
    "year",
    "key",
    "mode",
    "duration_ms",
    "time_signature",
]

FLOAT_COLUMNS = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
]

TEXT_COLUMNS = ["artist_name", "track_name", "track_id", "genre"]
COLUMN_ORDER = [
    "serial_number",
    "artist_name",
    "track_name",
    "track_id",
    "popularity",
    "year",
    "genre",
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "duration_ms",
    "time_signature",
]

SQLITE_SCHEMA = {
    "serial_number": "INTEGER",
    "artist_name": "TEXT",
    "track_name": "TEXT",
    "track_id": "TEXT PRIMARY KEY",
    "popularity": "INTEGER",
    "year": "INTEGER",
    "genre": "TEXT",
    "danceability": "REAL",
    "energy": "REAL",
    "key": "INTEGER",
    "loudness": "REAL",
    "mode": "INTEGER",
    "speechiness": "REAL",
    "acousticness": "REAL",
    "instrumentalness": "REAL",
    "liveness": "REAL",
    "valence": "REAL",
    "tempo": "REAL",
    "duration_ms": "INTEGER",
    "time_signature": "INTEGER",
}


def clean_spotify_data(input_path=DEFAULT_INPUT_PATH, output_path=DEFAULT_OUTPUT_PATH):
    df = pd.read_csv(input_path)

    if "Unnamed: 0" in df.columns:
        df = df.rename(columns={"Unnamed: 0": "serial_number"})
    elif "" in df.columns:
        df = df.rename(columns={"": "serial_number"})

    df = df.dropna(subset=ESSENTIAL_COLUMNS)

    for column in TEXT_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()

    df = df[(df[ESSENTIAL_COLUMNS] != "").all(axis=1)]

    numeric_columns = INTEGER_COLUMNS + FLOAT_COLUMNS
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=[column for column in numeric_columns if column in df.columns])

    for column in INTEGER_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype("int64")

    for column in FLOAT_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype("float64")

    df = df.drop_duplicates(subset=["track_id"], keep="first")
    df = df[[column for column in COLUMN_ORDER if column in df.columns]]
    df = df.reset_index(drop=True)
    df.to_csv(output_path, index=False)

    return df


def replace_spotify_table(df, database_path=DEFAULT_DATABASE_PATH):
    columns_sql = ", ".join(
        f"{column} {SQLITE_SCHEMA[column]}" for column in COLUMN_ORDER
    )
    placeholders = ", ".join("?" for _ in COLUMN_ORDER)
    insert_sql = f"""
        INSERT INTO {TABLE_NAME} ({", ".join(COLUMN_ORDER)})
        VALUES ({placeholders})
    """

    with sqlite3.connect(database_path) as connection:
        connection.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        connection.execute(f"CREATE TABLE {TABLE_NAME} ({columns_sql})")
        connection.executemany(
            insert_sql,
            df[COLUMN_ORDER].itertuples(index=False, name=None),
        )
        connection.execute(
            f"CREATE INDEX idx_{TABLE_NAME}_genre ON {TABLE_NAME} (genre)"
        )
        connection.execute(
            f"CREATE INDEX idx_{TABLE_NAME}_year ON {TABLE_NAME} (year)"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Clean the Spotify dataset.")
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--database", default=DEFAULT_DATABASE_PATH, type=Path)
    parser.add_argument(
        "--replace-db-table",
        action="store_true",
        help="Replace the spotify_data table in SQLite with typed columns.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cleaned = clean_spotify_data(args.input, args.output)
    print(f"Wrote {len(cleaned):,} cleaned rows to {args.output}")

    if args.replace_db_table:
        replace_spotify_table(cleaned, args.database)
        print(f"Replaced {TABLE_NAME} in {args.database}")
