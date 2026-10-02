# Silent Storm 2

Non-commercial fan sequel to Silent Storm (2003), built as a content layer on a
modern port of the original engine. Developed with the Claude Code Game Studios
agent architecture (48 coordinated subagents, each owning a domain).

## Technology Stack

- **Engine**: the original Silent Storm engine (Nival, C++, DirectX 9), ported
  to a modern compiler in a separate repository. This repository does not
  contain or modify engine code.
- **Content**: text sources under `game/` (TOML mission descriptions, Lua 4.0
  scripts), compiled into the game database by Python tools under `tools/`.
- **Language**: Python 3.11+ (standard library only) for tools; Lua 4.0 for
  mission scripts.
- **Version Control**: Git with trunk-based development
- **Build System**: `python tools/build.py` (stages retail data, compiles
  content into `build/run`); `python tools/run.py` to launch and capture.
- **Asset Pipeline**: retail assets are reused in place; SS2 adds database rows
  and loose resource files only. See `docs/content-pipeline.md`.

> **Do not suggest another engine.** The engine choice is settled
> (`docs/architecture/adr-0001-content-layer-on-ported-engine.md`). The Godot,
> Unity and Unreal specialist agents and `docs/engine-reference/` from the
> template do not apply to this project.

> **Retail data never enters the repository.** Everything under `build/` is
> derived from the owner's game install and is gitignored.

## Pace and Quality (owner's instruction, 2026-10-02)

There is no rush on this project, on the standing goal of building Silent
Storm 2 or on any part of the game. Take the time to do things right.

- No shortcuts. Prefer the correct, complete solution over the quick one, even
  when it takes much longer.
- Cost and time are not concerns. Do not trim scope, skip verification or
  leave a known gap in order to finish sooner or spend less.
- Verify work in the running game before calling it done, and say plainly what
  was and was not verified.

## Project Structure

@.claude/docs/directory-structure.md

## Content Pipeline Reference

@docs/content-pipeline.md

## Technical Preferences

@.claude/docs/technical-preferences.md

## Coordination Rules

@.claude/docs/coordination-rules.md

## Collaboration Protocol

**User-driven collaboration, not autonomous execution.**
Every task follows: **Question -> Options -> Decision -> Draft -> Approval**

- Agents MUST ask "May I write this to [filepath]?" before using Write/Edit tools
- Agents MUST show drafts or summaries before requesting approval
- Multi-file changes require explicit approval for the full changeset
- No commits without user instruction

See `docs/COLLABORATIVE-DESIGN-PRINCIPLE.md` for full protocol and examples.


## Coding Standards

@.claude/docs/coding-standards.md

## Context Management

@.claude/docs/context-management.md
