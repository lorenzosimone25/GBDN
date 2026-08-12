from __future__ import annotations

import pytest
import torch
from torch.nn import functional as F

from gbdn.heterophily_contract import DATASET_REGISTRY
from gbdn.heterophily_training import official_training_loss


@pytest.mark.parametrize("dataset", ("Roman-empire", "Amazon-ratings"))
def test_multiclass_training_loss_is_exact_cross_entropy(dataset):
    classes = DATASET_REGISTRY[dataset].class_count
    logits = torch.linspace(-1.2, 1.3, 4 * classes, dtype=torch.float64).reshape(4, classes)
    labels = torch.tensor([0, 1, classes - 1, 0], dtype=torch.long)
    torch.testing.assert_close(
        official_training_loss(dataset, logits, labels),
        F.cross_entropy(logits, labels),
        rtol=0,
        atol=0,
    )


@pytest.mark.parametrize("dataset", ("Minesweeper", "Tolokers", "Questions"))
@pytest.mark.parametrize("column", (False, True))
def test_binary_training_loss_is_exact_one_logit_bce(dataset, column):
    logits = torch.tensor([-0.7, 0.1, 1.2, -1.1], dtype=torch.float64)
    labels = torch.tensor([0, 1, 1, 0], dtype=torch.long)
    observed = official_training_loss(dataset, logits[:, None] if column else logits, labels)
    expected = F.binary_cross_entropy_with_logits(logits, labels.to(torch.float64))
    torch.testing.assert_close(observed, expected, rtol=0, atol=0)


def test_loss_dispatch_rejects_universal_or_malformed_heads():
    with pytest.raises(ValueError, match="multiclass logit shape"):
        official_training_loss(
            "Roman-empire", torch.zeros(3), torch.tensor([0, 1, 2], dtype=torch.long)
        )
    with pytest.raises(ValueError, match="binary logit shape"):
        official_training_loss(
            "Minesweeper", torch.zeros(3, 2), torch.tensor([0, 1, 0], dtype=torch.long)
        )
    with pytest.raises(ValueError, match="class range"):
        official_training_loss(
            "Amazon-ratings", torch.zeros(2, 5), torch.tensor([0, 5], dtype=torch.long)
        )
    with pytest.raises(ValueError, match="exactly 0 or 1"):
        official_training_loss(
            "Questions", torch.zeros(2), torch.tensor([0, 2], dtype=torch.long)
        )
    with pytest.raises(ValueError, match="torch.long"):
        official_training_loss("Tolokers", torch.zeros(2), torch.tensor([0.0, 1.0]))
