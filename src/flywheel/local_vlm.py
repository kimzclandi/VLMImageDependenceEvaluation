"""Pixels-only public model adapter. No sample, oracle, query or metadata argument."""

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from flywheel.io import digest

MODEL = "HuggingFaceTB/SmolVLM-256M-Instruct"
REVISION = "7e3e67edbbed1bf9888184d9df282b700a323964"
PROMPTS = {
    "baseline": "Answer the image question. Give only the short answer. ",
    "observe": "Carefully inspect each visible object and its color, shape and position. "
    "Check all objects against the question before answering. Give only the short answer. ",
}


@dataclass(frozen=True, slots=True)
class VisualInput:
    image: bytes
    question: str


def cache_key(item, arm, identity):
    return digest([hashlib.sha256(item.image).hexdigest(), item.question, PROMPTS[arm], identity])


class LocalVLM:
    def __init__(self, snapshot: Path):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        torch.set_num_threads(4)
        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(
            snapshot, local_files_only=True, trust_remote_code=False
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.float32,
            attn_implementation="eager",
        ).eval()

    def predict(self, item: VisualInput, arm: str):
        if type(item) is not VisualInput:
            raise TypeError("Only VisualInput is allowed")
        text = self.processor.apply_chat_template(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": PROMPTS[arm] + item.question},
                    ],
                }
            ],
            add_generation_prompt=True,
        )
        image = Image.open(io.BytesIO(item.image)).convert("RGB")
        inputs = self.processor(text=text, images=[image], return_tensors="pt")
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=16)
        return self.processor.batch_decode(
            output[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )[0]
