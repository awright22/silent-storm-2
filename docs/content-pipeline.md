# Authoring SS2 content

How to add a mission and get it running. Background and the reasons for this
design are in `docs/architecture/adr-0001-content-layer-on-ported-engine.md`.
How the engine behaves is in `docs/engine-notes/` (script API, dialogue and
text, campaign flow).

## One-time setup

1. Own Silent Storm (Steam or GOG) and have a build of the ported engine
   (`<engine>/build/Game.exe`, engine commit 5b8f7fb0a of 2026-10-02 or later:
   the tools use its test hooks).
2. Copy `ss2.local.example.toml` to `ss2.local.toml` and set both paths.
3. `python tools/build.py`. The first run copies about 2.4 GB of retail data
   into `build/run` and takes about 20 seconds; later runs take about 10.

Python 3.11 or newer, standard library only.

## Build, run, test

```
python tools/build.py                                        # compile game/ into build/run
python tools/run.py map 50010 118 116 42 120 --front         # play mission 1 with the SS2 squad
python tools/run.py map 50010 118 116 42 120 --shots 5,20 --out m01   # unattended: screenshots and log
python tools/test_missions.py                                # scripted playthrough of every mission
python tools/test_build.py                                   # the build left every retail row intact
```

- `map <id> [persID ...]` starts a mission directly. The ID is `50000 + slot`
  (the build prints it for every mission). The numbers after it are the party,
  as RPGPers IDs; with none the engine uses a default three-person party.
- `--front` opens the window normally for playing by hand. Without it the
  window opens behind other windows and never takes focus.
- `--shots` are seconds after the mission starts. Screenshots and the engine's
  log (including every `out( ... )` from the script) land in
  `build/shots/<out>_NN.png` and `build/shots/<out>.log`.
- A dialogue waits for the player. For unattended screenshots past a dialogue,
  build with `python tools/build.py --skip-dialogue` (dialogues are then only
  logged) and rebuild normally afterwards.

## A mission

A mission is a folder under `game/missions/` holding `mission.toml`,
`script.lua` and optionally `test.lua`. Real examples: `m01_cold_welcome`
(a complete mission), `m00_compose` and `m00_sandbox` (pipeline tests).

### mission.toml

```toml
slot = 10                # 1..9999, unique. The mission is "map 50010".
name = "m01"             # internal name: row names, dialogue codes
shell = 5354             # retail map variant that supplies the level
party = [118, 116, 42, 120]   # squad used when the mission is tested on its own
light = "night"          # day, night, dusk, or an AmbientLights ID. Without it
                         # most levels pick day or night at random.
keep_waypoints = true    # copy the shell's waypoints (default true)
keep_units = false       # copy the shell's units (default false)

[variant]                # optional: override TemplVariants columns directly
Weather = "Sunny"

[diplomacy]              # relations between player slots at the start
neutral = [[0, 3], [1, 3]]    # pairs not listed under neutral or ally are enemies
ally = []

[[character]]            # a retail character cloned under a new name
name = "olsen"           # refer to it as pers = "olsen"; script gets SS2_PERS_olsen
base = 937               # RPGPers ID to copy (model, stats, voice, equipment)
display_name = "Olsen"

[[template]]             # add a building, tree or other level piece
id = 3226                # Templates ID ("House", 12x16)
pos = [16.0, 14.0]       # centre, in tiles from the level's corner
rotation = 90.0
dz = 0.3125              # optional height offset; floor is optional too

[[object]]               # add a single object
id = 574                 # PlacableObjects ID ("Well")
pos = [24.0, 24.0]
name = "well"            # optional, for GetObject( "well" )

[[waypoint]]
name = "m01_extract"     # the name scripts use. UnitHero and Unit1..Unit6 are
pos = [41.0, 29.0]       # where DividedDeploy() puts the party.
floor = 0                # optional, also z and rotation

[[unit]]
name = "m01_sentry"      # for GetUnit( "m01_sentry" )
pers = 63                # RPGPers ID, or the name of a [[character]]
pos = [25, 21]           # whole tiles
rotation = 270.0
player = 1               # 0 is the human player; default 1
group = "yard"           # optional; script gets SS2_GROUP_yard
pose = "Stand"           # Stand, Crouch or Crawl
logic = "Sentry"         # Sentry, Guard, Roaming or Fear
roaming_radius = 0       # for Roaming
level = 0                # added to the zone's difficulty to give the unit's level
route = ["m01_beat_barn", "m01_beat_yard"]   # optional patrol: waypoint names, walked in a loop

[[camera]]
name = "farm"            # script gets SS2_CAMERA_farm
anchor = [28.0, 14.0, 0.0]   # the point looked at
yaw = -0.8               # radians
pitch = -0.8             # radians; about -0.7 (shallow) to -1.35 (steep)
distance = 60.0          # 10..65. Beyond about 65 the frame goes black.

[[dialogue]]
name = "intro"           # script gets SS2_DIALOG_intro
[[dialogue.line]]
who = 118                # RPGPers ID or a [[character]] name: whose figure is shown
text = "That's the farm."    # keep under about 140 characters; <br> breaks a line
```

Finding IDs and positions:

- `python tools/inspect_db.py variant 5354` lists a level's nested templates,
  objects, units and waypoint positions. `pers <text>` searches characters,
  `table <Name> [col=value]` dumps any table, `script <id>` prints a script.
- `docs/locations.md` lists the retail levels that load and how long they
  take. `python tools/survey.py` regenerates the data behind it, with an
  overview screenshot per level in `build/survey/shots/`.
- Dialogue text can only use characters the retail fonts have (ASCII, Cyrillic
  and a few typographic marks); the build rejects anything else. Details and
  text markup: `docs/engine-notes/dialogue-and-text.md`.

### script.lua

The mission script, in the engine's Lua 4.0. It starts when the mission does;
long-running logic goes in functions started with `StartThread`. The build puts
two things in front of it: the generated `SS2_*` constants and
`game/scripts/common.lua` (shared helpers such as `SS2_Say`, `SS2_PartyAt`).

```lua
houseGuards = GetGroup( SS2_GROUP_house )

BeginSequence( 1 )               -- briefing: nothing can start a fight until it ends
DividedDeploy()                  -- party to the UnitHero / Unit1..6 waypoints
CameraSet( GetCamera( SS2_CAMERA_farm ) )
SS2_Say( SS2_DIALOG_intro )      -- play the dialogue and wait for the player
EndSequence()

function Watch()
	while 1 do
		Sleep( 10 )
		if not GroupCanFight( houseGuards ) then
			SS2_Log( "house clear" )
			return
		end
	end
end
StartThread( Watch )
```

The full function reference is `docs/engine-notes/lua-api.md`. What differs
from modern Lua:

- No booleans. `nil` is false, anything else is true, including 0. The retail
  library defines `TRUE`/`FALSE` as 1 and nil.
- No standard library: no `tostring`, `type`, `getn`, `format`, `print`.
- `Sleep( n )`: n is in world ticks of 50 ms of game time, so `Sleep( 20 )` is
  one second. `Sleep( 0 )` does not yield, and a loop with no `Sleep` freezes
  the game.
- A call to a name that does not exist silently does nothing, and many
  functions the retail scripts use are do-nothing placeholders in this engine
  build. The build runs `tools/lualint.py` on every mission script and stops
  on either, naming the file and line.

### test.lua

A scripted playthrough, compiled into the mission only by
`python tools/build.py --test` (which `tools/test_missions.py` does for you).
It does by fiat what a player has to achieve (kill these guards, move the
team there), checks that the mission's own logic reacts, and ends with
`SS2_Log( "TEST PASS" )` or `SS2_Log( "TEST FAIL: <why>" )`. In a test build
`SS2_TEST` is 1 and dialogues are skipped. See `m01_cold_welcome/test.lua`.

## What the build does with it

For each mission, `tools/content.py`:

1. clones the shell's `TemplVariants` row and its `Templates` row under ID
   `50000 + slot`;
2. clones every row that places something in the shell (`Rects`,
   `FinalElements`, `TerrainSpots`, walls, floors, ...) under new IDs, and
   copies the shell's `Terrain` and `Buildings` resources to loose files
   `build/run/Terrain/<id>` and `build/run/Buildings/<id>`;
3. adds the mission's own templates, objects, waypoints (a row plus a loose
   `Waypoints/<id>` file each), characters, units (with a loose `Units/<id>`
   route file for a patrol), groups, cameras, light and diplomacy;
4. adds dialogues as `Dialogs`, `DialogSeqs`, `AckInfos` and `Strings` rows;
5. checks the assembled script and adds it as a `Scripts` row.

Retail rows are never changed, so the retail campaigns still run from an SS2
build. `python tools/test_build.py` verifies that after a build.

## Tools

| Tool | Purpose |
|---|---|
| `tools/build.py` | stage, patch, compile: the one command to rebuild |
| `tools/run.py` | launch a console command, take screenshots, collect the log |
| `tools/test_missions.py` | run every mission's scripted playthrough in the game |
| `tools/test_build.py` | check a build left every retail row intact |
| `tools/lualint.py` | check a mission script for undefined and do-nothing names |
| `tools/inspect_db.py` | look up levels, characters, tables and scripts |
| `tools/survey.py` | test which retail levels load; overview screenshots |
| `tools/ssdb.py` | library: read, edit, write `game.db` |
| `tools/sspack.py` | read `.res` packs: `list` and `get` |
| `tools/test_ssdb.py`, `tools/test_lualint.py` | tests for the two libraries |
| `tools/stage.py` | copy retail data and the engine exe into the run root |

## Known limits

- New 3D models and textures cannot be added yet: the engine only looks in the
  retail packs for those.
- Dialogue is text only until the engine port has an audio backend.
- There is no objectives screen and no on-screen message line; a mission can
  only talk to the player through dialogues.
- A script cannot stop the player leaving a mission early, and cannot show a
  mission-failed screen.
- A campaign of SS2's own can be authored as data but only started by console
  command with a default party (`docs/engine-notes/campaign-flow.md`).
- Big retail levels take one to three minutes to load, because the engine
  rebuilds collision trees every time.
