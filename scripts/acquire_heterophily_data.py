#!/usr/bin/env python3
"""Acquire or verify the pinned Platonov-five archives in the local data cache."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gbdn.heterophily_acquisition import (  # noqa: E402
    MANIFEST_RELATIVE_PATH,
    acquire_official_datasets,
    load_identity_manifest,
    verify_manifest_against_local_data,
)
from gbdn.heterophily_contract import ProtocolContractError  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("acquire", "download missing pinned archives, then verify and write identity manifest"),
        ("verify", "offline-verify all preexisting archives and write/compare the manifest"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--repository-root", type=Path, default=ROOT)
    validate = subparsers.add_parser(
        "validate-manifest", help="validate the existing manifest and its local archives"
    )
    validate.add_argument("--repository-root", type=Path, default=ROOT)
    validate.add_argument("--manifest", type=Path)
    return parser


def _summary(manifest: dict[str, object], manifest_path: Path) -> dict[str, object]:
    datasets = manifest["datasets"]
    assert isinstance(datasets, list)
    return {
        "datasets": [record["canonical_name"] for record in datasets],
        "manifest": str(manifest_path),
        "policy": manifest["policy"],
        "schema_version": manifest["schema_version"],
        "status": "verified",
    }


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        root = arguments.repository_root.resolve(strict=True)
        manifest_path = root / MANIFEST_RELATIVE_PATH
        if arguments.command == "validate-manifest":
            requested = arguments.manifest
            path = manifest_path if requested is None else requested.resolve(strict=True)
            if path != manifest_path:
                raise ProtocolContractError(
                    "dataset identity manifest must be the canonical results_submission report"
                )
            verify_manifest_against_local_data(root, path)
            manifest = load_identity_manifest(path)
        else:
            manifest = acquire_official_datasets(
                root,
                offline=arguments.command == "verify",
                write_manifest=True,
            )
        print(json.dumps(_summary(manifest, manifest_path), sort_keys=True))
        return 0
    except (OSError, ProtocolContractError) as error:
        print(f"dataset acquisition/verification failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
