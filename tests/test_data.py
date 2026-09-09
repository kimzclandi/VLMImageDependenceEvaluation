import copy
from pathlib import Path

import pytest
from PIL import Image, ImageColor

from flywheel.data import COLORS, generate, question, relation, solve, validate
from flywheel.io import digest, safe_path


def test_generator_reproducibility_and_pixel_metadata(tmp_path, config):
    a, b = generate(tmp_path / "a", config), generate(tmp_path / "b", config)
    assert digest(a) == digest(b)
    assert len(a) == 36
    assert (
        validate(a, tmp_path / "a", Path("schemas/sample.schema.json"))["cross_split_images"] == 0
    )
    assert {r["task_type"] for r in a} == set(config["task_importance"])
    for row in a:
        image = Image.open(tmp_path / "a" / row["image_path"])
        for obj in row["scene_metadata"]["objects"]:
            assert image.getpixel((obj["x"], obj["y"])) == ImageColor.getrgb(COLORS[obj["color"]])
        assert row["question"] == question(row["query"])


def test_pair_changes_one_color_only(tmp_path, config):
    samples = generate(tmp_path, config)
    for a, b in zip(samples[::2], samples[1::2], strict=True):
        assert a["split"] == b["split"]
        if a["task_type"] == "spatial_relation":
            assert a["image_sha256"] == b["image_sha256"]
        else:
            original, edited = a["scene_metadata"], copy.deepcopy(b["scene_metadata"])
            assert original["objects"][0]["color"] != edited["objects"][0]["color"]
            edited["objects"][0]["color"] = original["objects"][0]["color"]
            assert original == edited
        if a["task_type"] in ("attribute_binding", "counterfactual"):
            assert a["ground_truth"] == "yes" and b["ground_truth"] == "no"


def test_independent_handwritten_oracle_cases():
    scene = {
        "objects": [
            {"id": "o1", "x": 80, "y": 100, "color": "red", "shape": "circle", "size": "small"},
            {"id": "o2", "x": 200, "y": 280, "color": "red", "shape": "square", "size": "large"},
            {"id": "o3", "x": 400, "y": 100, "color": "blue", "shape": "circle", "size": "small"},
        ]
    }
    assert solve(scene, {"kind": "count", "filters": {"color": "red"}}) == "2"
    assert solve(scene, {"kind": "count", "filters": {"color": "yellow"}}) == "0"
    assert solve(scene, {"kind": "select", "filters": {"shape": "circle"}}) == "o1,o3"
    assert (
        solve(
            scene,
            {"kind": "select", "filters": {"shape": "circle"}, "relation": "left", "anchor": "o2"},
        )
        == "o1"
    )
    assert solve(scene, {"kind": "relation", "a": "o1", "b": "o2", "relation": "above"}) == "yes"
    assert relation({"x": 0, "y": 0}, {"x": 150, "y": 0}, "adjacent")
    assert not relation({"x": 0, "y": 0}, {"x": 151, "y": 0}, "adjacent")


@pytest.mark.parametrize(
    "corruption", ["label", "id", "split", "image", "duplicate", "question", "pixels"]
)
def test_corruption_is_rejected(tmp_path, config, corruption):
    rows = generate(tmp_path, config)
    if corruption == "label":
        rows[0]["ground_truth"] = "not-the-answer"
    elif corruption == "id":
        rows[1]["sample_id"] = rows[0]["sample_id"]
    elif corruption == "split":
        rows[1]["split"] = "holdout"
    elif corruption == "image":
        (tmp_path / rows[0]["image_path"]).write_bytes(b"broken")
    elif corruption == "question":
        rows[0]["question"] = "A different question"
    elif corruption == "pixels":
        from flywheel.io import file_digest

        image_path = tmp_path / rows[0]["image_path"]
        image = Image.open(image_path)
        image.putpixel((80, 112), (0, 0, 0))
        image.save(image_path)
        rows[0]["image_sha256"] = file_digest(image_path)
    else:
        rows.append({**rows[0], "sample_id": "another-id"})
    with pytest.raises(ValueError):
        validate(rows, tmp_path, Path("schemas/sample.schema.json"))


@pytest.mark.parametrize("relative", ["../outside.png", "/outside.png"])
def test_path_traversal_is_rejected(tmp_path, relative):
    with pytest.raises(ValueError):
        safe_path(tmp_path, relative)
