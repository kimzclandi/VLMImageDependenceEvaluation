from pathlib import Path

import pytest

from flywheel.io import read_json


@pytest.fixture
def config():
    value = read_json(Path("configs/demo.json"))
    return {**value, "groups_per_task": 3, "bootstrap_replicates": 100, "selection_budget": 6}
