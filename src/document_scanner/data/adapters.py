from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SMARTDOC_ROOT = PROJECT_ROOT / "data" / "raw" / "smartdoc"
INTERIM_ROOT = PROJECT_ROOT / "data" / "interim"

def load_metadata():
    csv_path = SMARTDOC_ROOT / "frames_metadata.csv"

    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    return pd.read_csv(csv_path)

def image_path(relative_path):
    return SMARTDOC_ROOT / relative_path

def corners_tl_tr_br_bl(row):
    return np.array(
        [
            [row.tl_x, row.tl_y],
            [row.tr_x, row.tr_y],
            [row.br_x, row.br_y],
            [row.bl_x, row.bl_y],
        ],
        dtype=np.float32,
    )

if __name__ == "__main__":
    df = load_metadata()

    print("Số ảnh:", len(df))
    print("Số trang gốc:", df["model_name"].nunique())
    print("Số nền:", df["bg_name"].nunique())
    print()
    print(df[["image_path", "model_name", "bg_name"]].head())
