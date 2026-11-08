"""Thử tinh chỉnh Tesseract trên các dòng FUNSD và so sánh validation.

Không dùng FUNSD testing_data. Bộ lọc chỉ là tự động và cần kiểm tra bằng mắt.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import argparse
import csv
import json
import os
import random
import shutil
import subprocess

import cv2

from metrics import normalize_text, edit_distance
from recognize import TESSERACT_PATH


ROOT = Path(__file__).resolve().parents[3]
TESSERACT_DIR = TESSERACT_PATH.parent
BEST = ROOT / "models" / "tessdata_best" / "eng.traineddata"
OUTPUT = ROOT / "artifacts" / "week3" / "funsd_finetune"
ENV = os.environ.copy()
ENV["OMP_THREAD_LIMIT"] = "1"


def run(command):
    result = subprocess.run([str(part) for part in command], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", env=ENV)
    if result.returncode:
        raise RuntimeError("Lệnh lỗi: " + " ".join(map(str, command)) + "\n" + result.stderr[-6000:])
    return result


def recognize(image, tessdata, language):
    return normalize_text(run([TESSERACT_PATH, image, "stdout", "--tessdata-dir", tessdata,
                               "-l", language, "--psm", "7"]).stdout)


def sample_by_page(rows, limit, seed):
    """Chọn đều theo trang để một biểu mẫu không chiếm phần lớn mẫu."""
    rng = random.Random(seed)
    pages = {}
    for row in rows:
        pages.setdefault(row["page"], []).append(row)
    groups = list(pages.values())
    rng.shuffle(groups)
    for group in groups:
        rng.shuffle(group)
    selected = []
    while groups and len(selected) < limit:
        remaining = []
        for group in groups:
            if len(selected) < limit:
                selected.append(group.pop())
            if group:
                remaining.append(group)
        groups = remaining
    return selected


def write_lstm_input(source, row, output):
    image_path = source / row["image"]
    target = output / row["split"] / image_path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image_path, target)
    text = row["text"]
    image = cv2.imread(str(target), cv2.IMREAD_GRAYSCALE)
    height, width = image.shape
    # Định dạng hộp một dòng theo tesstrain: mỗi ký tự dùng khung toàn dòng.
    box = "".join(f"{char} 0 0 {width} {height} 0\n" for char in text)
    box += f"\t 0 0 {width} {height} 0\n"
    target.with_suffix(".box").write_text(box, encoding="utf-8")
    config = TESSERACT_DIR / "tessdata" / "configs" / "lstm.train"
    run([TESSERACT_PATH, target, target.with_suffix(""), "--tessdata-dir", BEST.parent,
         "-l", "eng", "--psm", "13", config])
    lstmf = target.with_suffix(".lstmf")
    if not lstmf.is_file() or not lstmf.stat().st_size:
        raise ValueError("Không tạo được dữ liệu LSTM: " + str(target))
    return lstmf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Thư mục tạo bởi prepare_funsd_training.py")
    parser.add_argument("--train-count", type=int, default=720)
    parser.add_argument("--val-count", type=int, default=180)
    parser.add_argument("--iterations", type=int, default=400)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", help="Dùng lại baseline.csv và các file LSTM của lần chạy chưa hoàn tất")
    args = parser.parse_args()
    source = Path(args.data).resolve()
    if not BEST.is_file():
        raise FileNotFoundError("Cần mô hình tessdata_best/eng.traineddata: " + str(BEST))
    with (source / "manifest.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    train = sample_by_page([r for r in rows if r["split"] == "train"], args.train_count, 42)
    validation = sample_by_page([r for r in rows if r["split"] == "val"], args.val_count, 43)
    if not train or not validation or {r["page"] for r in train} & {r["page"] for r in validation}:
        raise ValueError("Tập train/validation rỗng hoặc trùng trang.")
    folder = Path(args.resume).resolve() if args.resume else OUTPUT / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if args.resume and (folder / "run_info.json").is_file():
        previous = json.loads((folder / "run_info.json").read_text(encoding="utf-8"))
        if previous.get("complete"):
            raise ValueError("Lần chạy này đã hoàn tất; hãy tạo lần chạy mới để tránh ghi đè kết quả.")
    folder.mkdir(parents=True, exist_ok=bool(args.resume))
    info = {"complete": False, "source": str(source), "selection": "Chọn đều theo trang, seed 42/43",
            "max_train_cer": 0.15, "warning": "Tập train lọc theo model gốc, validation không lọc. "
            "Đây là thử nghiệm, không chứng minh model tốt hơn trên ảnh chụp."}
    (folder / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Lần chạy:", folder, flush=True)

    def get_base(row):
        prediction = recognize(source / row["image"], BEST.parent, "eng")
        reference = normalize_text(row["text"])
        return {**row, "baseline": prediction, "char_errors": edit_distance(reference, prediction),
                "char_count": len(reference), "word_errors": edit_distance(reference.split(), prediction.split()),
                "word_count": len(reference.split())}

    if args.resume:
        with (folder / "baseline.csv").open(encoding="utf-8", newline="") as file:
            scored = list(csv.DictReader(file))
        for row in scored:
            for key in ("char_errors", "char_count", "word_errors", "word_count"):
                row[key] = int(row[key])
        if [(r["split"], r["image"]) for r in scored] != [(r["split"], r["image"]) for r in train + validation]:
            raise ValueError("Tham số hoặc dữ liệu không khớp với lần chạy cần tiếp tục.")
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            scored = []
            for item in pool.map(get_base, train + validation):
                scored.append(item)
                if len(scored) % 100 == 0:
                    print("Đã kiểm tra nhãn:", len(scored), "/", len(train) + len(validation), flush=True)
    selected_train = [r for r in scored if r["split"] == "train"
                      and r["char_errors"] / r["char_count"] <= 0.15]
    val = [r for r in scored if r["split"] == "val"]
    if len(selected_train) < 50:
        raise ValueError("Quá ít dòng train qua bộ lọc.")
    with (folder / "baseline.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(scored[0]))
        writer.writeheader()
        writer.writerows(scored)
    print("Dòng train sau lọc:", len(selected_train), "/", len(train), "- validation:", len(val), flush=True)
    if args.resume:
        paths = [folder / r["split"] / Path(r["image"]).with_suffix(".lstmf").name
                 for r in selected_train + val]
        if any(not path.is_file() or not path.stat().st_size for path in paths):
            raise FileNotFoundError("Thiếu file LSTM để tiếp tục.")
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            paths = []
            for path in pool.map(lambda row: write_lstm_input(source, row, folder), selected_train + val):
                paths.append(path)
                if len(paths) % 100 == 0:
                    print("Đã tạo LSTM:", len(paths), "/", len(selected_train) + len(val), flush=True)
    train_paths = paths[:len(selected_train)]
    val_paths = paths[len(selected_train):]
    for split, split_paths in (("train", train_paths), ("val", val_paths)):
        # lstmtraining đọc danh sách LF; CRLF trên Windows bị hiểu thành ký tự trong tên file.
        (folder / (split + ".list")).write_bytes(("\n".join(p.as_posix() for p in split_paths) + "\n").encode("utf-8"))
    base_lstm = folder / "eng.lstm"
    run([TESSERACT_DIR / "combine_tessdata.exe", "-e", BEST, base_lstm])
    checkpoint = folder / "funsd"
    command = [TESSERACT_DIR / "lstmtraining.exe", "--continue_from", base_lstm,
               "--traineddata", BEST, "--model_output", checkpoint,
               "--train_listfile", folder / "train.list", "--eval_listfile", folder / "val.list",
               "--learning_rate", "0.0001", "--max_iterations", str(args.iterations), "--debug_interval", "0"]
    print("Bắt đầu huấn luyện:", args.iterations, "iterations", flush=True)
    # Ghi log ngay khi chạy để vẫn xem được lỗi nếu quá trình bị dừng.
    with (folder / "training.log").open("w", encoding="utf-8") as log:
        training = subprocess.run([str(part) for part in command], stdout=log,
                                  stderr=subprocess.STDOUT, env=ENV)
    if training.returncode:
        raise RuntimeError("Huấn luyện lỗi; xem " + str(folder / "training.log"))
    model_dir = folder / "tessdata"
    model_dir.mkdir(exist_ok=True)
    model = model_dir / "funsd_eng.traineddata"
    run([TESSERACT_DIR / "lstmtraining.exe", "--stop_training", "--continue_from",
         str(checkpoint) + "_checkpoint", "--traineddata", BEST, "--model_output", model])
    results = []
    for row in val:
        predicted = recognize(source / row["image"], model_dir, "funsd_eng")
        installed = recognize(source / row["image"], TESSERACT_DIR / "tessdata", "eng")
        ref = normalize_text(row["text"])
        results.append({**row, "finetuned": predicted, "finetuned_char_errors": edit_distance(ref, predicted),
                        "finetuned_word_errors": edit_distance(ref.split(), predicted.split()),
                        "installed_eng": installed, "installed_char_errors": edit_distance(ref, installed),
                        "installed_word_errors": edit_distance(ref.split(), installed.split())})
    with (folder / "validation.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    chars = sum(r["char_count"] for r in results)
    words = sum(r["word_count"] for r in results)
    info.update(complete=True, train_candidates=len(train), train_lines=len(selected_train), val_lines=len(val),
                baseline_cer=sum(r["char_errors"] for r in results) / chars,
                finetuned_cer=sum(r["finetuned_char_errors"] for r in results) / chars,
                baseline_wer=sum(r["word_errors"] for r in results) / words,
                finetuned_wer=sum(r["finetuned_word_errors"] for r in results) / words,
                installed_eng_cer=sum(r["installed_char_errors"] for r in results) / chars,
                installed_eng_wer=sum(r["installed_word_errors"] for r in results) / words,
                model=str(model), iterations=args.iterations)
    (folder / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
