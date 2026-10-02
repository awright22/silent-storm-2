# Campaign flow in the Jan03 engine

Reference for authoring a new campaign ("scenario") as database rows plus loose resource files.

**How this was established.** Everything below comes from reading the engine source at
`D:\Code\Silent-Storm` commit `d98886b6f` (2026-10-02 08:13; the campaign files are unchanged
since `f414f0c8b`) and from decoding the retail `game.db.retail`, `Chapters.res` and `Globals.res`.
Nothing was run in the game for this note. Statements that are an inference rather than a direct
reading of code or data are marked **unverified**.

Paths: `Main/...`, `DBFormat/...`, `FileIO/...`, `Script/...` are relative to
`D:\Code\Silent-Storm\Soft\Andy\Jan03\a5dll`. `port/...` is relative to `D:\Code\Silent-Storm`.
Line numbers are those of the committed files. Six campaign files have uncommitted edits in the
engine working tree (see section 6); in those files lines after the edit point are shifted by a few.

---

## 0. Summary and blockers

- A campaign is a `Scenarios` row plus `ScenarioZones`, `ScenarioClues`, `ScenarioObjectives` and
  `ScenarioObjective2Clues` rows, one `GlobalMaps` row, one or more `ChapterMaps` rows, and one
  `Globals\<GlobalMapID>` and one `Chapters\<ChapterMapID>` resource file per map. All of it is
  data. No table or file belonging to the retail campaigns has to change.
- Progress is driven only by **clues**. A found clue completes an objective; the objective opens
  and blocks zones and may hand out further ("compound") clues. Found clues are also the only
  campaign state that survives from one mission to the next and that a script can read
  (`ClueIsFound`).
- **Blocker 1 – campaign selection.** The side menu starts side 1 or side 2 and nothing else
  (`Main/iSideMenu.cpp:28-29,226-236`). A third campaign can only be started with the console
  command `global <GlobalMapID>`, which gives a fixed three-person party with no side. Without a
  side there is no hero selection, no hiring pool and no "return to base" button, and the store
  shows only store rows whose `SideID` is empty. A real third campaign needs a small code change
  (for example a `campaign <sideID>` command, or a data-driven side menu).
- **Blocker 2 – objectives screen.** The "Objectives" button has no handler in Jan03. The Gold
  goal functions are no-ops in the committed build. There is no objectives UI at all.
- **Blocker 3 – script cannot control leaving.** The "Leave" button ends the mission directly.
  `SetLeaveZoneMode`, `ShowLeaveZoneDialog`, `ShowLoseDialog`, `BeginZone` and `LeaveToSubZone`
  are no-ops, and the engine never calls a script `OnExit`.
- **Blocker 4 – no campaign variables.** `GetGlobalGameVar`/`SetGlobalGameVar` are stored per
  mission world and are lost on every zone change. Use clues as flags.
- **Constraint – six-zone rule.** The scenario graph is accepted only if the shortest
  `BASE` → `FFIGHT` route contains at least six zones. A shorter campaign still runs, but every
  zone gets difficulty 0, which sets enemy levels and store stock (section 2.6).
- **Constraint – two zone names are mandatory.** A scenario must contain a zone whose
  `SmallDescription` is `BASE` and one whose `SmallDescription` is `FFIGHT` (case-insensitive),
  otherwise no clue is ever placed.

---

## 1. Campaign start

### 1.1 The three ways in

| Entry | Call | Party | Side | Scenario | Returns to |
|---|---|---|---|---|---|
| Main menu → side → hero → face | `CICBeginGame( side.GlobalMap, players )` | chosen hero only | side 1 or 2 | from `GlobalMaps.Scenario` | global map, later chapter map |
| `global <GlobalMapID>` | `CICBeginGame( id, default player )` | RPGPers 54, 53, 14 (all flagged hero) | none | from `GlobalMaps.Scenario` | global map, later chapter map |
| `chapter <ChapterMapID>` | `CICBeginChapter( id, game )` | RPGPers 54, 53, 14 | none | **none** | chapter map |
| `zone <scenario> <zone> ...` | `CICBeginMission( zone, ... )` | listed pers or 54, 53, 14 | looked up from scenario | by name | nowhere (error on leave) |

Evidence: `Main/iFaceGen.cpp:285-295`, `Main/iGlobalMap.cpp:296-310`, `Main/iChapterMap.cpp:286-299`,
`Main/iMission.cpp:2408-2473`, `Main/RPGGlobal.cpp:212-229`.

### 1.2 `CICBeginGame` step by step

`Main/iGlobalMap.cpp:212-239`:

1. Reads the `GlobalMaps` row and takes its `Scenario` record ID (214-217).
2. `CreateGlobalGame( scenarioID )` builds the game object and the scenario tracker (220).
   Difficulty is hard-wired to `DifficultyConstants` row 2 (`Main/RPGGlobal.cpp:206`).
3. Sets `bGlobalMapSet = true`, `nGlobalMapID = id` (223-224). The chapter is **not** set.
4. Looks up the tracker zone for `GlobalMaps.BaseZoneID`. If there is none it prints
   `ERROR: Can't start game! No base zone set!` and stops (226-232).
5. Clears the active save slot (`temp`) (234-235; `Main/iSaveManager.h:18`).
6. Starts the base zone as an ordinary mission: `CICBeginMission( baseZone, -1, ... )` (238).

`GlobalMaps` columns read by Jan03: `Scenario`, `Background`, `BaseZoneID`
(`DBFormat/DataMap.cpp:78-83`). The retail columns `ScriptID` and `StartZoneID` are ignored, so
the first mission is always the base.

`global <id>` with an ID that has no `GlobalMaps` row dereferences a null pointer at line 226.

### 1.3 Console command arguments

- **`global <GlobalMapID>`** – one integer. `Main/iGlobalMap.cpp:296-310`.
- **`chapter <ChapterMapID>`** – one integer. Creates a game with no scenario
  (`CreateGlobalGame()` defaults to scenario -1). `Main/iChapterMap.cpp:286-299`.
  With no scenario every `ZONE` sector resolves to no zone and is neither drawn nor enterable
  (`Main/scScenarioTracker.cpp:80-86`, `Main/iChapterMapUI.cpp:436-439,751-756`). Typing
  `scenario <name>` in the console afterwards builds the scenario in the running game
  (`Main/scScenarioTracker.cpp:32`, `Main/scCommands.cpp:23-43`). The exit sector then fails with
  `ERROR: Can't continue global! No global set!`.
- **`zone <scenarioName> <zoneName> [clueName ...] [persID ...]`** – `Main/iMission.cpp:2408-2473`.
  - Names are matched case-insensitively against `Scenarios.Name` and `ScenarioZones.SmallDescription`.
  - Every further token is a pers ID if `atoi` gives non-zero, otherwise a clue name.
  - If any extra token is present, all clues are first removed from the zone and only the named
    clues are placed (2448-2463).
  - It needs a `Sides` row whose `GlobalMap` points to a `GlobalMaps` row with this scenario
    (`GetSideForScenario`, `Main/scScenarioTracker.cpp:620-646`). If none is found the command
    returns silently. That lookup dereferences `GlobalMaps.Scenario` of every side it visits, so a
    `Sides` row pointing at a `GlobalMaps` row with `Scenario = 0` will crash it.
  - Neither map flag is set, so leaving ends in `ERROR: GlobalMap and ChapterMap not set!`
    after the players have already been removed from the world (`Main/iMission.cpp:2373-2390`).
    Use it to test one mission, not a campaign.
- **`map <variantID> [persID ...] [vs persID ...] [with name ...]`** and
  **`template <templateID> ...`** – no zone, no scenario. `Main/iMission.cpp:2197-2247`.
- Debug commands that exist while a tracker is alive: `scenario list`, `scenario draw`,
  `scenario take <clue>`, `scenario destroy <clue>`, `open_zone <zone>`
  (`Main/scCommands.cpp:23-64`). On the global map: `difficulty <id>` (`Main/iGlobalMap.cpp:79,281-289`).

### 1.4 The menu path and why a new side cannot use it

`mainmenu` → `CICSideMenu` (`Main/iMainMenu.cpp:208`) → `CICHeroMenu( GetDBSide(1) )` or
`CICHeroMenu( GetDBSide(2) )` (`Main/iSideMenu.cpp:28-29,226-236`) → `CICFaceGen` or `CICCharGen`
(`Main/iHeroMenu.cpp:251,256`) → on "play": `CreateGlobalPlayer( side )`, push the hero,
`CICBeginGame( side.GlobalMap, players )` (`Main/iFaceGen.cpp:285-295`).

`Sides` columns read (`DBFormat/DataRPG.cpp:1041-1078`): `GlobalMap`, `HeroSelectTemplate`,
`StringID`, `Nationality1..3`, `Male*`/`Female*` class pers, `Nationality{1,2,3}{Male,Female}`
(the six hero choices, `Main/iHeroMenu.cpp:130-142`), `ESCMenuBackground`, `UIBaseFlag`,
`UIBaseFlagActive`, `HeroDialogPersID`.

The only data-only way to reach a new campaign through the menu is to repoint
`Sides[1].GlobalMap` or `Sides[2].GlobalMap` in your own `game.db`. That replaces a retail
campaign in your build.

### 1.5 From zone to map

`CMission::Initialize` (`Main/iMission.cpp:131-254`):

- Template = `ScenarioZones.TemplateID1` unless a template was passed (143-144).
- The variant is chosen by the `RndWeight` roulette with a per-zone seed fixed when the scenario
  was created, so a zone always gets the same variant (149, 162-171; `Main/scFlowChartItems.cpp:78-92`).
- Enemy level base = zone difficulty (150).
- It first tries to load `<ZoneID>.sav` from the active slot (173-174). If that fails the world is
  built from the variant and the clues assigned to this zone and template are passed in (176-181).
- The variant script runs only when the world is built. A restored zone keeps its saved Lua state
  and the script chunk is not run again (`Main/wMain.cpp:1401-1407,1449-1454`).

Every zone template must reference a `Templates` row with at least one `TemplVariants` row. The
variant is dereferenced without a check when the scenario is created
(`Main/scFlowChartItems.cpp:91`).

### 1.6 Minimal rows for one base zone and two mission zones

See section 7 for the checklist with column values.

---

## 2. The scenario model

### 2.1 Tables

| Table (ID) | Meaning | Columns read by Jan03 |
|---|---|---|
| `Scenarios` (83) | One campaign graph | `Name`, `Description` |
| `ScenarioZones` (79) | One playable location | `Scenario`, `TemplateID1..3`, `ItemSlots`, `PersonSlots`, `SmallDescription`, `CluesMaxNumber`, `CanBeRevealed` |
| `ScenarioClues` (81) | A thing to find, capture or conclude | `Type`, `Scenario`, `State`, `ZoneToPlace1..3`, `Objective1..2`, `SmallDescription`, `ItemID`, `PersID`, `Permanent`, `MinParentToOpen`, `Description`, `GiveImmediately` |
| `ScenarioObjectives` (82) | What happens when a clue is taken or destroyed | `Type`, `ZoneToOpen1..3`, `ZoneToBlock1..3`, `Description`, `Scenario` |
| `ScenarioObjective2Clues` (84) | Objective → compound clue link | `ObjectiveID`, `ClueID` |
| `ScenarioStates` (80) | Imported, never used by game code | `Description` |

Evidence: `DBFormat/DataScenario.cpp:47-118`, `DBFormat/DataFormat.cpp:1989-1994`.
`ScenarioClues.State` is stored and no code in `Main` reads it.

Retail columns that Jan03 ignores: `Scenarios.FullGraph`; `ScenarioZones.TimeOfDay`,
`PWLImageID`, `Name`, `CanPKBeUsed`, `MaxDifficulty`; `ScenarioClues.GiveByScript`, `GoalID`;
`GlobalMaps.ScriptID`, `StartZoneID`; `ChapterMaps.ScriptID`, `PWLImageID`;
`TemplVariants.NoAttack`, `Weather`, `ExitBorder`; `RPGPers.CanHired`.

Value rules:

- `ScenarioClues.Type`: `person`, `item` or `conclusion`, case-insensitive
  (`DBFormat/DataScenario.cpp:10-33`).
- `ScenarioObjectives.Type`: `capture` or `destroy` (`DBFormat/DataScenario.cpp:17-45`).
- `SmallDescription` is the internal name of a zone or clue. Scripts, console commands and the
  engine look items up by it, case-insensitively (`Main/scFlowChart.cpp:85-126`). The journal's
  "by zone" view shows the zone `SmallDescription` to the player as a heading
  (`Main/iCluesMenu.cpp:267,287`).
- A clue's journal line is the `Strings` row in `ScenarioClues.Description`. Its detail text and
  its popup text are the `Strings` row in the `Description` of whichever of its objectives was
  completed (`Main/iCluesMenu.cpp:123-137,314-328`, `Main/scScenarioTracker.cpp:58-70`).

### 2.2 How the graph is generated at campaign start

`CScenarioFlowChart` constructor, `Main/scFlowChart.cpp:491-525`, calling `Generate`
(263-297) and `LoadItems` (306-388):

1. Load every zone, clue and objective whose `Scenario` equals the scenario ID, then the
   objective→clue links.
2. If there is no `BASE` zone or no `FFIGHT` zone, log
   `[SCENARIO TRACKER] incorrect data for scenario graph.` and stop before placing anything (25-38, 267-271).
3. Place each clue, in random order, into one of its `ZoneToPlace1..3` zones chosen at random
   among those that can take it (159-192). A zone can take a clue if the clue is `Permanent`, or if
   the number of non-permanent clues of that type already there is below `ItemSlots` (item) or
   `PersonSlots` (person) and the total is below `CluesMaxNumber`
   (`Main/scFlowChartItems.cpp:133-156`). A non-permanent `conclusion` clue can never be placed in
   a zone, because its slot count is zero.
4. Attach each objective to the placed clue that lists it in `Objective1`/`Objective2`. The
   clues linked to that objective through `ScenarioObjective2Clues` become placed **compound**
   clues (194-220). Do not list one objective in two clues.
5. Resolve each placed objective's `ZoneToOpen*` and `ZoneToBlock*` (222-261).
6. Remove compound clues that have fewer placed parent clues than they require (551-579).
7. Check the graph: a route from `BASE` to `FFIGHT` must exist and contain at least six zones
   (679-689). If the check fails the whole generation is repeated, up to 11 times, then accepted
   as it is with `[SCENARIO TRACKER] [ ERROR ] Scenario flowchart is incorrect` (494-524).
8. Only for an accepted graph: compute zone difficulties (643-677).

Then `PostCreateScenario` (`Main/scScenarioTracker.cpp:259-281`) makes `BASE` available and
**immediately completes the first objective of every clue placed in `BASE`**. This is how the first
zones open.

Consequence for retail Axis under Jan03: the base zone (80) has `ItemSlots = 1` and four
non-permanent item clues want to be placed there (5332, 5334, 5368, 5371), so exactly one of them
is placed per campaign and one first zone opens (ECom 57, ELab 56, GVip 68 or GStore 64).

`MinParentToOpen` for a compound clue: a value of 0 or more is the number of found parent clues
required; -1 means all possible parents (`Main/scFlowChart.cpp:1424-1442`).

Zones that have a second template (`TemplateID2 <> 0`) get their slot counts by building each
template's map during scenario creation, which is slow and is repeated on every generation
attempt (`Main/scFlowChartItems.cpp:94-130`). Single-template zones use the `ItemSlots` and
`PersonSlots` columns directly.

### 2.3 How a clue is found

- **Carried out.** When the party returns to the chapter map, every living party member and every
  living carried unit is checked by pers ID, and every inventory item by item record ID. A match
  against `ScenarioClues.PersID` or `ItemID` takes the clue; a matching item is removed from the
  inventory (`Main/scScenarioTracker.cpp:546-595`, called from `Main/RPGGlobal.cpp:295-307`,
  `Main/iChapterMap.cpp:262`). Nothing is taken at the moment of pickup, and nothing is taken when
  the mission ends on the global map instead of the chapter map.
- **Destroyed.** A unit whose pers ID matches a clue dies, or is removed by `UnitRemove` before the
  clue was found, or a frozen clue item is destroyed
  (`Main/wUnitServer.cpp:1188`, `Main/scriptUnit.cpp:411-425`, `Main/wDebris.cpp:309`).
  With `GiveImmediately = 1` the effect is applied at once, otherwise when the party next returns
  to the chapter map (`Main/scScenarioTracker.cpp:471-488`).
- **Given by script.** `ScenarioGiveClue` (section 4).
- **Compound.** Given automatically when enough parent clues are found
  (`Main/scScenarioTracker.cpp:234-255`).
- **Placed in `BASE`.** Found at campaign start (2.2).

Taking completes the clue's `capture` objective. Destroying completes its `destroy` objective,
if it has one, and marks the clue destroyed so it never appears in the journal
(`Main/scScenarioTracker.cpp:490-510`, `313-324`).

`OnObjectiveComplete` (`Main/scScenarioTracker.cpp:209-257`) does nothing if the objective has no
parent clue or the clue is already found. Otherwise it blocks `ZoneToBlock*`, opens `ZoneToOpen*`
that are neither available nor blocked, and evaluates the compound clues.

### 2.4 How a clue is physically placed in a mission

`Main/wMain.cpp:950-1054`, `Main/MapBuild.cpp:375-387,441-460`:

- An **item slot** is a `FinalElements` placement whose object carries RPG item 188
  (`CLUE_SLOT_ID`, `Main/MapBuild.cpp:25`). An item clue assigned to this zone and template is
  created there as a frozen item named after the clue.
- A **person slot** is a `Units` row with `ClueSlot = 1`. The unit is created only if a person clue
  is assigned to it, using the clue's `PersID`, and is named after the clue if its own `Name` is
  empty (`Main/wMain.cpp:1097-1110`).
- A `Units` row with `ClueInventorySlot = 1` can receive an item clue in its inventory.
- If the map has no free slot of the right kind the clue is simply not created. A clue that is to
  be given by script needs no slot.

### 2.5 Zones opening and closing

- Available = in the tracker's list and not blocked (`Main/scScenarioTracker.cpp:303-311`).
- Opened by: a completed objective; `ScenarioOpenZone`; the console `open_zone`; the party marker
  crossing a zone icon whose zone has `CanBeRevealed = 1` (`Main/iChapterMapUI.cpp:443-445`,
  `Main/scScenarioTracker.cpp:381-399`).
- Blocked by: a completed objective's `ZoneToBlock*`; `ScenarioBlockZone`. A block is permanent
  and hides the zone even if it was opened (`Main/scScenarioTracker.cpp:104-112`).
- Entering a zone marks it "passed", which only changes its icon (`Main/iMission.cpp:146`,
  `Main/iChapterMapUI.cpp:470-480`).
- The "recommended" zone that flashes is the available zone that still holds an unfound clue and
  has the lowest difficulty relative to the party's average level (`Main/scScenarioTracker.cpp:355-379`).

### 2.6 Difficulty and the six-zone rule

For an accepted graph: `FFIGHT` gets 15, dead-end zones 13, and zones along the shortest
`BASE` → `FFIGHT` route are spread evenly from the base value up to 15
(`Main/scFlowChart.cpp:581-677`). For a rejected graph every zone keeps difficulty 0.

Zone difficulty feeds:

- Enemy level = `max( 0, zone difficulty + Units.RelativeLevel + DifficultyConstants.AIUnitsLevel )`
  (`Main/iMission.cpp:150`, `Main/wMain.cpp:1140-1145`).
- Store stock per store row = `( highest difficulty among available zones − Rating ) × Quantity`,
  truncated (`Main/wMain.cpp:227,309-316`). With all difficulties at 0, a row needs a negative
  `Rating` to be stocked.
- Random-encounter level = average difficulty of the chapter's zones plus a small random offset
  (`Main/iChapterMap.cpp:80-104`, `Main/iMission.cpp:152-160`).
- Lua `GetCurrentZoneAILevel()` (`Main/scriptScenario.cpp:90-97`).

### 2.7 Worked example: retail Axis (scenario 2)

- 25 zones, 86 clues (42 item, 13 person, 31 conclusion), 87 objectives (85 capture, 2 destroy),
  53 objective→clue links. `GlobalMaps` 3: `BaseZoneID` 80, `Scenario` 2. `Sides` 1: `GlobalMap` 3.
- Start: clue 5334 `INFO_E_SCIENTIST_DEFENCE` (item 254, `ZoneToPlace1` 80) has objective 5533,
  `capture`, `ZoneToOpen1` 56. If it is the base clue that got placed, zone 56 `ELab` opens at
  campaign start.
- Carry-out: clue 5354 `Save_E_Scientist` (person 198, zone 56) has objective 5553, `ZoneToOpen1`
  58 `EVip`. Bringing that person out of ELab alive opens EVip on return to the chapter map.
- Compound: objective 5528 (of clue 5329 `Capture_Colonel`) links to five conclusion clues through
  `ScenarioObjective2Clues`. Another compound clue, 5399 `RocketTechnology`, is linked from three
  objectives (5536, 5559, 5590) and has `MinParentToOpen = 2`, so two of its three parents suffice.
- Two outcomes: clue 5392 `General_Survived` (person 192, zone 68) has `Objective1` 5591
  `destroy` (opens 64, blocks 61) and `Objective2` 5592 `capture` (opens 61).
- Script-given: clue 5348 `Obtain_German_Pk` is `conclusion`, `Permanent = 1`, `ZoneToPlace1` 65.
  Permanent is what lets a conclusion clue be placed.
- Final: four objectives open zone 76 `FFight` (5525, 5574, 5578, 5583).
- Zone 123 `GFirst` (Gold's first mission) is opened by nothing and has `CanBeRevealed = 1`. Under
  Jan03 it is reachable only if a chapter record contains it.

---

## 3. Global map and chapter map screens

### 3.1 Database rows

- `GlobalMaps` (16): `Scenario`, `Background` (UI texture, retail 523), `BaseZoneID`.
- `ChapterMaps` (15): `Background` (UI texture), `CampZone1..4` (template IDs, 0 = none)
  (`DBFormat/DataMap.cpp:87-99`).
- The screens use UI containers 175 (global) and 147 (chapter)
  (`Main/iGlobalMap.cpp:101`, `Main/iChapterMap.cpp:127`).

### 3.2 Resource files

- Global map layout: resource `Globals`, key = `GlobalMaps.ID` (`Main/GlobalInfo.cpp:18-32`,
  `Main/iGlobalMap.cpp:89`).
- Chapter map layout: resource `Chapters`, key = `ChapterMaps.ID` (`Main/ChapterInfo.cpp:13-27`,
  `Main/iChapterMap.cpp:111`).
- An ID missing from the pack is opened as the loose file `Globals\<id>` or `Chapters\<id>` in the
  working directory (`Main/GResource.cpp:76-81,85-88,111-119`).
- A missing or unreadable file gives an empty record with no sectors; it does not crash
  (`Main/ChapterInfo.cpp:22-26`).

### 3.3 Serialized layout

Chunk encoding: one byte chunk ID, then the length as one byte `len << 1` when `len < 128`,
otherwise four bytes little-endian `(len << 1) | 1`, then the payload. Integers and floats are
4 bytes little-endian.

File framing written by `CStructureSaver` (`FileIO/BasicChunk1.cpp:380-491`):

```
chunk 1 : the object's fields
chunk 0 : object table      (empty for these two classes)
chunk 2 : object data       (empty for these two classes)
```

Containers (`FileIO/BasicChunk1.h:167-177,216-240`; strings `FileIO/BasicChunk1.cpp:265-277`):

- `vector<struct>` – a sequence of chunks with ID 1, one per element, no count.
- `vector<CVec2>` – chunk 1 = element count (int), chunk 2 = raw data, 8 bytes per point.
  Chunk 2 is absent when the count is 0.
- `string` – the raw bytes, no terminator.

**`CChapterInfo`** (`Main/ChapterInfo.h:15-45`):

| Chunk | Field | Type | Meaning |
|---|---|---|---|
| 2 | `nMapID` | int | Not read by the game. Retail stores 485 in the playable records. |
| 3 | `vDeployPos` | 2 × float | Party marker start, in 1024×768 screen pixels |
| 4 | `sectorsSet` | vector of sector | |

Sector (`SChapterSector`):

| Chunk | Field | Type | Meaning |
|---|---|---|---|
| 2 | `nTemplate` | int | `ZONE`: `ScenarioZones.ID`. `RANDOM`: `Templates.ID`. `EXITZONE`: -1 |
| 3 | `nProbability` | int | `RANDOM` only |
| 4 | `nDescriptionID` | int | `Strings.ID` shown on hover, or -1 |
| 5 | `pointsSet` | vector of CVec2 | Screen pixels. A sector with no points is skipped |
| 6 | `eType` | int | 0 `ZONE`, 1 `RANDOM`, 2 `EXITZONE` |
| 7 | `szID` | string | Not read by the game |

Write all six sector fields. The struct has no constructor, so an omitted field is uninitialised.

**`CGlobalInfo`** (`Main/GlobalInfo.h:15-39`):

| Chunk | Field | Type | Meaning |
|---|---|---|---|
| 2 | `nMapID` | int | Not read by the game. Retail stores 523 |
| 3 | `nScenarioID` | int | Not read by the game |
| 4 | `sectorsSet` | vector of sector | |

Sector (`SGlobalSector`):

| Chunk | Field | Type | Meaning |
|---|---|---|---|
| 2 | `nImageID` | int | `UIContainers.ID` of the sector widget |
| 3 | `nTemplate` | int | `ChapterMaps.ID` opened by a click |
| 4 | `nDescriptionID` | int | Not read by the game |
| 5 | `vImagePos` | 2 × float | Screen position of the widget |
| 6 | `pointsSet` | vector of CVec2 | Click and hover polygon. A sector with no points is skipped |

### 3.4 Real example: `Chapters` record 20 (124 bytes)

```
01 ec                               chunk 1, 118 bytes
   02 08 e5 01 00 00                nMapID = 485
   03 10 00 00 5c 43 00 00 80 43    vDeployPos = (220, 256)
   04 c8                            sectorsSet, 100 bytes
      01 68                         sector, 52 bytes
         02 08 4c 00 00 00          nTemplate = 76   (zone FFight)
         03 08 00 00 00 00          nProbability = 0
         04 08 c2 17 00 00          nDescriptionID = 6082
         05 30                      pointsSet, 24 bytes
            01 08 02 00 00 00       count = 2
            02 20 <16 bytes>        (319, 261) (307, 261)
         06 08 00 00 00 00          eType = 0 ZONE
         07 00                      szID = ""
      01 58                         sector, 44 bytes
         02 08 ff ff ff ff          nTemplate = -1
         03 08 00 00 00 00
         04 08 ff ff ff ff          nDescriptionID = -1
         05 20                      pointsSet, 16 bytes
            01 08 01 00 00 00       count = 1
            02 10 00 00 ba 42 00 00 21 43    (93, 161)
         06 08 02 00 00 00          eType = 2 EXITZONE
         07 00
00 00                               chunk 0, empty
02 00                               chunk 2, empty
```

`Globals` record 3 (Axis, 642 bytes) decodes the same way: `nMapID` 523, `nScenarioID` 2, seven
sectors. The first is `nImageID` 328, `nTemplate` 12, `nDescriptionID` -1, `vImagePos` (0, 282),
six points starting (242, 332). `Globals` record 2 uses an older sector layout without
`vImagePos` and is not referenced by any `GlobalMaps` row; ignore it. Several `Chapters` records
(1, 2, 4, 6-9) are megabytes of development data.

Writer sketch using `tools/ssdb.py`:

```python
from ssdb import emit
import struct
i32 = lambda v: struct.pack('<i', v)
def points(ps):
    out = emit(1, i32(len(ps)))
    if ps: out += emit(2, b''.join(struct.pack('<2f', *p) for p in ps))
    return out
def chapter_sector(templ, prob, descr, ps, etype):
    return emit(1, emit(2, i32(templ)) + emit(3, i32(prob)) + emit(4, i32(descr))
                 + emit(5, points(ps)) + emit(6, i32(etype)) + emit(7, b''))
def chapter(map_id, deploy, sectors):
    main = emit(2, i32(map_id)) + emit(3, struct.pack('<2f', *deploy)) + emit(4, b''.join(sectors))
    return emit(1, main) + emit(0, b'') + emit(2, b'')
def global_sector(image, templ, descr, pos, ps):
    return emit(1, emit(2, i32(image)) + emit(3, i32(templ)) + emit(4, i32(descr))
                 + emit(5, struct.pack('<2f', *pos)) + emit(6, points(ps)))
def global_map(map_id, scenario, sectors):
    main = emit(2, i32(map_id)) + emit(3, i32(scenario)) + emit(4, b''.join(sectors))
    return emit(1, main) + emit(0, b'') + emit(2, b'')
```

Check done: decoding retail `Chapters` records 12, 13, 16, 19, 20, 21, 28 and `Globals` records
3, 4 and re-encoding them with these functions reproduces each record byte for byte. Loading a
newly authored file in the engine is **unverified**.

### 3.5 Chapter map behaviour

`Main/iChapterMapUI.cpp`:

- A `ZONE` sector is a 69×69 icon whose top-left corner is the first point. Only the first point
  is used (31-32, 814-820). It is drawn only while its zone is available (447-457).
- A click on the map sets the target and the marker walks there at 20 pixels per second
  (850-856, 868-895).
- Clicking the party marker fires `action` (803). For every sector under the marker: `ZONE`
  starts that zone's mission; `EXITZONE` goes to the global map (736-763). The `ZONE` branch only
  checks that the zone exists, not that it is available, so an unopened zone can be entered by
  standing on its hidden icon. Do not put a zone in a chapter record before the story allows it,
  or accept this.
- If no sector handled the click and the chapter has camp templates, a random one of
  `CampZone1..4` is started as a mission without a zone (765-776).
- A `RANDOM` sector uses all its points as a polygon. A marker appears at a random point inside it
  and disappears again on a timer; walking the party marker onto it starts template `nTemplate`
  as a zone-less mission (547-591). `nProbability` is the percent chance that a timer tick is
  skipped: a higher value makes a hidden marker appear **less** often (561) and a visible one stay
  longer (586).
- An `EXITZONE` sector is an always-visible 69×69 icon at its first point (644-655).
- Hovering a visible zone shows the sector description plus the journal lines of the clues found
  in that zone (400-434).
- Each clue found since the last visit pops up once (950-960).
- The `showglobal` button opens the global map read-only; `cancel` closes it
  (`Main/iChapterMap.cpp:192-196`, `Main/iGlobalMap.cpp:159-163,268-279`).

### 3.6 Global map behaviour

`Main/iGlobalMapUI.cpp`:

- A sector is shown if `nTemplate` is -1, or if that chapter's record contains a `ZONE` sector
  whose zone is available (295-327). Do not use -1: clicking such a sector sets the current
  chapter to -1 and then fails (`Main/iChapterMap.cpp:226-241`).
- The sector widget is the UI container `nImageID`, with controls `zone_normal`, `zone_disabled`,
  `text_normal`, `text_hilighted` and `description` (126-141, 236). The retail widgets are
  containers 328-334 (Axis) and 421-425, 427 (Allies); they carry `zone_normal`, `text_normal`,
  `text_hilighted` and `description`, and no `zone_disabled`.
- A left click inside the polygon runs `CICBeginChapter( nTemplate )`, which sets the current
  chapter and puts the marker at that chapter's `vDeployPos` (250-266;
  `Main/iChapterMap.cpp:226-244`).
- The `basezone` button starts the base mission (`Main/iGlobalMap.cpp:176-182`). It is visible
  only when the player has a side, and uses `Sides.UIBaseFlag` and `UIBaseFlagActive` (203-211).
  The retail `input.cfg` has no key bound to `basezone`.

---

## 4. Mission end and transitions

### 4.1 The scenario Lua functions

All are registered in `Main/ScriptFunctions.cpp:159-169`. Booleans: `nil` is false, any number is
true (`Script/Script.cpp:180-184`).

| Function | Effect | Source |
|---|---|---|
| `ScenarioGiveClue( name, take = true, immediately = false )` | `take` true: take the clue. `take` nil: destroy it. `immediately` true: apply now. Otherwise queue it until the party next returns to the chapter map. Unknown name: nothing. | `Main/scriptScenario.cpp:16-33`, `Main/scScenarioTracker.cpp:132-167` |
| `ScenarioOpenZone( zoneName )` | Makes the zone available. Does not undo a block. | `scriptScenario.cpp:35-45`, `scScenarioTracker.cpp:391-399` |
| `ScenarioBlockZone( zoneName )` | Blocks the zone permanently. | `scriptScenario.cpp:47-57` |
| `ExitToChapter()` | Ends the mission exactly as the Leave button does, without the autosave. | `scriptScenario.cpp:59-62`, `Main/iMissionExec.cpp:209-213` |
| `ClueShow( name )` | Shows the clue popup (UI container 322) with the text of the clue's completed objective. Prints an error text if the clue is not found yet. | `scriptScenario.cpp:64-73`, `Main/iShowClue.cpp:59-63,173` |
| `ClueIsFound( name )` | 1 if any objective of the clue is completed, else nil. | `scriptScenario.cpp:75-88` |
| `GetCurrentZoneAILevel()` | The current zone's difficulty, or nil. | `scriptScenario.cpp:90-97` |
| `uiShowStore()` | Opens the store and inventory panels. | `Main/scriptSequence.cpp:103-106`, `iMissionExec.cpp:271-275` |
| `uiShowTeamMngMenu()` | Opens the team management screen. | `scriptSequence.cpp:108-111`, `iMissionExec.cpp:299-303` |

`ScenarioGiveClue` works only on a clue that the generator placed: one placed in a zone, or a
compound clue. For a clue that exists only to be given by script, use `Type = conclusion`,
`Permanent = 1` and a `ZoneToPlace1`, as retail does. The retail scripts call
`ScenarioGiveClue( name, true, true )` followed by `ClueShow( name )`.

### 4.2 The Leave button

- It is the control `endmission` in the top bar container 126; its label is string 17432 "Leave".
- A UI button posts its ID as an input event (`Main/UIInterface.cpp:451-457`). The mission binds
  `endmission` and runs an autosave followed by `CICEndMission` (`Main/iMission.cpp:1210-1217`).
- The only condition is that no action is executing in turn-based mode (`Main/iMission.cpp:1187-1188`).
  Visible enemies do not prevent leaving. The button's three icon states are cosmetic
  (`Main/iTopPanel.cpp:160-170`).
- No script function is called. `port/AUDIT.md` item L3 says zones cannot be left because
  `ShowLeaveZoneDialog` is a no-op; the committed code does not go through the script at all.
  Which of the two holds in a running build is **unverified**.
- The autosave runs first. Save and load round trips are an open item in `port/ROADMAP.md` (A5),
  so a failing autosave is a possible obstacle. **Unverified.**

### 4.3 `CICEndMission`, `CICContinueChapter`, `CICContinueGlobal`

`CICEndMission::Exec` (`Main/iMission.cpp:2373-2390`):

1. `Terminate`: for a zone mission, remove the players from the world and save the world to
   `<ZoneID>.sav` in the active slot (`Main/iMission.cpp:256-265,1864-1887`).
2. If a chapter is set → `CICContinueChapter`. Else if a global map is set → `CICContinueGlobal`.
   Else print an error.

`CICContinueChapter::Exec` (`Main/iChapterMap.cpp:253-273`):

1. `HealOnLeaveZone` (`Main/RPGGlobal.cpp:278-287,55-80`). Under difficulty row 2
   (`NeedCarryOutUnconscious = 1`): a merc who is unconscious and is not being carried by another
   merc is killed; everyone else is healed and woken.
2. `UpdateScenarioOnLeaveZone`: take clues from the party, then process all queued taken and
   destroyed clues (`Main/RPGGlobal.cpp:295-307`).
3. Open the chapter map at the stored marker position.

`CICContinueGlobal::Exec` (`Main/iGlobalMap.cpp:248-259`) only opens the global map. No healing
and no clue processing happen on this route. It is taken only when leaving the very first base
mission, before any chapter was entered, and from an `EXITZONE` sector.

Once a chapter has been entered, leaving the base also returns to that chapter map.

### 4.4 Other ways a mission ends

- **Passage object.** A `FinalElements` placement of an object that has a `PassageObjects` row.
  With `PassageZoneID <= 0` it exits to the chapter map; with a positive value it loads the zone's
  other template that contains a passage with the same number. Every living, conscious party member
  must be able to reach the object within `APRadius` action points
  (`Main/wMain.cpp:2077-2160`, `Main/wObject.cpp:345-375`, `DBFormat/DataMap.cpp:256-258`).
  Moving between templates does not save the template being left, and all templates of a zone
  share one save file name (`Main/iMissionExec.cpp:242-247`, `Main/iMission.cpp:173-174`). Whether
  multi-template zones restore correctly is **unverified**; prefer single-template zones.
- **Console `surrender`** – `CICEndMission` without the autosave (`Main/iMission.cpp:2249-2256`).

### 4.5 Party dead or unconscious

Each mission step checks `IsPlayerLoser` (`Main/iMission.cpp:937-938`). It is true when every
unit of the player is dead or unconscious, or when the player's unit list contains no unit flagged
as hero (`Main/PlayerTracker.cpp:52-75`). The engine then pushes the lose screen (UI container 371)
with two actions: load a save, or exit to the main menu (`Main/iLoseFake.cpp:99-151,170-175`).
There is no return to the chapter map and no script hook. Whether a dead hero is dropped from the
unit list, which would make the hero's death alone a loss, is **unverified**.

### 4.6 State that carries over

Held in `CGlobalGame` and written into every save (`Main/RPGGlobal.h:115-149`):

- current global map ID and chapter map ID, the marker position on the chapter map
- current zone and template
- the scenario tracker: generated graph, available and blocked zones, completed objectives, queued
  clues (`Main/scScenarioTracker.h:47-57`)
- the players (section 5), the difficulty row, the current chapter's average difficulty

Per zone: the whole world of a zone, including its Lua state, is kept in `<ZoneID>.sav` and
restored on the next visit (4.3). Zone-less missions (camp, random encounter, `map`) are not kept.

Not carried: Lua globals and `SetGlobalGameVar` values of other zones
(`Main/scriptCommon.cpp:335-400`; `port/AUDIT.md` item L5).

---

## 5. Party persistence, store and hiring

- **Where the party lives.** `CGlobalGame.players[0]` is a `CGlobalPlayer` with `pSide`, `mercs`
  (the active party), `totalMercs` (the roster), `deployData` and `storeItemsList`
  (`Main/RPGGlobal.h:81-111`). Each merc is one `NRPG::CUnit` holding pers, class, head, XP,
  skills, name, inventory, perk tree and the hero flag (`Main/RPGUnit.h:146-147`).
- **Why it persists.** A mission wraps the very same `CUnit` objects (`Main/wMain.cpp:1548-1549`),
  so inventory, XP, perks and wounds change in place. Dead mercs are skipped at deployment
  (`wMain.cpp:1502-1503`) and are removed from the party when the team screen is next opened
  (`Main/iTeamMngMenu.cpp:922-928`).
- **Deployment.** All living mercs are placed around deploy spot 0 of the map, a `FinalElements`
  placement of an object with `IsDeployPoint` (`Main/wMain.cpp:1476-1564`, `Main/MapBuild.cpp:314-324`).
- **Hero selection.** The menu path creates the roster from every `RPGPers` row whose `SideID` is
  the chosen side and adds the chosen pers as the only party member, flagged hero
  (`Main/RPGGlobal.cpp:231-252`, `Main/iFaceGen.cpp:287-288`). `RPGPers.CanHired` is not read.
- **Console path.** `global`, `chapter`, `zone` and `map` without pers IDs create RPGPers 54, 53
  and 14, all flagged hero, with a roster of just those three and no side
  (`Main/RPGGlobal.cpp:212-229`).
- **Team screen** (`uiShowTeamMngMenu`, UI container 316). Shows the first 20 roster entries.
  "Hire" adds a living, conscious roster unit while the party has at most five members, so the
  party can reach six; "fire" removes one. On closing, new members are spawned at the deploy spot
  of the current mission and fired ones are removed
  (`Main/iTeamMngMenu.cpp:26-28,781-804,823-830,938,964-1003`). There is no cost.
- **Store** (`uiShowStore`). Lists `RPGStoreItems` rows whose `SideID` equals the player's side;
  a player without a side sees rows with an empty `SideID`. Stock follows the formula in 2.6 and is
  topped up each time the list is built. The item's `RPGItems` row needs a successor
  (`Main/wMain.cpp:222-325`, `DBFormat/DataRPG.cpp:169-175`). No price or money code was found in
  the store panel.
- **The base.** Nothing in the engine is specific to the base except the zone name `BASE`,
  `GlobalMaps.BaseZoneID` and the `basezone` button. In retail the base script opens the store,
  the team screen and the exit from object-use callbacks.
- **Script callbacks the engine really makes:** `OnOpenObject`, `OnCloseObject`, `OnTalk`,
  `OnDialogPhrase`, `OnDialogFinished`, `OnMineTriggered`, `OnScriptNotify`
  (`Main/wObject.cpp:205-207`, `Main/wUnitAttackExec.cpp:2578`, `Main/iMissionDlgUI.cpp:310,416`,
  `Main/wMine.cpp:77`).

---

## 6. Objectives and Journal buttons

### 6.1 What the buttons do

| Button | Control | Result in Jan03 |
|---|---|---|
| Journal | `clues` (key J) | Opens the clues screen, UI container 181. Works in missions, on the chapter map and on the global map. |
| Objectives | `objectives` (key O) | Nothing. The input event has no consumer anywhere in `Main`. |

Evidence: retail `UIControls` 2130 and 2131 in container 126; `Main/iMission.cpp:1024-1030`,
`Main/iChapterMap.cpp:187-191`, `Main/iGlobalMap.cpp:170-174`, `Main/iCluesMenu.cpp:430`.

The Journal lists every clue that is placed, found and not destroyed, in the order found, by zone,
or by the zone each clue points to (`Main/iCluesMenu.cpp:238-296`). Selecting a line shows the
completed objective's description (123-137).

A script can add a journal entry with functions that exist:
`ScenarioGiveClue( "NAME", 1, 1 )` and optionally `ClueShow( "NAME" )`. There is no way to show a
pending task, and no way to mark an entry done other than giving a second clue.

### 6.2 Gold-era functions, as committed

`port/luacompat/lua_compat.cpp:40-65` lists the names that resolve to a logged no-op returning
nil (`NoOpStub`, 84-88). A name registered in `pRegList` never reaches that fallback.

| Function | Committed build |
|---|---|
| `ScenarioAddGoal` | no-op |
| `ScenarioSetGoalComplete` | no-op |
| `ScenarioSetTaskComplete` | no-op |
| `BeginZone` | no-op |
| `SetLeaveZoneMode` | no-op |
| `ShowLeaveZoneDialog` | no-op |
| `ShowLoseDialog` | no-op |
| `LeaveToSubZone` | no-op |
| `GetScenarioNumber` | no-op, returns nil |
| `c_StartGameEx`, `c_DelayGameStartEx` | no-op |
| `PlayerGiveTurn`, `WantTurnBased`, `ShowHint`, `FadeIn`, `FadeOut`, camera family | no-op |
| `GetGlobalGameVar`, `SetGlobalGameVar` | real, but per mission world (`Main/scriptCommon.cpp:355-400`) |
| `IsUIActionIDPresent`, `TableGetSize`, `UnitGetSkill`, `UnitSetSkill`, `UnitGetSkillMaxValue`, `UnitSetSkillMaxValue` | real (`Main/ScriptFunctions.cpp:59-69`) |

### 6.3 Uncommitted work seen in the engine tree

On 2026-10-02 between 08:00 and 08:16 the engine working tree held uncommitted edits by another
session that implement the three goal functions:

- New files `Main/scriptScenarioGoal.cpp`, `Main/scScenarioGoal.cpp`, `Main/scScenarioGoal.h`,
  `DBFormat/DataScenarioGoal.cpp`, `DBFormat/DataScenarioGoal.h`; edits to
  `Main/ScriptFunctions.cpp`, `Main/scScenarioTracker.*`, `Main/scFlowChartItems.*`,
  `DBFormat/DataScenario.*`, `DBFormat/DataFormat.cpp`, `DBFormat/DataDifficulty.*`.
- Signatures there: `ScenarioAddGoal( goalID )`, `ScenarioSetGoalComplete( goalID, complete = true )`,
  `ScenarioSetTaskComplete( goalID, taskIndex, complete = true )` with a 0-based task index.
  They act on the current zone.
- They read the retail tables 0x6F `ScenarioGoals` (`GoalName`, `Task1..6`) and 0x6E
  `ScenarioTasks` (`Tag`, `Description`), and `ScenarioClues.GoalID`. `tools/table_names.py` has
  no names for these two tables; they are reachable as `db[0x6F]` and `db[0x6E]`.
- Nothing calls the function that collects goals for display, and there is still no handler for
  the `objectives` event. Even with this work, goals would be stored but not shown.
- Whether these edits compile or run is **unverified**, and they may change or be dropped.

---

## 7. Minimal new campaign: required rows and files

Layout assumed: base `BASE`, first mission `M1`, second mission that doubles as `FFIGHT`. IDs in
capitals are placeholders for new, unused record IDs. Columns not listed are ignored by Jan03 and
may be left at 0 or empty.

This layout has a three-zone route, so the graph is reported as incorrect and all zone
difficulties are 0 (2.6). The campaign is still functional by the code. To get computed
difficulties the shortest route must have six zones: `BASE` → four zones in sequence → `FFIGHT`.

None of this has been run. Treat the whole checklist as **unverified** until a build loads it.

### 7.1 Scenario graph

- [ ] `Scenarios`: `ID = SCN`, `Name = 'SS2'`, `Description` free text.
- [ ] `ScenarioZones`, all with `Scenario = SCN`, `TemplateID2 = 0`, `TemplateID3 = 0`,
      `CluesMaxNumber = 255`, `CanBeRevealed = 0`:

  | ID | `SmallDescription` | `TemplateID1` | `ItemSlots` | `PersonSlots` |
  |---|---|---|---|---|
  | `Z_BASE` | `Base` | base template | 0 | 0 |
  | `Z_M1` | `M1` | mission 1 template | number of item clue slots in the map | number of person clue slots |
  | `Z_FF` | `FFight` | mission 2 template | same rule | same rule |

- [ ] `ScenarioObjectives`, all with `Scenario = SCN`, `Type = 'Capture'`:

  | ID | `ZoneToOpen1` | `Description` |
  |---|---|---|
  | `O_START` | `Z_M1` | string: briefing text |
  | `O_M1` | `Z_FF` | string: text shown when mission 1 is done |
  | `O_FF` | 0 | string: ending text |

- [ ] `ScenarioClues`, all with `Scenario = SCN`, `Type = 'Conclusion'`, `Permanent = 1`,
      `MinParentToOpen = -1`, `ItemID = 0`, `PersID = 0`, `State = 0`, `Objective2 = 0`:

  | ID | `SmallDescription` | `ZoneToPlace1` | `Objective1` | `Description` | How it is found |
  |---|---|---|---|---|---|
  | `C_START` | `SS2_START` | `Z_BASE` | `O_START` | string: journal line | automatically at campaign start |
  | `C_M1` | `SS2_M1_DONE` | `Z_M1` | `O_M1` | string | mission 1 script: `ScenarioGiveClue( "SS2_M1_DONE", 1, 1 )` |
  | `C_FF` | `SS2_FF_DONE` | `Z_FF` | `O_FF` | string | mission 2 script |

- [ ] `ScenarioObjective2Clues`: none needed.
- [ ] `Strings`: one row per clue `Description`, per objective `Description`, and per sector
      description below.
- [ ] For a clue the player must carry out instead: `Type = 'Item'` with `ItemID`, or
      `Type = 'Person'` with `PersID`, `Permanent = 0`, and a matching slot in the map (2.4).

### 7.2 Maps

- [ ] `Templates` and `TemplVariants` (with `ScriptID`), placement rows and a `Scripts` row for
      each of the three zones. Each map needs a deploy point.
- [ ] `GlobalMaps`: `ID = GM`, `Scenario = SCN`, `BaseZoneID = Z_BASE`, `Background` = a UI
      texture (retail 523).
- [ ] `ChapterMaps`: `ID = CM`, `Background` = a UI texture (retail 485), `CampZone1..4 = 0`.
- [ ] File `Chapters\<CM>` in the working directory (layout 3.3): `nMapID` = the background
      texture ID, `vDeployPos`, and these sectors:

  | `eType` | `nTemplate` | points | Purpose |
  |---|---|---|---|
  | 0 `ZONE` | `Z_BASE` | one point | The way back to the base. Needed because the `basezone` button is hidden without a side |
  | 0 `ZONE` | `Z_M1` | one point | Mission 1 |
  | 0 `ZONE` | `Z_FF` | one point | Mission 2; appears when `C_M1` is found |
  | 2 `EXITZONE` | -1 | one point | Optional; back to the global map |

  Keep the icons at least 69 pixels apart.
- [ ] File `Globals\<GM>`: `nMapID` = the background texture ID, `nScenarioID = SCN`, one sector
      with `nImageID` = a sector widget container (a retail one such as 328, or your own with the
      controls of 3.6), `nTemplate = CM`, `nDescriptionID = -1`, `vImagePos`, and a polygon
      of at least three points.

### 7.3 Starting it

- [ ] Config line: `global <GM>`. Party: RPGPers 54, 53, 14. No side.
- [ ] Expected flow by the code: base mission → Leave → global map → click the sector → chapter
      map → walk the marker onto the M1 icon and click the marker → mission 1 → script gives
      `SS2_M1_DONE` → Leave → chapter map, the clue pops up and the `FFight` icon appears.

### 7.4 Optional rows

- [ ] `RPGStoreItems` with an empty `SideID` and a negative `Rating` to stock the base store for a
      side-less player: stock = `( 0 − Rating ) × Quantity`.
- [ ] `Units.RelativeLevel` on enemies to set their level, since zone difficulty is 0.
- [ ] `Sides` row `ID = SIDE` (not 1 or 2), `GlobalMap = GM`, `UIBaseFlag`, `UIBaseFlagActive`,
      `HeroDialogPersID` = a valid `DialogPers` row, hero columns as retail. With stock code it is
      used only by the `zone` command. It becomes the campaign's side once the engine can start a
      campaign for an arbitrary side. Make sure its `GlobalMaps` row has a valid `Scenario` (1.3).
- [ ] `RPGPers` rows with `SideID = SIDE` for the hiring roster, and `RPGStoreItems` with
      `SideID = SIDE`, for that same future.

### 7.5 Engine changes that would remove the blockers

| Need | Smallest change | Where |
|---|---|---|
| Start a campaign for any side | A console command that builds `CreateGlobalPlayer( side )`, adds a hero and calls `CICBeginGame( side.GlobalMap, ... )`, or a side menu that reads `Sides` | `Main/iSideMenu.cpp:226-236`, `Main/iFaceGen.cpp:285-295` |
| Objectives screen | A consumer for the `objectives` event and a screen fed by the tracker | `Main/iMission.cpp` near 1024; section 6.3 |
| Script veto on leaving | Route `endmission` through the script before `CICEndMission` | `Main/iMission.cpp:1210-1217` |
| Campaign variables | Store the variable table in `CGlobalGame` | `Main/scriptCommon.cpp:355-400`, `Main/RPGGlobal.h:115-149` |
| Short campaigns with real difficulty | Relax the six-zone test or read a per-zone difficulty column | `Main/scFlowChart.cpp:679-689,643-677` |
