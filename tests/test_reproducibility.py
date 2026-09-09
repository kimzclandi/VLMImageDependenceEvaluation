import copy
import importlib.util
from pathlib import Path

import pytest
from PIL import Image

from flywheel.io import file_digest

spec = importlib.util.spec_from_file_location(
    "repro_check", Path("scripts/check_reproducibility.py")
)
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)


def encoded_pair(tmp_path):
    a, b = tmp_path / "new", tmp_path / "old"
    a.mkdir()
    b.mkdir()
    image = Image.new("RGB", (16, 16), (100, 120, 140))
    image.save(a / "image.png", compress_level=0)
    image.save(b / "image.png", compress_level=9)
    common = {"sample_id": "sample", "image_path": "image.png", "ground_truth": "yes"}
    new = {**common, "image_sha256": file_digest(a / "image.png")}
    old = {**common, "image_sha256": file_digest(b / "image.png")}
    return a, b, new, old


def test_lossless_compression_differences_are_explicit(tmp_path):
    a, b, new, old = encoded_pair(tmp_path)
    assert new["image_sha256"] != old["image_sha256"]
    aliases = repro.align_samples([new], [old], a, b)
    assert repro.stable(new, aliases) == old
    with pytest.raises(AssertionError, match="strict mode"):
        repro.align_samples([new], [old], a, b, strict_bytes=True)


@pytest.mark.parametrize("corruption", ["pixels", "metadata", "hash"])
def test_portable_check_never_masks_evidence_changes(tmp_path, corruption):
    a, b, new, old = encoded_pair(tmp_path)
    new = copy.deepcopy(new)
    if corruption == "pixels":
        image = Image.open(a / "image.png")
        image.putpixel((0, 0), (0, 0, 0))
        image.save(a / "image.png")
        new["image_sha256"] = file_digest(a / "image.png")
    elif corruption == "metadata":
        new["ground_truth"] = "no"
    else:
        new["image_sha256"] = "bad-hash"
    with pytest.raises(AssertionError):
        repro.align_samples([new], [old], a, b)
