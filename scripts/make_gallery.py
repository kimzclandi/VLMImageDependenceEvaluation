"""Generate a contact sheet from actual dataset PNGs; never fabricate screenshots."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from flywheel.io import read_jsonl


def main() -> None:
    rows = read_jsonl(Path("data/sample/samples.jsonl"))
    tasks = list(dict.fromkeys(row["task_type"] for row in rows))
    canvas = Image.new("RGB", (1080, 1020), "#edf3f7")
    draw = ImageDraw.Draw(canvas)
    title, body = ImageFont.load_default(size=28), ImageFont.load_default(size=18)
    draw.text(
        (24, 20), "Original synthetic scenes · six capability slices", font=title, fill="#10243a"
    )
    for i, task in enumerate(tasks):
        sample = next(
            row for row in rows if row["task_type"] == task and row["difficulty"] == "medium"
        )
        x, y = 24 + (i % 2) * 528, 82 + (i // 2) * 306
        image = Image.open(Path("data/sample") / sample["image_path"])
        image.thumbnail((360, 270))
        canvas.paste(image, (x + 66, y))
        draw.text(
            (x, y + 270),
            task.replace("_", " ").title() + " · gold: " + sample["ground_truth"],
            font=body,
            fill="#10243a",
        )
    Path("assets").mkdir(exist_ok=True)
    canvas.save("assets/scene-gallery.png")


if __name__ == "__main__":
    main()
