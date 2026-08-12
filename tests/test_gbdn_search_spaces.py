from __future__ import annotations

import copy
from pathlib import Path

import pytest
import torch

from gbdn.artifacts import ArtifactValidationError
from gbdn.heterophily_contract import DATASET_REGISTRY
from gbdn.heterophily_worker import (
    FrozenMethodConfig,
    _build_model,
    _optimizer,
    _resource_count,
    _validate_model,
    _validate_optimizer,
    _validate_training,
)
from gbdn.screening_contract import enumerate_candidates, load_search_space


ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOT = ROOT / "configs" / "submission" / "search_spaces"
PATHS = {
    method: f"configs/submission/search_spaces/{method}.json"
    for method in ("ChebNet", "TightGBDN", "ProductSumGBDN", "GBDNPlus")
}
SPMV_TIERS = (2, 6, 10)
COMMON_TUNED = {
    "model.hidden_channels": (32, 64, 128),
    "optimizer.learning_rate": (0.001, 0.005, 0.01),
    "optimizer.weight_decay": (0.0, 0.0005, 0.005),
}
COMMON_FIXED = {
    "optimizer.amsgrad": (False,),
    "optimizer.betas": ([0.9, 0.999],),
    "optimizer.eps": (1e-8,),
    "optimizer.name": ("Adam",),
    "training.checkpoint_tie_breaker": ("earliest",),
    "training.deterministic_algorithms": (True,),
    "training.gradient_clip_norm": (None,),
    "training.max_epochs": (1000,),
    "training.min_delta": (0.0,),
    "training.patience": (100,),
    "training.precision": ("float32",),
    "training.selection_source": ("validation_only",),
}


def _spaces():
    return {
        method: load_search_space(ROOT / relative, source_path=relative)
        for method, relative in PATHS.items()
    }


def _parameters(space):
    return {parameter.path: parameter for parameter in space.parameters}


def _assert_alignment(spaces) -> None:
    parameters = {method: _parameters(space) for method, space in spaces.items()}
    for expected in (COMMON_TUNED, COMMON_FIXED):
        for path, values in expected.items():
            for method in spaces:
                assert parameters[method][path].values == values
    for path in COMMON_TUNED:
        assert all(parameters[method][path].role == "TUNED" for method in spaces)
    for path in COMMON_FIXED:
        assert all(parameters[method][path].role == "FIXED" for method in spaces)

    assert parameters["ChebNet"]["model.K"].values == (2, 4, 6)
    assert tuple(2 * (degree - 1) for degree in parameters["ChebNet"]["model.K"].values) == SPMV_TIERS
    for method in ("TightGBDN", "ProductSumGBDN"):
        assert parameters[method]["model.K"].values == (1, 3, 5)
        assert parameters[method]["model.num_layers"].values == (2,)
        assert tuple(2 * degree for degree in parameters[method]["model.K"].values) == SPMV_TIERS
        assert parameters[method]["model.num_roots"].values == (1,)
    assert parameters["GBDNPlus"]["model.K"].values == (2, 6, 10)
    assert parameters["GBDNPlus"]["model.num_layers"].values == (2,)
    assert parameters["GBDNPlus"]["model.K"].values == SPMV_TIERS

    for method in ("TightGBDN", "ProductSumGBDN", "GBDNPlus"):
        assert parameters[method]["model.convention"].values == ("forward",)
        assert parameters[method]["model.r_max"].values == (0.95,)
    for method in ("ChebNet", "GBDNPlus"):
        dropout = parameters[method]["model.dropout"]
        assert dropout.role == "TUNED"
        assert dropout.values == (0.0, 0.3, 0.5)
    for method in ("TightGBDN", "ProductSumGBDN"):
        assert "model.dropout" not in parameters[method]


def test_repository_spaces_are_bounded_and_resource_aligned():
    spaces = _spaces()
    _assert_alignment(spaces)
    assert {method: space.candidate_count for method, space in spaces.items()} == {
        "ChebNet": 243,
        "TightGBDN": 81,
        "ProductSumGBDN": 81,
        "GBDNPlus": 243,
    }
    assert min(space.candidate_count for space in spaces.values()) == 81


@pytest.mark.parametrize("method", ["TightGBDN", "ProductSumGBDN", "GBDNPlus"])
def test_every_gbdn_candidate_passes_actual_worker_validators_and_cpu_builders(method):
    space = _spaces()[method]
    candidates = enumerate_candidates(space)
    assert len(candidates) == space.candidate_count
    for candidate in candidates:
        model_config = _validate_model(method, dict(candidate.configuration["model"]))
        optimizer_config = _validate_optimizer(dict(candidate.configuration["optimizer"]))
        training_config = _validate_training(dict(candidate.configuration["training"]))
        for dataset in DATASET_REGISTRY:
            frozen = FrozenMethodConfig(
                method=method,
                dataset=dataset,
                model=model_config,
                optimizer=optimizer_config,
                training=training_config,
                source_path=space.source_path,
                source_sha256=space.source_sha256,
            )
            model = _build_model(frozen)
            assert all(parameter.device.type == "cpu" for parameter in model.parameters())
            before_forward = {id(parameter) for parameter in model.parameters() if parameter.requires_grad}
            optimizer = _optimizer(model, optimizer_config)
            optimized = {
                id(parameter)
                for group in optimizer.param_groups
                for parameter in group["params"]
            }
            assert optimized == before_forward
            resources = _resource_count(model, frozen)
            assert resources["feature_matrix_spmvs_per_forward"] in SPMV_TIERS
            assert resources["trainable_parameters"] == sum(
                parameter.numel() for parameter in model.parameters() if parameter.requires_grad
            )
            del optimizer, model


@pytest.mark.parametrize(
    ("method", "section", "field", "bad_value", "message"),
    [
        ("TightGBDN", "model", "K", 0, "positive integer"),
        ("ProductSumGBDN", "model", "r_max", 1.0, "strictly"),
        ("GBDNPlus", "model", "convention", "adjoint", "forward or inverse"),
        ("TightGBDN", "optimizer", "name", "SGD", "Adam/AdamW"),
        ("GBDNPlus", "optimizer", "learning_rate", 0.0, "positive"),
        ("ProductSumGBDN", "training", "selection_source", "test", "validation_only"),
    ],
)
def test_actual_worker_rejects_adversarial_search_values(
    method, section, field, bad_value, message
):
    candidate = enumerate_candidates(_spaces()[method])[0]
    configuration = copy.deepcopy(candidate.configuration)
    configuration[section][field] = bad_value
    validator = {
        "model": lambda value: _validate_model(method, value),
        "optimizer": _validate_optimizer,
        "training": _validate_training,
    }[section]
    with pytest.raises(ArtifactValidationError, match=message):
        validator(configuration[section])


def test_actual_worker_rejects_missing_method_specific_field():
    candidate = enumerate_candidates(_spaces()["TightGBDN"])[0]
    model = dict(candidate.configuration["model"])
    del model["num_roots"]
    with pytest.raises(ArtifactValidationError, match="keys do not match"):
        _validate_model("TightGBDN", model)


def test_alignment_audit_fails_if_one_method_silently_changes_common_width():
    spaces = _spaces()
    changed = copy.deepcopy(spaces)
    parameters = list(changed["TightGBDN"].parameters)
    index = next(i for i, parameter in enumerate(parameters) if parameter.path == "model.hidden_channels")
    parameters[index] = type(parameters[index])(
        path="model.hidden_channels", role="TUNED", values=(32, 64)
    )
    changed["TightGBDN"] = type(changed["TightGBDN"])(
        method=changed["TightGBDN"].method,
        source_path=changed["TightGBDN"].source_path,
        source_sha256=changed["TightGBDN"].source_sha256,
        parameters=tuple(parameters),
        candidate_count=changed["TightGBDN"].candidate_count,
    )
    with pytest.raises(AssertionError):
        _assert_alignment(changed)


def test_candidate_validation_does_not_request_cuda(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: (_ for _ in ()).throw(AssertionError("CUDA queried")))
    candidate = enumerate_candidates(_spaces()["TightGBDN"])[0]
    frozen = FrozenMethodConfig(
        method="TightGBDN",
        dataset="Minesweeper",
        model=_validate_model("TightGBDN", dict(candidate.configuration["model"])),
        optimizer=_validate_optimizer(dict(candidate.configuration["optimizer"])),
        training=_validate_training(dict(candidate.configuration["training"])),
        source_path="cpu-audit",
        source_sha256="0" * 64,
    )
    model = _build_model(frozen)
    _optimizer(model, frozen.optimizer)
