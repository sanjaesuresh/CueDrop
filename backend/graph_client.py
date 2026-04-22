"""Neo4j queries and writes."""

from __future__ import annotations

import os

from neo4j import AsyncGraphDatabase

from backend.models import DJModel, SetModel, TrackModel


class GraphClient:
    """Async Neo4j graph client for the CueDrop knowledge base."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "cuedrop_dev")
        self._driver = AsyncGraphDatabase.driver(
            self._uri, auth=(self._user, self._password)
        )

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    async def ensure_schema(self) -> None:
        """Create constraints, indexes, and full-text indexes."""
        statements = [
            "CREATE CONSTRAINT track_id_unique IF NOT EXISTS FOR (t:Track) REQUIRE t.track_id IS UNIQUE",
            "CREATE CONSTRAINT dj_name_unique IF NOT EXISTS FOR (d:DJ) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT set_id_unique IF NOT EXISTS FOR (s:Set) REQUIRE s.set_id IS UNIQUE",
            "CREATE INDEX track_artist_idx IF NOT EXISTS FOR (t:Track) ON (t.artist)",
            "CREATE INDEX track_bpm_idx IF NOT EXISTS FOR (t:Track) ON (t.bpm)",
            "CREATE INDEX track_genre_idx IF NOT EXISTS FOR (t:Track) ON (t.genre)",
            "CREATE FULLTEXT INDEX track_search IF NOT EXISTS FOR (n:Track) ON EACH [n.title, n.artist]",
        ]
        async with self._driver.session() as session:
            for stmt in statements:
                await session.run(stmt)

    # ------------------------------------------------------------------
    # Upserts
    # ------------------------------------------------------------------

    async def upsert_track(self, track_data: TrackModel) -> str:
        """MERGE a Track node by track_id; never overwrite with null."""
        query = """
        MERGE (t:Track {track_id: $track_id})
        SET t.title = $title,
            t.artist = $artist,
            t.remix = coalesce($remix, t.remix),
            t.bpm = coalesce($bpm, t.bpm),
            t.key = coalesce($key, t.key),
            t.energy = coalesce($energy, t.energy),
            t.genre = coalesce($genre, t.genre),
            t.intro_bars = coalesce($intro_bars, t.intro_bars),
            t.outro_bars = coalesce($outro_bars, t.outro_bars),
            t.duration_ms = coalesce($duration_ms, t.duration_ms),
            t.label = coalesce($label, t.label),
            t.has_dj_edit = coalesce($has_dj_edit, t.has_dj_edit),
            t.dj_edit_bpm = coalesce($dj_edit_bpm, t.dj_edit_bpm)
        RETURN t.track_id AS track_id
        """
        params = track_data.model_dump()
        # Genre is a list — pass empty list as null so coalesce preserves existing
        if not params.get("genre"):
            params["genre"] = None
        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["track_id"]

    async def upsert_transition(
        self, from_id: str, to_id: str, source: str
    ) -> None:
        """MERGE a TRANSITIONS_TO edge, incrementing frequency."""
        query = """
        MATCH (a:Track {track_id: $from_id}), (b:Track {track_id: $to_id})
        MERGE (a)-[r:TRANSITIONS_TO]->(b)
        SET r.frequency = coalesce(r.frequency, 0) + 1,
            r.sources = CASE
                WHEN $source IN coalesce(r.sources, [])
                THEN r.sources
                ELSE coalesce(r.sources, []) + [$source]
            END,
            r.bpm_delta = CASE
                WHEN a.bpm IS NOT NULL AND b.bpm IS NOT NULL
                THEN b.bpm - a.bpm
                ELSE r.bpm_delta
            END
        """
        async with self._driver.session() as session:
            await session.run(
                query, {"from_id": from_id, "to_id": to_id, "source": source}
            )

    async def upsert_dj(self, dj_data: DJModel) -> None:
        """MERGE a DJ node by name."""
        query = """
        MERGE (d:DJ {name: $name})
        SET d.genres = coalesce($genres, d.genres),
            d.profile_url = coalesce($profile_url, d.profile_url),
            d.set_count = coalesce($set_count, d.set_count)
        """
        params = dj_data.model_dump()
        if not params.get("genres"):
            params["genres"] = None
        async with self._driver.session() as session:
            await session.run(query, params)

    async def upsert_set(
        self, set_data: SetModel, tracks: list[TrackModel]
    ) -> None:
        """Create a Set node, link DJ, add CONTAINS edges, and create transitions."""
        # 1. Upsert all tracks
        track_ids: list[str] = []
        for track in tracks:
            tid = await self.upsert_track(track)
            track_ids.append(tid)

        # 2. Upsert DJ
        dj = DJModel(name=set_data.dj_name)
        await self.upsert_dj(dj)

        # 3. Create Set node and link to DJ
        set_query = """
        MERGE (s:Set {set_id: $set_id})
        SET s.event = coalesce($event, s.event),
            s.date = coalesce($date, s.date),
            s.venue = coalesce($venue, s.venue),
            s.source_url = coalesce($source_url, s.source_url),
            s.track_count = $track_count
        WITH s
        MATCH (d:DJ {name: $dj_name})
        MERGE (d)-[:PLAYED_SET]->(s)
        """
        params = set_data.model_dump()
        params["track_count"] = len(tracks)
        async with self._driver.session() as session:
            await session.run(set_query, params)

        # 4. Link tracks to set with position
        for i, tid in enumerate(track_ids):
            contains_query = """
            MATCH (s:Set {set_id: $set_id}), (t:Track {track_id: $track_id})
            MERGE (s)-[c:CONTAINS]->(t)
            SET c.position = $position
            """
            async with self._driver.session() as session:
                await session.run(
                    contains_query,
                    {
                        "set_id": set_data.set_id,
                        "track_id": tid,
                        "position": i,
                    },
                )

        # 5. Upsert transitions for consecutive track pairs
        source = set_data.source_url or set_data.set_id
        for i in range(len(track_ids) - 1):
            await self.upsert_transition(track_ids[i], track_ids[i + 1], source)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_track(self, track_id: str) -> dict | None:
        """Return a single track's properties, or None."""
        query = """
        MATCH (t:Track {track_id: $track_id})
        RETURN t
        """
        async with self._driver.session() as session:
            result = await session.run(query, {"track_id": track_id})
            record = await result.single()
            if record is None:
                return None
            return dict(record["t"])

    async def get_neighbors(
        self, track_id: str, limit: int = 20
    ) -> list[dict]:
        """Return adjacent tracks ordered by transition frequency desc."""
        query = """
        MATCH (t:Track {track_id: $track_id})-[r:TRANSITIONS_TO]-(neighbor:Track)
        RETURN neighbor, r.frequency AS frequency
        ORDER BY r.frequency DESC
        LIMIT $limit
        """
        async with self._driver.session() as session:
            result = await session.run(
                query, {"track_id": track_id, "limit": limit}
            )
            records = [record async for record in result]
            return [
                {**dict(rec["neighbor"]), "frequency": rec["frequency"]}
                for rec in records
            ]

    async def get_stats(self) -> dict:
        """Return total counts of tracks, transitions, sets, and DJs."""
        query = """
        OPTIONAL MATCH (t:Track)
        WITH count(t) AS tracks
        OPTIONAL MATCH ()-[r:TRANSITIONS_TO]->()
        WITH tracks, count(r) AS transitions
        OPTIONAL MATCH (s:Set)
        WITH tracks, transitions, count(s) AS sets
        OPTIONAL MATCH (d:DJ)
        RETURN tracks, transitions, sets, count(d) AS djs
        """
        async with self._driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            return {
                "tracks": record["tracks"],
                "transitions": record["transitions"],
                "sets": record["sets"],
                "djs": record["djs"],
            }

    async def search_tracks(
        self, query: str, limit: int = 10
    ) -> list[dict]:
        """Full-text search across track title and artist."""
        cypher = """
        CALL db.index.fulltext.queryNodes('track_search', $query)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """
        async with self._driver.session() as session:
            result = await session.run(
                cypher, {"query": query, "limit": limit}
            )
            records = [record async for record in result]
            return [
                {**dict(rec["node"]), "score": rec["score"]}
                for rec in records
            ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the Neo4j driver."""
        await self._driver.close()
