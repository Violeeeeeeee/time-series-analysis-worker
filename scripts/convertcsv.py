import argparse
import hashlib
from uuid import uuid4

import pandas as pd


def generate_numeric_code(text: str) -> int:
    """
    Generate numeric representation of given text

    :param text: Text to translate
    :type text: str
    :return: Numeric translation
    :rtype: int
    """
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:6], 16)


def transform_timeseries(
    input_path: str,
    output_path: str,
    nomenclature: str,
    category: str,
    multiplicity: int = 1,
):
    """
    Transform a time series CSV into a formatted sales CSV.

    :param input_path: Path to the input CSV file
    :type input_path: str
    :param output_path: Path to the output CSV file
    :type output_path: str
    :param nomenclature: Nomenclature name
    :type nomenclature: str
    :param category: Item category
    :type category: str
    :param multiplicity: Multiplicity value, defaults to 1
    :type multiplicity: int
    :return: None
    :rtype: None
    """
    df = pd.read_csv(input_path)

    if df.shape[1] != 2:
        raise ValueError("File must contain exactly 2 columns: date and value")

    date_col, value_col = df.columns

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    date_columns = [d.strftime("%d.%m.%Y") for d in df[date_col]]

    code = generate_numeric_code(nomenclature)

    header = (
        ["", "Code", "Category", "", "Nomenclature, Base unit of measurement"]
        + date_columns
        + ["Total"]
    )

    service_row = (
        ["", "", "", "Multiplicity", "Counterparty"]
        + ["Quantity"] * len(date_columns)
        + ["Quantity"]
    )

    values = df[value_col].fillna(0).tolist()
    total = sum(values)

    data_row = ["", code, category, multiplicity, nomenclature] + values + [total]

    out_df = pd.DataFrame([service_row, data_row], columns=header)

    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✔ File saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Conversion of a time series into sales format"
    )
    parser.add_argument("--input", help="Path to input CSV")
    parser.add_argument("--output", help="Path to output CSV")
    parser.add_argument(
        "--nomenclature", default=str(uuid4()), help="Nomenclature name"
    )
    parser.add_argument("--category", default=str(uuid4()), help="Category")
    parser.add_argument(
        "--multiplicity", type=int, default=1, help="Multiplicity (default=1)"
    )

    args = parser.parse_args()

    transform_timeseries(
        input_path=args.input,
        output_path=args.output,
        nomenclature=args.nomenclature,
        category=args.category,
        multiplicity=args.multiplicity,
    )
