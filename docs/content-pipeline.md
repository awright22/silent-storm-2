# Authoring SS2 content

How to add a mission and get it running. Background and the reasons for this
design are in `docs/architecture/adr-0001-content-layer-on-ported-engine.md`.

## One-time setup

1. Own Silent Storm (Steam or GOG) and have a build of the ported engine
   (`<engine>/build/Game.exe`).
2. Copy `ss2.local.example.toml` to `ss2.local.toml` and set both paths.
3. `python tools/build.py`. The first run copies about 2.4 GB of retail data
   into `build/run` and takes about 20 seconds; later runs take about 10.

Python 3.11 or newer, standard library only.

## Build and run

```
python tools/build.py                                  # compile game/ into build/run
python tools/run.py map 50001 --shots 5,20 --out m00   # launch, screenshot, collect the log
```

- `map <id>` starts a mission directly with a default three-person party. The
  ID is `50000 + slot` (the build prints it for every mission).
- `--shots` are seconds after the mission starts. Screenshots and the log land
  in `build/shots/<out>_NN.png` and `build/shots/<out>.log`.
- The log holds the engine's debug output, including every `out( ... )` call
  from the mission script, each line prefixed with seconds since launch.
- The window opens behind other windows and never takes focus. `--front` leaves
  it in front for playing by hand.
- `--debug` runs under the engine port's `dbgrun` for a crash stack. Large maps
  load several times slower that way.

## A mission

A mission is a folder under `game/missions/` with two files.

### mission.toml

```toml
slot = 1                 # 1..9999, unique. The mission is "map 50001".
name = "m00_sandbox"     # internal name, used in row names
shell = 6213             # retail map variant that supplies the level geometry
keep_waypoints = true    # copy the shell's waypoints (default true)
keep_units = false       # copy the shell's units (default false)

[variant]                # optional: override TemplVariants columns
Weather = "Sunny"

[[waypoint]]
name = "ss2_gate"        # the name scripts use; reuses an existing name row if one matches
pos = [28.0, 20.0]       # tiles from the level's corner
floor = 0                # optional, also z and rotation

[[unit]]
name = "raider1"         # for GetUnit( "raider1" )
pers = 735               # RPGPers ID: who this is (model, stats, weapon)
pos = [27, 17]           # whole tiles
rotation = 270.0
player = 2               # 0 is the human player; others are AI sides
group = "raiders"        # optional; script gets SS2_GROUP_raiders
pose = "Stand"           # Stand, Crouch or Crawl
logic = "Sentry"

[[camera]]
name = "gate"            # script gets SS2_CAMERA_gate
anchor = [28.0, 19.0, 0.0]   # the point looked at
yaw = -0.8               # radians
pitch = -0.75            # radians; about -0.7 (shallow) to -1.35 (steep)
distance = 24.0          # 10..65. Beyond about 65 the frame goes black.
```

Choosing a shell: `python tools/survey.py` loads every retail campaign zone and
every level template marked "Complete" and records which ones start, how long
they take and an overview screenshot (`build/survey/results.json`,
`build/survey/shots/<variant>.png`).

### script.lua

The mission script, in the engine's Lua 4.0. It runs once when the mission
starts; long-running logic goes in functions started with `StartThread`.

```lua
raiders = GetGroup( SS2_GROUP_raiders )
DividedDeploy()                                  -- party to the UnitHero / Unit1..6 waypoints
CameraSet( GetCamera( SS2_CAMERA_gate ) )
SetDiplomacy( 2, 0, DS_ENEMY )
SetDiplomacy( 0, 2, DS_ENEMY )

function WatchRaiders()
	while TRUE do
		Sleep( 20 )
		if not GroupCanFight( raiders ) then
			out( "SS2: all raiders are down" )
			return
		end
	end
end
StartThread( WatchRaiders )
```

Things that differ from modern Lua:

- No booleans. `nil` is false, anything else is true; the retail scripts define
  `TRUE`/`FALSE` constants.
- No `local function`, no `#`, no `pairs` as you know it; `for i = a, b do` and
  `while` work.
- `Sleep( n )`: n is in engine ticks, roughly 70 ms each, so `Sleep( 20 )` is
  about 1.4 seconds.
- A call to a function the engine does not have used to abort the whole script;
  the port turns unknown names into logged no-ops instead. Check the log for
  `[luacompat]` lines when something silently does nothing.

The helper layer every mission can use (`WaitForUnit`, `DividedDeploy`,
`GroupCanFight`, `UnitAIMode`, ...) is in the retail `scripts/Common.l`, staged
at `build/run/scripts/`.

## What the build does with it

For each mission, `tools/content.py`:

1. clones the shell's `TemplVariants` row and its `Templates` row under ID
   `50000 + slot`;
2. clones every row that places something in the shell (`Rects`,
   `FinalElements`, `TerrainSpots`, walls, floors, ...) under new IDs;
3. copies the shell's `Terrain` and `Buildings` resources to loose files
   `build/run/Terrain/<id>` and `build/run/Buildings/<id>`;
4. adds the mission's waypoints (a row plus a loose `Waypoints/<id>` file each),
   units, groups and cameras;
5. adds the script as a `Scripts` row, with the `SS2_GROUP_*` / `SS2_CAMERA_*`
   globals prepended.

Retail rows are never changed, so the retail campaigns still run from an SS2
build.

## Tools

| Tool | Purpose |
|---|---|
| `tools/build.py` | stage, patch, compile: the one command to rebuild |
| `tools/run.py` | launch a console command, take screenshots, collect the log |
| `tools/survey.py` | test which retail levels load; overview screenshots |
| `tools/ssdb.py` | library: read, edit, write `game.db` |
| `tools/sspack.py` | read `.res` packs: `list` and `get` |
| `tools/test_ssdb.py` | round-trip check of the database library against a real `game.db` |
| `tools/stage.py` | copy retail data and the engine exe into the run root |

## Known limits

- New 3D models and textures cannot be added yet: the engine only looks in the
  retail packs for those.
- Big retail levels take one to three minutes to load, because the engine
  rebuilds collision trees every time.
- Objectives, briefings and mission win/lose flow are not wired up yet.
