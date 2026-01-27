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
    df = pd.read_csv(input_path)

    if df.shape[1] != 2:
        raise ValueError("Файл має містити рівно 2 колонки: дата та значення")

    date_col, value_col = df.columns

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    date_columns = [d.strftime("%d.%m.%Y") for d in df[date_col]]

    code = generate_numeric_code(nomenclature)

    header = (
        ["", "Код", "Категорія", "", "Номенклатура, Базова одиниця виміру"]
        + date_columns
        + ["Підсумок"]
    )

    service_row = (
        ["", "", "", "Кратність", "Контрагент"]
        + ["Кількість"] * len(date_columns)
        + ["Кількість"]
    )

    values = df[value_col].fillna(0).tolist()
    total = sum(values)

    data_row = ["", code, category, multiplicity, nomenclature] + values + [total]

    out_df = pd.DataFrame([service_row, data_row], columns=header)

    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✔ Файл збережено: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Конвертація часового ряду у формат продажів"
    )
    parser.add_argument("--i", help="Шлях до вхідного CSV")
    parser.add_argument("--o", help="Шлях до вихідного CSV")
    parser.add_argument(
        "--nomenclature", default=str(uuid4()), help="Назва номенклатури"
    )
    parser.add_argument("--category", default=str(uuid4()), help="Категорія")
    parser.add_argument(
        "--multiplicity", type=int, default=1, help="Кратність (default=1)"
    )

    args = parser.parse_args()

    transform_timeseries(
        input_path=args.input,
        output_path=args.output,
        nomenclature=args.nomenclature,
        category=args.category,
        multiplicity=args.multiplicity,
    )
