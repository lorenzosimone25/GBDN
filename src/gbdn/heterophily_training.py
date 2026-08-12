"""Training-only task dispatch for the official heterophily benchmark.

This module receives logits and labels for an already selected training
partition. It neither loads masks nor exposes test data, checkpoints, or
selection policy.
"""

from __future__ import annotations

import torch
from torch.nn import functional as F

from gbdn.heterophily_contract import resolve_dataset


def official_training_loss(
    dataset: str,
    logits: torch.Tensor,
    labels: torch.Tensor,
) -> torch.Tensor:
    """Compute exactly the loss frozen by the official dataset task type."""

    spec = resolve_dataset(dataset)
    if logits.ndim not in (1, 2) or labels.ndim != 1 or logits.shape[0] != labels.shape[0]:
        raise ValueError("training logits and labels must have one aligned example axis")
    if labels.dtype != torch.long:
        raise ValueError("training labels must use torch.long")
    if logits.device != labels.device:
        raise ValueError("training logits and labels must share a device")
    if not logits.is_floating_point() or not torch.isfinite(logits).all():
        raise ValueError("training logits must be finite floating-point values")
    if spec.task_type == "multiclass":
        if logits.shape != (labels.numel(), spec.class_count):
            raise ValueError("multiclass logit shape differs from the official head")
        if labels.numel() and (labels.min() < 0 or labels.max() >= spec.class_count):
            raise ValueError("multiclass labels are outside the official class range")
        return F.cross_entropy(logits, labels)
    if logits.shape == (labels.numel(), 1):
        logits = logits[:, 0]
    elif logits.shape != (labels.numel(),):
        raise ValueError("binary logit shape differs from the official one-logit head")
    if labels.numel() and not torch.all((labels == 0) | (labels == 1)):
        raise ValueError("binary labels must be exactly 0 or 1")
    return F.binary_cross_entropy_with_logits(logits, labels.to(dtype=logits.dtype))


__all__ = ["official_training_loss"]
