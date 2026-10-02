# ADR-0001: SS2 is a content layer on the ported original engine

## Status

Accepted

## Date

2026-10-02

## Decision Makers

Project owner (engine choice, 2026-03-29); Claude (content-layer design, 2026-10-01).

## Context

### Problem Statement

Silent Storm 2 reuses the original game's 29,000+ assets and its destruction,
ballistics and AI systems. Those only exist as the original C++ engine and its
proprietary data formats, so the sequel has to run on that engine. The question
is how SS2 relates to the engine and to the retail data: where SS2's own content
lives, and how it reaches the game.

### Current State

- The engine (Nival's January 2003 source snapshot) has been ported to a modern
  compiler in a separate repository and plays the retail game from an owned
  Steam install. That port is maintained separately as the "remaster".
- Retail data is one database file, `game.db` (155 tables, 231,522 rows), plus
  resource packs (`res/*.res`). A map is not a file: it is a set of rows that
  place building templates, objects, units and waypoints in a "variant", plus a
  Lua script row and a few resources keyed by the variant's ID.
- The original map editor is not part of the port.

### Constraints

- Nival's source and data licence is non-commercial and does not allow
  redistributing the retail data. The SS2 repository must not contain retail
  data, only instructions to derive from a player's own copy.
- The engine is changing underneath us (the remaster effort). SS2 must not fork
  it casually.
- One person plus AI assistance: content has to be text that can be diffed,
  reviewed and generated, not binary files edited in a GUI.

### Requirements

- Adding a mission must not require the map editor.
- The retail campaigns must keep working in an SS2 build (nothing retail is
  modified).
- A build must be reproducible from: this repository, an owned retail install,
  and an engine build.

## Decision

SS2 is authored as **text sources in this repository** (`game/`) and compiled by
**Python tools** (`tools/`) onto a **copy** of the player's retail data. The
compiled result runs on the ported engine unchanged.

### Architecture

```
 owned retail install (read-only)        this repo                    engine port
 ┌───────────────────────────┐      ┌──────────────────┐         ┌───────────────┐
 │ game.db, res/*.res,       │      │ game/missions/   │         │ build/Game.exe│
 │ cfg/, scripts/            │      │   mission.toml   │         └──────┬────────┘
 └────────────┬──────────────┘      │   script.lua     │                │
              │ tools/stage.py      └────────┬─────────┘                │
              ▼                              │ tools/content.py         │
        build/run/  ◄────────────────────────┴──────────────────────────┘
        ├─ SS2.exe            (engine exe, renamed)
        ├─ game.db            (retail copy + engine UI patches + SS2 rows)
        ├─ res/               (retail packs, untouched copies)
        └─ Terrain/ Buildings/ Waypoints/ ...   (SS2 loose resources)
```

### Key Interfaces

- **Database rows.** `tools/ssdb.py` reads and writes `game.db`. SS2 only ever
  adds rows, in ID ranges retail does not use:
  - per mission slot N: variant, template and script IDs are `50000 + N`
    (kept below 65536 because some resource keys carry a part number in the
    high 16 bits);
  - all other rows: `1000000 + N*10000 + n`.
- **Loose resources.** The engine opens `<PackName>\<id>` relative to the
  working directory when an ID is not in `res/<PackName>.res` (for resources
  loaded through `CResourceOpener`: Terrain, Buildings, Waypoints, Units,
  Groups and others). SS2 ships its resources this way and never rewrites a
  retail pack. Loaders that test `DoesExist` first (Geometries, AIGeometries)
  only see packs, so new 3D models are out of reach until the engine changes.
- **Level geometry.** A mission names a retail variant as its "shell". The
  compiler copies the shell's placement rows under new IDs and copies its
  Terrain/Buildings resources to loose files under the new variant ID. The
  mission then adds its own units, waypoints, cameras and Lua script.
- **Scripts.** Lua 4.0, the engine's own API. The compiler prepends generated
  globals (`SS2_GROUP_<name>`, `SS2_CAMERA_<name>`) so scripts never hard-code
  IDs.

### Implementation Guidelines

- Never modify a retail row or a retail pack. If a mission needs a changed copy
  of something retail, clone it under an SS2 ID.
- Everything under `build/` is derived and gitignored. Nothing derived from
  retail data is committed.
- The staged exe is named `SS2.exe`, so test tools that look for the port's
  `Game.exe` window never touch an SS2 run and vice versa.
- Engine changes that SS2 needs (new script functions, new mechanics) are
  requested from the engine port, not patched in this repository.

## Consequences

- New missions are limited to rearranging existing level templates, units and
  objects until new geometry can be loaded. That is acceptable for the MVP and
  the vertical slice, which the concept document already scopes to reused
  assets.
- The build depends on the engine port's four `dbpatch_*.py` UI patches for as
  long as the port needs them; `tools/build.py` runs whichever are present.
- Large retail levels build tens of thousands of collision trees at load
  (50–200 s). Mission iteration is faster on small levels.

## Verification

- `python tools/test_ssdb.py <game.db>`: the database library writes an
  untouched database back byte for byte and re-encodes every table identically.
- `python tools/build.py` then `python tools/run.py map 50001`: the sandbox
  mission loads with SS2-placed units, camera and script
  (`docs/screenshots/m00_sandbox_first_run.png`).
