#!/usr/bin/env python3
"""Seed this deployment's writable mounts without replacing live files."""

from pathlib import Path
import shutil


def bootstrap_runtime(root: Path) -> None:
    sources = [(root / "deployment/config.yaml", root / "runtime/config/config.yaml")]
    workspace = root / "mind_data"
    sources.extend(
        (source, root / "runtime/workspace" / source.relative_to(workspace))
        for source in workspace.rglob("*") if source.is_file()
    )
    for source, destination in sources:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as incoming:
            try:
                with destination.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
            except FileExistsError:
                pass


if __name__ == "__main__":
    bootstrap_runtime(Path(__file__).resolve().parents[1])
