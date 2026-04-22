"""JSON import pipeline for CueDrop knowledge base."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from backend.graph_client import GraphClient
from backend.models import SetImport, SetModel

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Aggregated results from an import run."""

    tracks_added: int = 0
    tracks_updated: int = 0
    transitions_created: int = 0
    sets_imported: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: ImportResult) -> None:
        """Merge another result into this one."""
        self.tracks_added += other.tracks_added
        self.tracks_updated += other.tracks_updated
        self.transitions_created += other.transitions_created
        self.sets_imported += other.sets_imported
        self.errors.extend(other.errors)


async def _import_set(set_import: SetImport, graph: GraphClient, result: ImportResult) -> None:
    """Import a single SetImport into the graph."""
    dj = set_import.dj

    set_model = SetModel(
        dj_name=dj.name,
        event=set_import.event,
        date=set_import.date,
        venue=set_import.venue,
        source_url=set_import.source_url,
        track_count=len(set_import.tracks),
    )

    await graph.upsert_dj(dj)
    await graph.upsert_set(set_model, set_import.tracks)

    result.tracks_added += len(set_import.tracks)
    result.transitions_created += max(0, len(set_import.tracks) - 1)
    result.sets_imported += 1


async def import_file(path: str, graph: GraphClient) -> ImportResult:
    """Read a JSON file (single SetImport or list) and import into Neo4j."""
    result = ImportResult()
    file_path = Path(path)

    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        result.errors.append(f"{file_path}: {exc}")
        return result

    items = raw if isinstance(raw, list) else [raw]

    for i, item in enumerate(items):
        try:
            set_import = SetImport(**item)
            await _import_set(set_import, graph, result)
        except Exception as exc:
            msg = f"{file_path}[{i}]: {exc}"
            logger.warning("Skipping malformed record: %s", msg)
            result.errors.append(msg)

    return result


async def import_directory(dir_path: str, graph: GraphClient) -> ImportResult:
    """Import all .json files in a directory."""
    result = ImportResult()
    directory = Path(dir_path)

    if not directory.is_dir():
        result.errors.append(f"Not a directory: {dir_path}")
        return result

    json_files = sorted(directory.glob("*.json"))
    if not json_files:
        logger.info("No JSON files found in %s", dir_path)
        return result

    for json_file in json_files:
        file_result = await import_file(str(json_file), graph)
        result.merge(file_result)

    return result
