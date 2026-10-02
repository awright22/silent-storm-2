# Technical Preferences

<!-- Updated as the user makes decisions throughout development. -->
<!-- All agents reference this file for project-specific standards and conventions. -->

## Engine & Language

- **Engine**: original Silent Storm engine (Nival, January 2003 source), ported to a
  modern MSVC toolchain in a separate repository. SS2 does not modify engine code.
- **Language**: Python 3.11+ (tools, standard library only); Lua 4.0 (mission scripts)
- **Rendering**: the engine's DirectX 9 renderer, as provided by the port
- **Physics**: the engine's own destruction and ballistics systems

## Naming Conventions

- **Python**: PEP 8; modules are short lowercase names under `tools/`
- **Mission folders**: `game/missions/mNN_short_name/` holding `mission.toml` and `script.lua`
- **Lua**: follow the retail scripts: `CamelCase` functions, engine API names as is;
  generated globals are `SS2_GROUP_<name>` and `SS2_CAMERA_<name>`; log lines start with `SS2:`
- **Database rows**: SS2 rows carry `SS2\<mission>` in their `UserName` column
- **IDs**: per mission slot N, variant/template/script are `50000 + N`; other rows
  `1000000 + N*10000 + n` (see ADR-0001)

## Performance Budgets

- **Target Framerate**: set by the engine port, not by this repository
- **Mission load time**: prefer shells that load in under 60 seconds (see `tools/survey.py` results)

## Testing

- **Database library**: `python tools/test_ssdb.py <game.db>` must pass (byte-identical round trip)
- **Missions**: every mission must start under `python tools/run.py map <id>` with no
  script errors in the log
- **Required Tests**: balance formulas and gameplay systems once SS2 adds its own

## Forbidden Patterns

- Modifying or deleting a retail database row or a retail resource pack (clone under an SS2 ID instead)
- Committing anything under `build/` or anything derived from retail data
- Writing to the retail install or to the engine port's repository
- Hard-coded record IDs in mission scripts where a generated `SS2_*` global exists

## Allowed Libraries / Addons

- Python standard library only

## Architecture Decisions Log

- [ADR-0001](../../docs/architecture/adr-0001-content-layer-on-ported-engine.md): SS2 is a
  content layer on the ported original engine
