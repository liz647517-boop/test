"""Local OCR for clear, horizontally aligned table images."""
import csv
import io
import shutil
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


def available_languages():
    if not shutil.which("tesseract"):
        raise RuntimeError("未安装表格识别引擎，请检查部署的 packages.txt 安装结果。")
    result = subprocess.run(["tesseract", "--list-langs"], capture_output=True,
                            text=True, check=True, timeout=15)
    return set(result.stdout.splitlines()[1:])


def extract_table(image_bytes, language="chi_sim"):
    """Return editable CSV and a low-confidence word count; never send images remotely."""
    if not set(language.split("+")).issubset(available_languages()):
        raise RuntimeError("缺少所选识别语言包，请检查部署的 packages.txt 安装结果。")
    with Image.open(io.BytesIO(image_bytes)) as source:
        if source.width * source.height > 25_000_000:
            raise ValueError("图片超过 2500 万像素，请先裁剪表格区域。")
        image = ImageOps.exif_transpose(source).convert("RGB")
    scale = min(2.0, 1000 / max(image.size))
    if scale > 1:
        image = image.resize((round(image.width * scale), round(image.height * scale)))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "table.png"
        ImageOps.grayscale(image).save(path)
        result = subprocess.run(["tesseract", str(path), "stdout", "-l", language,
                                 "--psm", "6", "tsv"], capture_output=True,
                                text=True, check=True, timeout=60)
    words = []
    for word in csv.DictReader(io.StringIO(result.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        if word.get("text", "").strip() and float(word["conf"]) >= 0:
            words.append({"text": word["text"].strip(), "x": int(word["left"]),
                          "y": int(word["top"]) + int(word["height"]) / 2,
                          "w": int(word["width"]), "h": int(word["height"]),
                          "conf": float(word["conf"])})
    if not words:
        raise ValueError("未识别到文字，请上传清晰、正向的表格截图。")
    rows = []
    for word in sorted(words, key=lambda w: w["y"]):
        if rows and abs(word["y"] - rows[-1][0]["y"]) < max(8, word["h"] * .6):
            rows[-1].append(word)
        else:
            rows.append([word])
    # Large horizontal gaps delimit cells; spaces inside a cell are preserved.
    grouped = []
    for row in rows:
        cells = []
        for word in sorted(row, key=lambda w: w["x"]):
            if cells and word["x"] - cells[-1]["end"] < max(18, word["h"] * 1.3):
                cells[-1]["text"] += " " + word["text"]
                cells[-1]["end"] = word["x"] + word["w"]
            else:
                cells.append({"text": word["text"], "x": word["x"], "end": word["x"] + word["w"]})
        grouped.append(cells)
    anchor = max(grouped, key=len)
    if len(anchor) < 2 or len(grouped) < 2:
        raise ValueError("未识别出至少两行两列的表格，请裁剪表格区域，避免合并单元格与复杂排版。")
    positions = [cell["x"] for cell in anchor]
    output = io.StringIO()
    writer = csv.writer(output)
    for row in grouped:
        values = [""] * len(anchor)
        for cell in row:
            index = min(range(len(positions)), key=lambda i: abs(positions[i] - cell["x"]))
            values[index] = (values[index] + " " + cell["text"]).strip()
        writer.writerow([re.sub(r"(?<=[\u3400-\u9fff]) +(?=[\u3400-\u9fff])", "", value) for value in values])
    return output.getvalue(), sum(word["conf"] < 60 for word in words)
