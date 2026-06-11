import pandas as pd
import csv
import sys
import json

csv.field_size_limit(sys.maxsize)


def load_csv_debug(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(
        file_path,
        engine="python",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL
    )
    print(f"Loaded {len(df)} rows from CSV.")
    print("\nColumn names:", df.columns.tolist())
    print("\nRow-by-row analysis:")

    for idx, row in df.iterrows():
        print(f"\n--- Row {idx} ---")
        print(f"Status: {row.get('Status', 'N/A')}")

        # Check output_pairs
        output_pairs_raw = row.get('output_pairs', '')
        try:
            pairs = json.loads(output_pairs_raw) if isinstance(output_pairs_raw, str) else output_pairs_raw
            print(f"output_pairs parsed: {len(pairs) if isinstance(pairs, list) else 'not a list'} pairs")
            print(f"First 3 pairs: {pairs[:3] if isinstance(pairs, list) else pairs}")
        except Exception as e:
            print(f"output_pairs parse error: {e}")

        # Check for NaN values in other columns
        for col in df.columns:
            if pd.isna(row[col]):
                print(f"  {col}: NaN")

    return df


def plot_latency_from_csv(
        csv_path: Union[str, "os.PathLike[str]"],
        out: Optional[Union[str, "os.PathLike[str]"]] = "latency_from_csv.png",
        *,
        y_unit: str = "ms",
        y_log: bool = False,
        threshold_ms: Optional[float] = None,
        max_points: int = 400_000,
        render: bool = True,
) -> None:
    """Plot per-step latency from CSV results."""

    csv_path = os.fspath(csv_path)
    df = _load_csv(csv_path)

    print(f"DEBUG: Loaded {len(df)} rows from CSV")

    series_list = []
    for idx, row in df.iterrows():
        try:
            s = _df_to_series(row, y_unit=y_unit)
            print(f"DEBUG: Row {idx} ({row.get('Name', 'unknown')}): {len(s)} points")
            series_list.append(s)
        except Exception as e:
            print(f"DEBUG: Row {idx} skipped: {e}")

    print(f"DEBUG: {len(series_list)} rows passed filtering")

    if not series_list:
        raise ValueError("no valid runs found in CSV")

    # ... rest of plotting code


if __name__ == "__main__":
    file_path = "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/results/delete.csv"
    df = load_csv_debug(file_path)
