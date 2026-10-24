import numpy as np
import pandas as pd

from adapters import INTERIM_ROOT
SEED = 42

def main():
    manifest_path = INTERIM_ROOT / "manifest.csv"
    df = pd.read_csv(manifest_path)

    valid = df["validation_status"] == "valid"

    models = np.array(sorted(df.loc[valid, "model_name"].unique()))

    if len(models) < 3:
        raise ValueError("Cần ít nhất 3 trang gốc để chia 3 tập.")

    # Xáo trộn danh sách trang gốc theo seed cố định.
    rng = np.random.default_rng(SEED)
    rng.shuffle(models)

    # Với 30 trang gốc: 5 test, 4 validation, 21 train.
    n_test = max(1, int(np.ceil(len(models) * 0.15)))
    n_val = max(1, int(np.floor(len(models) * 0.15)))

    test_models = set(models[:n_test])
    val_models = set(models[n_test:n_test + n_val])
    train_models = set(models[n_test + n_val:])

    # Bảo đảm không có trang gốc nào nằm trong hai tập.
    assert train_models.isdisjoint(val_models)
    assert train_models.isdisjoint(test_models)
    assert val_models.isdisjoint(test_models)

    # Tạo cột split; ảnh không hợp lệ sẽ để trống.
    df["split"] = ""

    df.loc[
        valid & df["model_name"].isin(train_models), "split"
    ] = "train"

    df.loc[
        valid & df["model_name"].isin(val_models), "split"
    ] = "val"

    df.loc[
        valid & df["model_name"].isin(test_models), "split"
    ] = "test"

    # Tất cả ảnh hợp lệ phải được gán vào một trong ba tập.
    assert df.loc[valid, "split"].isin(["train", "val", "test"]).all()

    output_path = INTERIM_ROOT / "manifest_with_split.csv"
    df.to_csv(output_path, index=False)

    print("Seed:", SEED)
    print("Số trang gốc:", len(models))

    for name, group in [
        ("train", train_models),
        ("val", val_models),
        ("test", test_models),
    ]:
        print()
        print("Tập:", name)
        print("Số trang gốc:", len(group))
        print("Số ảnh:", int((df["split"] == name).sum()))
        print("Danh sách trang gốc:", sorted(group))

    print()
    print("Đã lưu:", output_path)


if __name__ == "__main__":
    main()
