# Lua script API of the Jan03 port build

Lookup reference for mission authors: every function a mission script can call in the current build, the retail helper layer on top of it, and the constants.

**Status, 2026-10-02.** Written from the C++ and Lua sources; nothing here was run for this note. Statements are "by code" unless marked **unverified**. Call counts ("Used") are call sites in the 113 retail `Scripts` rows of `game.db.retail`; a count after `+` is call sites inside `Common.l` / `TriggersManager.l`.

Path conventions:

- `Main/...`, `Script/...`, `DBFormat/...`, `Misc/...` are under `D:\Code\Silent-Storm\Soft\Andy\Jan03\a5dll\`.
- `port/...` is under `D:\Code\Silent-Storm\`.
- `Common.l`, `Constants.l`, `TriggersManager.l`, `Hint.l` are in `build/run/scripts/`.
- Engine tree state: git `3514832c4` plus uncommitted scenario-goal files (`Main/scriptScenarioGoal.cpp`, `Main/scScenarioGoal.cpp`). The staged `build/run/SS2.exe` (2026-10-02 08:04) contains the scenario-goal functions but predates engine commit `d98886b6f` (a Lua VM fix for "attempt to call a string value" after a no-op stub call).

Contents: [Reading the tables](#reading-the-tables) | [1. Engine functions](#1-engine-functions) | [2. Callbacks from the engine](#2-callbacks-from-the-engine) | [3. Gold-era functions](#3-gold-era-functions-portluacompat) | [4. Lua-side helpers](#4-lua-side-helpers) | [5. Constants](#5-constants) | [6. Lua 4.0 notes](#6-lua-40-notes)

---

## Reading the tables

The registration table is `pRegList` in `Main/ScriptFunctions.cpp:32-183`: **126 names** (115 from the January 2003 source, 11 added by the port, marked *(port)*). No other file registers script functions.

Most functions are declared with `BEGIN_SCRIPT_COMMAND( Name, "spec" )` (`Main/scriptCommon.h:17`); the spec string is checked by `Script::CheckArgs` (`Script/Script.cpp:118-229`) before the body runs:

| Code | Accepts | Notes |
|---|---|---|
| `n` | number | Numeric strings are accepted. Read as float and truncated to int. |
| `s` | string | Numbers are accepted and converted. |
| `u` | handle (userdata) | `nil` is a **script error**. A handle whose object has been destroyed gives the console warning "Argument N is no more valid" and is passed on as null, so the function does nothing. |
| `b` | flag | `nil` is false, **any number is true, including 0**. A handle, table or non-numeric string is a script error. |
| `x[default]` | optional | A trailing argument with a default may be omitted. |

- A missing required argument is a script error ("Not enough arguments when calling function X"); a wrong type is "Wrong type of argument N". Either one kills the calling thread (see [6](#6-lua-40-notes)). Extra arguments are ignored.
- A handle of the wrong kind (a group where a unit is expected) is not an error: the cast fails and the function silently does nothing or returns nil.
- "Returns 1/nil" means a truth value: `1` for true, `nil` for false. "-" means no return value (the call evaluates to nil).
- In the Args column, `unit`, `group`, `obj`, `item`, `route`, `pos`, `cam` are handles; `wp` is a waypoint name; names in quotes are strings.
- **Unit orders** (marked "order") are queued on the unit with `CUnitServer::Do` (`Main/wUnitServer.cpp:288`) and return at once; use `WaitForUnit` to wait. An order is dropped silently if the unit is dead or unconscious, and does not start if the unit lacks the action points for it, unless `CHEAT_AP` or `CHEAT_SCRIPTSEQUENCE` is set (`Main/RPGUnitMission.cpp:444-455`); inside `BeginSequence`..`EndSequence` every unit has `CHEAT_SCRIPTSEQUENCE`. A new order given while another is running cancels the running one and starts when it has stopped.

---

## 1. Engine functions

### 1.1 Units (25)

Source: `Main/scriptUnit.cpp` (line in the last column).

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `GetUnit` | `"name"` | unit or nil | Looks a unit up by name (case-insensitive). Console warning "unit [x] not found" when missing. | 387 | 37 |
| `CreateUnit` | `persID, playerID, "name", wp, level` | unit or nil | Creates an RPGPers character for the given player at the waypoint, sets its XP level, registers the name, puts it on the nearest passable tile and refreshes visibility. nil if the waypoint, player or pers is missing. | 3 | 46 |
| `GetHero` | - | unit or nil | The unit of the first party member flagged as hero. Under `map <id>` all three default party members are flagged, so it is the first one (`Main/RPGGlobal.cpp:225,309`). | 76 +2 | 470 |
| `UnitGetName` | `unit` | string or nil | The registered name, **in upper case** (names are stored upper-cased). nil if the unit has none. | 6 +1 | 429 |
| `UnitRemove` | `unit` | - | Removes the unit from the world (dies silently, leaves its player and the AI). If the unit's pers is a scenario clue not yet found, the clue is marked destroyed. | 36 +1 | 411 |
| `UnitSetPlayer` | `unit, playerID` | - | Moves the unit to another player: cancels its action, takes that player's diplomacy, re-registers it with AI. No-op if the player does not exist. | 16 | 443 |
| `UnitIsDead` | `unit` | 1/nil | Dead state. Returns nothing for a stale handle. | 11 +2 | 273 |
| `UnitIsUnconscious` | `unit` | 1/nil | Unconscious state. | 3 +1 | 285 |
| `UnitIsAction` | `unit` | 1/nil | 1 while the unit is executing an order (moving, shooting, animating). | 4 +3 | 205 |
| `UnitCancelAction` | `unit` | - | Cancels the current order, aimed-shot preparation and healing. | 33 +1 | 405 |
| `UnitPlayAnimation` | `unit, animID, bLoop` | - | Order: play an Animations record on the unit; `bLoop` non-nil repeats it until cancelled. `bLoop` is required (pass `nil` for once). | 33 | 372 |
| `UnitSetXPLevel` | `unit, level` | - | Sets the experience level and recomputes all skills; perk points change by the level difference (`Main/rpgUnit.cpp:390`). | 4 | 152 |
| `UnitTakePerk` | `unit, perkID` | - | Takes a perk from the unit's perk tree and spends one perk point. Unknown IDs are ignored. | 26 | 399 |
| `UnitDrawPerksTree` | `unit` | - | Debug: prints the perk tree to the console. | 0 | 392 |
| `UnitSetSkill` *(port)* | `unit, ST_*, value` | - | Sets the current value of a skill or stat. Index outside 0..16 is ignored. | 52 | 592 |
| `UnitSetSkillMaxValue` *(port)* | `unit, ST_*, value` | - | Sets the maximum of a skill or stat (set this before `UnitSetSkill` to raise both). | 51 | 600 |
| `UnitGetSkill` *(port)* | `unit, ST_*` | number or nil | Current value. | 24 | 608 |
| `UnitGetSkillMaxValue` *(port)* | `unit, ST_*` | number or nil | Maximum value. | 20 | 618 |
| `UnitCheat` | `unit, CHEAT_*, bOn` | - | Sets or clears one cheat bit. For `CHEAT_NOAI` on an AI unit it also suspends or resumes the unit's current AI control. `bOn` is required. Flag effects are listed in [5](#5-constants). | 0 +1 | 336 |
| `UnitPlaceInPocket` | `unit` | - | Puts the unit in the "pocket": it is taken off the map but keeps existing. No-op if already there. | 5 | 517 |
| `UnitRestoreFromPocket` | `unit` | - | Brings a pocketed unit back in its normal state. | 3 | 529 |
| `UnitTakeCorpse` | `unit, body` | - | Order: pick up a dead or unconscious unit. Ignored unless `unit` can fight and `body` cannot. | 5 | 480 |
| `UnitDropCorpse` | `unit` | - | Order: drop the carried body. | 3 | 491 |
| `UnitAI` | `unit` | - | Debug: prints the AI's view of the unit's inventory (AI units only). | 0 | 566 |
| `HasInventoryItem` | `itemID` | count or nil, unit | **Two results.** Counts RPGItems `itemID` in the backpacks and both hand slots of every unit of the non-AI players; the second result is the last unit found holding one. The only inventory query that works in this build. | 0 | 86 |

### 1.2 Groups (12)

A group is an ordered set of units without duplicates; indexes are **0-based**. Source: `Main/scriptUnitGroup.cpp`.

`GroupMoveToWaypoint`, `GroupCheat` and `GroupGetVisible` use every member without checking that the unit still exists. Take a unit out of its groups before `UnitRemove` (what happens otherwise is **unverified**).

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `CreateGroup` | `"name", ...` | group | New script-owned group from zero or more unit **names** (not handles); unknown names are skipped. A non-string argument, including nil, is undefined behaviour (null string, likely crash). | 24 +3 | 18 |
| `GetGroup` | `groupID` | group or nil | A group defined in the map, by its integer ID. Warning "group number N not found" when missing. | 105 | 38 |
| `GroupGetID` | `group` | number | The group's ID; 0 for script-made groups or a bad handle. | 0 | 53 |
| `GroupAddUnit` | `group, unit` | - | Adds the unit if it is not already a member. | 13 +2 | 62 |
| `GroupRemoveUnit` | `group, unit` | - | Removes the unit if it is a member. | 23 +3 | 70 |
| `GroupGetSize` | `group` | number or nil | Member count. **Dead units still count**; a removed unit leaves an empty slot that `GroupGetUnit` returns as nil. | 138 +26 | 78 |
| `GroupGetUnit` | `group, index` | unit or nil | Member at a 0-based index. Out of range gives nil and a console warning. | 246 +24 | 86 |
| `GroupIsContainUnit` | `group, unit` | 1/nil | Membership test. | 0 | 112 |
| `GroupAddGroup` | `group, group` | group or nil | New group with the members of both (union). | 22 | 185 |
| `GroupGetCross` | `group, group` | group | New group with the units present in both (intersection). Empty group if either handle is bad. | 8 +1 | 203 |
| `GroupCheat` | `group, CHEAT_*, bOn` | - | Sets or clears a cheat bit on every member. Unlike `UnitCheat` it does not suspend AI control for `CHEAT_NOAI`. | 0 | 173 |
| `PlayerGetUnits` | `playerID` | group | New group with all units of a player (0 is the human player). Empty group if the player does not exist. | 51 +1 | 219 |

### 1.3 Movement, routes and positions (15)

Sources: `Main/scriptRoute.cpp` (R), `Main/scriptUnit.cpp` (U), `Main/scriptUnitGroup.cpp` (G), `Main/scriptPosition.cpp` (P). Routes are AI controls: they work only for units of an AI player (`Main/aiRoute.cpp:158-217`); for a unit of the human player they do nothing.

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `UnitMoveToWaypoint` | `unit, wp` | - | AI unit: gives it a one-waypoint route (wait with `WaitForUnitRoute`). Human-player unit: path order (wait with `WaitForUnit`). | 202 +2 | R:86 |
| `UnitSetToWaypoint` | `unit, wp` | - | Teleports the unit to the waypoint, standing, then (AI units) pins it there with a one-waypoint route. Immediate. | 40 +3 | R:68 |
| `GroupMoveToWaypoint` | `group, wp` | - | Path order for every member to a formation spot around the waypoint. Works for any player's units. | 57 | G:127 |
| `UnitSetPose` | `unit, POSE_*` | - | Order: change pose in place. | 39 +1 | U:249 |
| `UnitSetWishPose` | `unit, POSE_*` | - | Sets the pose the unit uses for later moves (for example `POSE_RUN`). Returns at once. | 74 +1 | U:239 |
| `UnitSetDirection` | `unit, DIR_*` | - | Order: turn in place. | 123 +1 | U:261 |
| `CreateRoute` | `wp, ...` | route | Route through the named waypoints; unknown names are skipped (with a warning). Arguments must be strings. Each waypoint's own commands from the map (pose, direction, wait) are executed on arrival. | 19 | R:23 |
| `UnitSetRoute` | `unit, route, bLoop` | - | AI unit follows the route; `bLoop` non-nil repeats it (needs more than one waypoint). `bLoop` is required. Interrupts the unit's current AI control. | 6 | R:37 |
| `GroupSetRoute` | `group, route, bLoop` | - | Same for a group: members head for formation spots around each waypoint and synchronise there before going on. | 13 | R:46 |
| `UnitGetRoute` | `unit` | route task or nil | The task the AI unit is following now. nil for human-player units or when there is none. | 0 +2 | U:541 |
| `RouteIsFinished` | `task` | 1/nil | 1 when the task from `UnitGetRoute` has run all its commands. Looped routes never finish. Any other handle gives 1. | 0 +2 | U:558 |
| `UnitRoaming` | `unit, wp, radius` | - | AI unit wanders around the waypoint indefinitely; radius is in movement action points. | 12 +1 | R:109 |
| `GetPos` | `unit` or `obj` | pos | Position object for a unit or map object. Any other handle gives (0,0,0). | 48 +3 | P:17 |
| `GetWaypointPos` | `wp` | pos | Position object for a waypoint (its exact map position, not the snapped tile). (0,0,0) if unknown. | 36 +2 | P:28 |
| `GetDistance` | `pos, pos` | number | 3-D distance in tiles (one tile is 0.625 world units, `Main/Grid.h:7`). 0 if either argument is not a position. | 44 +2 | P:37 |

### 1.4 Combat, visibility and diplomacy (16)

Sources: `Main/scriptUnit.cpp` (U), `Main/scriptUnitGroup.cpp` (G), `Main/scriptDiplomacy.cpp` (D), `Main/scriptCommon.cpp` (C).

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `UnitShoot` | `unit, target, HL_*` | - | Order: attack the target unit with the weapon in hand, aiming at a hit location (`HL_ANY` for none). All three arguments are required. | 16 | U:214 |
| `UnitSetShootMode` | `unit, SM_*` | - | Order: switch fire mode. | 8 | U:229 |
| `UnitReload` | `unit` | - | Order: reload. | 3 | U:327 |
| `UnitActivateWeapon` | `unit, bReady=true` | - | Order: raise the weapon (default) or lower it (`nil`). | 36 +1 | U:506 |
| `UnitHide` | `unit` | - | Order: **toggles** hiding (stealth) on or off (`Main/wUnitExec.cpp:739`). | 11 | U:383 |
| `UnitApplyCritical` | `unit, criticalID` or `unit, location, type` | - | Applies a critical at once. Two arguments: a Criticals table record. Three arguments: `ECriticalLocation` (0 head, 1 torso, 2 arms, 3 legs, 4 any) and `ECritical` (0 death, 1 AP reduction, 2 blind, ... `DBFormat/DataRPG.h:632-670`). | 5 | U:161 |
| `UnitKill` | `unit` | - | Applies the death critical immediately. | 22 | U:362 |
| `UnitMakeUnconscious` | `unit` | - | Knocks the unit out immediately. | 11 | U:500 |
| `Explosion` | `grenadeID, wp` | - | Grenade explosion (an RPGGrenade record: damage, effect, sound) at the waypoint, with no owner. An invalid grenade ID is not checked (**unverified**, likely crash). | 14 | C:299 |
| `UnitGetVisible` | `unit` | group | New group with the units of **other players** this unit currently sees. Each call registers a new group in the world that is never removed, so avoid calling it every tick. | 4 +1 | U:299 |
| `GroupGetVisible` | `group` | group or nil | Union of what the members see. Same registration caveat. | 8 +1 | G:152 |
| `UnitIsSeeUnit` | `watcher, target` | 1/nil | Line-of-sight visibility check through the RPG rules, computed on the spot. | 3 | U:311 |
| `GetDiplomacy` | `playerA, playerB` | DS_* | How player A regards player B. | 0 | D:15 |
| `SetDiplomacy` | `playerA, playerB, DS_*` | - | Sets how A regards B, for the player and all its current units. **One-directional**: call it both ways for mutual hostility. | 39 | D:24 |
| `UnitGetDiplomacy` | `unit, playerID` | DS_* or nil | How this one unit regards a player. | 0 | D:38 |
| `UnitSetDiplomacy` | `unit, playerID, DS_*` | - | Overrides it for this one unit. | 7 | D:51 |

Example: `SetDiplomacy( 2, 0, DS_ENEMY ) SetDiplomacy( 0, 2, DS_ENEMY )`.

### 1.5 Objects, doors and items (16)

Source: `Main/scriptObject.cpp`. "Object" is a placed map object (door, window, crate, prop); "item" is an inventory item lying on the ground.

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `GetObject` | `"name"` | obj or nil | Map object by name. Warning "object [x] not found" when missing. | 242 | 52 |
| `CreateObject` | `rndObjectID, wp, angleDeg, "name"` | obj or nil | Creates an object from a RndObjects record at the waypoint, rotated by `angleDeg`, and registers the name. | 0 | 111 |
| `ObjectGetName` | `obj` | string or nil | Registered name, in upper case. | 7 | 183 |
| `ObjectOpen` | `door` | - | Opens a door or window with animation and sound; fires its trap if it has one. No-op if locked, broken or already open. `OnOpenObject( nil, door )` is called when the animation ends. | 12 | 68 |
| `ObjectClose` | `door` | - | Closes it; `OnCloseObject( nil, door )` follows. | 35 | 73 |
| `ObjectIsOpened` | `door` | 1/nil | Open state. nil for anything that is not a door or window. | 15 | 78 |
| `ObjectDestroy` | `obj` | - | Destroys any attackable object by sending a lethal attack through the normal damage code. | 0 | 87 |
| `ObjectRemove` | `obj` | - | Deletes the object from the world with no effects. | 25 | 104 |
| `ObjectSetToWaypoint` | `obj, wp, angleDeg` | - | **Broken**: reads the object from the wrong argument slot (`scriptObject.cpp:147`), so it never moves anything. | 0 | 144 |
| `ObjectSetDestroyStage` | `obj, stage` | - | Sets the object's destruction stage directly. Retail scripts use 0 and 1; what each stage means depends on the object (**unverified**). | 195 | 176 |
| `ObjectPlayAnimation` | `obj, animID` | - | Plays an Animations record on an animated object. | 6 | 160 |
| `ObjectIsAction` | `obj` | 1/nil | 1 while an animated object is playing. | 0 +1 | 167 |
| `ObjectCancelAction` | `obj` | - | Stops the object's animation. | 0 | 200 |
| `GetItem` | `"name"` | item or nil | Ground item by name (map item name, or a clue item's `SmallDescription`). Warning when missing. | 10 | 22 |
| `ItemGetName` | `item` | string or nil | Registered name, in upper case. | 0 | 31 |
| `ItemRemove` | `item` | - | Removes the ground item from the world. | 2 | 46 |

### 1.6 Camera and sequences (8)

Source: `Main/scriptSequence.cpp`. UI commands are queued and executed one at a time by the mission screen (`Main/iMission.cpp:1808`).

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `GetCamera` | `cameraID` | cam or nil | Handle to a Cameras record. | 232 | 82 |
| `CameraMove` | `cam, ms` | action id (0) or nothing | Queues a camera move to the record's placement over `ms` milliseconds (0 jumps). Does not block; returns the action id `AT_CAMERA` for `WaitForUI`. Returns nothing if `cam` is not a camera handle. | 73 +1 | 87 |
| `Floor` | `n` | - | Sets the floor the view is cut at. | 88 | 113 |
| `c_BeginSequence` | `bBlockInput=true` | - | Starts a scripted sequence: letterbox UI, camera limits off, `CHEAT_SCRIPTSEQUENCE` on every unit (free AP, AI ignores them, current orders cancelled), AI tactical commanders release their units, real time is forced. The argument is read but not used. Call it through `BeginSequence`. | 0 +1 | 50 |
| `EndSequencePart` | - | - | Marks a skip point. When the player presses cancel during a sequence the game fast-forwards (at most 1200 steps) to the next `EndSequencePart` or `EndSequence` (`Main/iMission.cpp:853`). | 16 | 57 |
| `EndSequence` | - | - | Ends the sequence: removes the letterbox, clears the sequence cheat, releases forced real time, refreshes visibility. | 56 +2 | 62 |
| `IsInterfaceAction` | `id=0` | 1/nil | 1 while an action of that kind is outstanding: 0 camera moves, 1 dialogues. The counter goes up in `CameraMove` / `DialogPlay` and down when the UI reports the action finished. Other ids give nil. | 0 | 71 |
| `IsUIActionIDPresent` *(port)* | `id=0` | 1/nil | The Gold name for the same function; `WaitForUI` polls it. | 0 +1 | 71 |

The "action id" is the action **kind** (0 or 1), not a per-call ticket: `WaitForUI( CameraMove( c, 1000 ) )` waits until all queued camera moves are done.

Hazard, by code and not reproduced: a `DialogPlay` issued while the player is skipping a sequence is dropped by the UI ("Dialog in WaitForPartFinished mode ignored", `Main/iMission.cpp:1840`) without the finished event, so the dialogue counter never returns to 0 and `WaitForUI( DialogPlay( .. ) )` waits forever, then and on every later dialogue.

### 1.7 Dialogue and UI (8)

Sources: `Main/scriptDialog.cpp` (D), `Main/scriptUnit.cpp` (U), `Main/scriptScenario.cpp` (S), `Main/scriptSequence.cpp` (Q). See `dialogue-and-text.md` for what is actually drawn.

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `DialogPlay` | `"code"` | action id (1) or nothing | Queues the full-screen dialogue whose Dialogs record has that Code. Does not block; returns `AT_DIALOG` for `WaitForUI`. Returns nothing if the code is unknown. A second argument (Gold's "hero on left") is ignored. | 82 +1 | D:14 |
| `DialogPlayAsAcks` | `"code"` | - | Queues the first phrase of the dialogue as an acknowledgement bark instead of the full-screen dialogue (`Main/iMission.cpp:1851`). No action id. | 31 | D:26 |
| `UnitSayAck` | `unit, conditionID` | - | Queues the unit's acknowledgement for that condition (Acks rows matching the unit's pers and the condition). | 5 | U:79 |
| `UnitSetDialog` | `unit, "code"` | - | Sets the dialogue played when the hero talks to this unit, and makes the unit talkable. An unknown code clears the dialogue. | 2 | U:455 |
| `UnitSetCanTalk` | `unit, bCan=true` | - | Enables or disables the talk action on the unit. Only the hero can talk (`Main/wUnitAttackExec.cpp:2586`). | 10 | U:464 |
| `ClueShow` | `"clueName"` | - | Opens the clue screen for a scenario clue. Needs a running scenario. Returns nothing, so `WaitForUI( ClueShow( .. ) )` does not wait. | 11 | S:64 |
| `uiShowStore` | - | - | Opens the base store screen. | 5 | Q:103 |
| `uiShowTeamMngMenu` | - | - | Opens the team management screen. | 3 | Q:108 |

### 1.8 Scenario and campaign (12)

Sources: `Main/scriptScenario.cpp` (S), `Main/scriptScenarioGoal.cpp` (G), `Main/scriptCommon.cpp` (C). Clues and zones are found by their `SmallDescription`, case-insensitive. The clue, zone and goal functions need a running scenario, and the goal functions and `GetCurrentZoneAILevel` need a current scenario zone: a mission started with `map <id>` has neither. `Main/scriptScenarioGoal.cpp` is uncommitted and still being edited in the engine tree; its line numbers below are as of 2026-10-02 08:03 and will shift.

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `ScenarioGiveClue` | `"clue", bTake=true, bNow=false` | - | Marks a clue taken (default) or destroyed (`bTake` nil). With `bNow` it is processed at once; otherwise it is queued until the scenario flow chart is next expanded (`Main/scScenarioTracker.cpp:512`; on leaving the zone, **unverified**). | 12 | S:16 |
| `ClueIsFound` | `"clue"` | 1/nil | Whether the clue has been found. | 5 | S:75 |
| `ScenarioOpenZone` | `"zone"` | - | Makes a scenario zone available. | 0 | S:35 |
| `ScenarioBlockZone` | `"zone"` | - | Blocks a scenario zone. | 0 | S:47 |
| `ScenarioAddGoal` *(port)* | `goalID` | - | Adds a ScenarioGoals record to the current zone's objectives. Debug log "[scenario] goal N NOT added" when there is no zone or no such record. | 14 | G:21 |
| `ScenarioSetGoalComplete` *(port)* | `goalID, bDone=true` | - | Marks a goal completed, or failed when `bDone` is nil. Console warning "Could not complete goal N" if the goal is not in the zone. | 26 | G:30 |
| `ScenarioSetTaskComplete` *(port)* | `goalID, taskIndex, bDone=true` | - | Same for one task of a goal; `taskIndex` is 0-based. | 45 | G:46 |
| `GetCurrentZoneAILevel` | - | number or nil | Difficulty level of the current scenario zone. | 0 | S:90 |
| `ExitToChapter` | - | - | Leaves the mission to the chapter map. | 6 +1 | S:59 |
| `Difficulty` | `difficultyID` | - | Switches the game to another Difficulty record. Unknown IDs are ignored. | 0 | C:314 |
| `GetGlobalGameVar` *(port)* | `"key", default` | value | Reads a script variable store keyed by string; returns `default` (or nil) when unset. Values keep their type. | 20 | C:355 |
| `SetGlobalGameVar` *(port)* | `"key", value` | - | Writes it. The store is a Lua table in this world's script state, so it does **not** carry over to another zone as it did in Gold. | 19 | C:382 |

### 1.9 World and miscellaneous (14)

Sources: `Main/scriptCommon.cpp` (C), `Script/lapi.cpp` (L), `Main/scriptPtr.cpp` (P), `Main/scriptTemplate.cpp` (T), `Main/ScriptFunctions.cpp` (F).

| Function | Args | Returns | What it does | Used | Line |
|---|---|---|---|---|---|
| `out` | any number of values | - | Prints the values, with nothing between them, as one console line. Strings and numbers print as text, nil as `NIL`, a handle as its kind and name (`Unit [NAME]`, `UnitGroup 12`, `Position ( x, y, z )`). Tables and functions print nothing. | 428 +9 | C:101 |
| `Sleep` | `ticks=1` | - | Suspends the calling thread for that many world ticks. See [6](#6-lua-40-notes). | 655 +18 | L:437 |
| `StartThread` | `function, args...` | - | Starts the function as a new thread with the given arguments. The first argument must be a function value, not a name. | 225 +1 | L:414 |
| `random` | `n` or `a, b` | number | `random( n )`: integer 0..n-1. `random( a, b )`: integer a..b-1 (b is **excluded**). `random()` and a non-number return 0. `random( 0 )` and `random( a, a )` divide by zero. | 69 | C:147 |
| `IsRealTime` | - | 1/nil | 1 in real-time mode, nil in turn-based mode. | 0 | C:161 |
| `GetTurn` | - | number | Turn counter, from 0. In real time a turn passes every 20 s of game time (`Main/wMain.cpp:73`); while real time is forced by a sequence it does not advance (`Main/wMain.cpp:1876`). | 4 +2 | C:309 |
| `PlaceTemplate` | `templateID, wp` | - | Builds a random variant of a Templates record at the waypoint: its objects, waypoints, AI units (at the difficulty's AI level) and groups, then runs the variant's scripts. Console error "can't load template" on failure. | 69 | T:14 |
| `Ptr` | `handle` | handle or nothing | Weak-reference copy of a handle. | 0 | P:32 |
| `ObjPtr` | `handle` | handle or nothing | Owning-reference copy of a handle: the object stays alive while the script holds it. | 0 | P:43 |
| `IsValid` | `value` | 1/nil | 1 if the value is a handle whose object still exists. nil for nil, numbers, strings and stale handles; never an error. | 53 +11 | P:64 |
| `IsEqual` | `handle, handle` | 1/nil | Whether two handles refer to the same object. Use it instead of `==` (a weak and an owning handle to the same object are different Lua values). | 16 | C:319 |
| `TableGetSize` *(port)* | `table` | number | Lua 4 `getn`: the table's `n` field, else its largest positive integer key. 0 for a non-table. | 12 | C:346 |
| `LuaTest` | - | - | Developer test; calls a non-existent Lua function. No effect. | 0 | C:287 |
| `_ERRORMESSAGE` | `"message"` | - | The error hook the VM calls on a script error; prints "Script error: ..." to the console. Not meant to be called; redefining it replaces error reporting. | 0 | F:23 |

---

## 2. Callbacks from the engine

The engine calls these global Lua functions when they exist; each call runs as a new thread (`Main/scriptCommon.cpp:252-284`). A missing function is ignored.

| Function | Called when | Source |
|---|---|---|
| `OnOpenObject( unit, object )` | A door or window has finished opening. `unit` is nil when a script opened it. | `Main/wObject.cpp:205` |
| `OnCloseObject( unit, object )` | A door or window has finished closing. | `Main/wObject.cpp:207` |
| `OnTalk( who, target )` | The hero uses the talk action on a talkable unit; runs before the unit's dialogue starts. | `Main/wUnitAttackExec.cpp:2578` |
| `OnMineTriggered( unit )` | A mine or a door trap goes off; `unit` may be nil. | `Main/wMine.cpp:77`, `Main/wObject.cpp:274` |
| `OnDialogPhrase( "code", n )` | A dialogue shows phrase `n` (0-based). | `Main/iMissionDlgUI.cpp:310` |
| `OnDialogFinished( "code" )` | A dialogue is closed. | `Main/iMissionDlgUI.cpp:416` |
| `OnScriptNotify( "windowID", n )` | Menu screens only (side and hero selection). | `Main/iSideMenu.cpp:68`, `Main/iHeroMenu.cpp:68` |

Retail scripts also define `OnEnterZone`, `OnClickUsable`, `OnExit`, `OnShotAtUnit`, `OnMineDiffusion`, `OnPlayerLose`, `OnOpenInventory`, `OnRealExit`, `OnStartTurn` and `OnUnitNeedCommand`. Nothing in this engine build calls them.

---

## 3. Gold-era functions (`port/luacompat`)

Retail scripts were written for the later "Gold" engine, which registered 226 functions. `port/luacompat/lua_compat.cpp` keeps the missing ones from killing a script, with two tag methods installed after registration (`Main/A5Script.cpp:35`):

1. **Named stubs** (`lua_compat.cpp:40-65`, `GetGlobalFallback` :116, `NoOpStub` :84). Reading a global that is nil and whose name is in a list of 100 Gold names returns a C function that ignores its arguments and **returns one nil**. The first use of each name logs `[luacompat] stubbed missing Lua C function: <name>` to the debug output (the run log).
2. **Nil-call backstop** (`NilCallBackstop` :98). Calling *any* nil value, whether a misspelt function, a nil table field or a Gold name not in the list (`WhoHasInventoryItem`, `UnitGrenadeToWaypoint`, `StopEffect`, ...), also does nothing and yields nil. Only the first such call in a session is logged, without a name.

Consequences: a typo in a function name is not an error in this build; it silently does nothing. Check the log for `[luacompat]` lines. `if SomeGoldName then` is true for the 100 listed names, because reading the name already yields the stub.

### 3.1 Implemented (11)

Eleven names in the list are now real functions in `pRegList` and never reach the stub. They are documented in section 1.

| Name | Status | Behaviour |
|---|---|---|
| `IsUIActionIDPresent` | implemented | Alias of `IsInterfaceAction` ([1.6](#16-camera-and-sequences-8)). |
| `TableGetSize` | implemented | Lua `getn` ([1.9](#19-world-and-miscellaneous-14)). |
| `GetGlobalGameVar`, `SetGlobalGameVar` | implemented | String-keyed variable store, per world rather than per campaign ([1.8](#18-scenario-and-campaign-12)). |
| `UnitSetSkill`, `UnitSetSkillMaxValue`, `UnitGetSkill`, `UnitGetSkillMaxValue` | implemented | Read and write skills and stats ([1.1](#11-units-25)). |
| `ScenarioAddGoal`, `ScenarioSetGoalComplete`, `ScenarioSetTaskComplete` | implemented | Zone objectives, re-created from the Gold disassembly; need a current scenario zone ([1.8](#18-scenario-and-campaign-12)). |

### 3.2 No-ops (89)

Every function below is accepted with any arguments, does nothing and **returns nil**. "Calls" counts retail call sites as above. "Meant to" is inferred from the name and the retail call sites, not from code (**unverified**). Where scripts use the result, the nil matters: a test is always false, and arithmetic, comparison with `<` or use as a table key is a script error that kills the thread.

**Game flow, zones and turns (20)**

| Name | Calls | Meant to / effect of the no-op |
|---|---|---|
| `c_DelayGameStartEx` | +1 | Hold the game start; behind `DelayGameStart`. The game is not held. |
| `c_StartGameEx` | +1 | Release the held start; behind `StartGame`. |
| `PlayerGiveTurn` | 14 | Hand the turn to a player. Turn order is not changed. |
| `WantTurnBased` | 1 | Request turn-based mode. |
| `Pause` | 3 | Pause the game. |
| `BeginZone` | 5 | Enter a scenario zone from a chapter script. |
| `SetLeaveZoneMode` | 7 | Allow or forbid leaving the zone, with a message ID. |
| `ShowLeaveZoneDialog` | 4 +1 | Ask to leave the zone; behind `OnExit`. |
| `ShowLoseDialog` | 3 +2 | Game-over dialog; behind `OnPlayerLose`. |
| `LeaveToSubZone` | 3 | Move to a sub-zone. |
| `GetScenarioNumber` | 6 | Which campaign is running. nil, so `== SCEN_AXIS` and `== SCEN_ALLIES` are both false. |
| `SetFirstMissionMode` | 1 | First-mission restrictions. |
| `SetTutorialMode` | 1 | Tutorial restrictions. |
| `SetMaxCriticalSeverity` | 4 | Cap critical hits. |
| `SetTimeOfDay` | 5 | Switch lighting (`DAY`, `NIGHT`). |
| `SlowSyncAIMap` | +1 | Rebuild the AI map; behind `WaitForPassCalc`. |
| `PassCalcerIsActive` | +1 | Is the pass map being rebuilt; nil ends the wait at once. |
| `WaitForInterface` | 7 | Development-era leftover (Gold did not have it either). |
| `ScenarioClueGive` | 1 | Development-era leftover. |
| `Random` | 2 | Development-era leftover; use `random`. nil result. |

**Camera, hints, sound and effects (18)**

| Name | Calls | Meant to / effect of the no-op |
|---|---|---|
| `ShowHint` | 69 | Show a hint window. `WaitForUI( ShowHint( n ) )` returns at once. |
| `AddHints` | 2 | Register hint texts. |
| `FadeOut` | 61 | Fade the screen to black. `WaitForUI( FadeOut() )` returns at once. |
| `FadeIn` | 56 | Fade back in. |
| `CameraSequence` | 23 | Play a camera path. The camera does not move; `WaitForUI` returns at once. |
| `CameraLock` | 19 | Lock or unlock player camera control. |
| `CameraSetClipping` | 7 | Set near and far clip planes. |
| `PlayVideo` | 3 | Play a video file. |
| `PlaySound` | 12 | Play a sound. |
| `Play3DSound` | 8 | Play a positioned sound. |
| `StopSound` | 2 | Stop a sound. |
| `PlayEffect` | 1 | Play a visual effect. |
| `AttachEffectToUnitBone` | 1 | Attach an effect to a unit. |
| `AttachEffectToWaypoint` | 1 | Attach an effect at a waypoint. |
| `SetAmbientEffect` | 4 | Weather or ambient effect. |
| `CreateWindow` | 3 | Script-built UI window. nil, so later window calls get nil. |
| `GetWindow` | 1 | Find a UI window. |
| `ButtonCreateState` | 2 | Add a state to a UI button. |

**Unit behaviour (11)**

| Name | Calls | Meant to / effect of the no-op |
|---|---|---|
| `UnitSetRetreatLogic` | 25 +1 | AI: fall back to a waypoint. The unit keeps its current AI. |
| `UnitSetNormalLogic` | 12 | AI: default behaviour. |
| `UnitSetGuardLogic` | 12 | AI: guard. |
| `UnitSetFearLogic` | 4 | AI: afraid. |
| `UnitSetPanicLogic` | 3 | AI: panic. |
| `UnitSetCivilianLogic` | 2 | AI: civilian. |
| `UnitSetScriptLogic` | 3 | AI: script-driven only. |
| `UnitSetHideProbability` | 4 | AI: chance to hide. |
| `UnitKeepMoving` | 18 +1 | Do not stop on spotting an enemy. |
| `UnitStop` | 4 +1 | Stop the unit; behind `GroupStop`. Use `UnitCancelAction`. |
| `UnitLockPose` | 2 | Forbid pose changes. |

**Unit combat and perception (17)**

| Name | Calls | Meant to / effect of the no-op |
|---|---|---|
| `UnitSetToHit` | 32 | Force a hit chance (100, or -1 to reset). `UnitCheat( u, CHEAT_TOHIT, TRUE )` gives guaranteed hits. |
| `UnitGetToHitUnit` | 4 | Hit chance against a unit. nil; retail adds it up, which is a script error. |
| `UnitGetToHitWaypoint` | 1 | Hit chance against a point. |
| `UnitAttackWaypoint` | 19 | Shoot at a waypoint. No shot is fired. |
| `UnitShootPrepare` | 8 | Aim before shooting. |
| `UnitDrawWeapon` | 14 | Draw the weapon. Use `UnitActivateWeapon`. |
| `UnitSwitchToGrenade` | 2 | Put a grenade in hand. |
| `UnitGrenadeToUnit` | 1 | Throw a grenade at a unit. |
| `UnitFlyToWaypoint` | 5 | Throw the unit to a waypoint (knock-back). |
| `UnitApplyTableCritical` | 7 | Critical from the criticals table. Use two-argument `UnitApplyCritical`. |
| `UnitHealCriticals` | 2 | Remove criticals. |
| `UnitRegenerateVP` | 5 | Restore hit points. |
| `UnitIsWeaponInHand` | 4 | Weapon-type test (`WP_*`). Always false. |
| `UnitIsUsingCannon` | 1 | Mounted-gun test. Always false. |
| `UnitIsHearUnit` | +1 | Hearing test; behind `UnitIsHearGroup`. Always false. |
| `UnitInArea` | 5 +1 | Is the unit inside the rectangle of two waypoints; behind `GroupInArea`. Always false. |
| `UnitIsCarryingCorpse` | 3 | Carry test. Always false. |

**Inventory, experience and party (14)**

| Name | Calls | Meant to / effect of the no-op |
|---|---|---|
| `UnitCreateItem` | 52 +5 | Give the unit an item. Nothing is given. |
| `CreateAndActivateItem` | 9 +1 | Give an item and put it in hand. |
| `DestroyItemInHand` | 5 | Remove the item in hand. |
| `UnitHoldItem` | 6 | Put an item in hand. |
| `UnitTakeItem` | 2 | Development-era leftover. |
| `UnitTakeObject` | 1 | Pick up an object. |
| `HasInventoryItemUnit` | 5 | Does the unit carry an item. Always false; `HasInventoryItem` works. |
| `HasInventoryItemGroup` | 4 | Same for a group. Always false. |
| `FindItem` | 2 | Find an item by ID. nil. |
| `ItemSetToWaypoint` | 2 | Move a ground item. |
| `ItemUnload` | 1 | Unload a weapon. |
| `UnitGiveXP` | +1 | Award experience; behind `GroupGiveXP`. Use `UnitSetXPLevel`. |
| `UnitGiveRandomPerks` | 5 | Spend perk points at random. |
| `PlayerGetUnitsEx` | 5 | Party subset. nil; passing it to `GroupGetSize` is a script error. |

**Panzerkleins (4)**

| Name | Calls | Meant to / effect of the no-op |
|---|---|---|
| `GetUnitPK` | 7 | The suit a unit wears. nil; retail uses it as a table key, which is a script error. |
| `UnitIsWearingPK` | 11 +1 | Always false; behind `GroupIsWearingPK`. |
| `UnitWearPK` | 8 | Put a unit in a suit. |
| `UnitLeavePK` | 4 | Leave the suit; nil instead of the suit. |

**Objects (5)**

| Name | Calls | Meant to / effect of the no-op |
|---|---|---|
| `ObjectLockDoor` | 14 | Lock a door. Doors stay as the map defines them. |
| `ObjectUnlockDoor` | 18 | Unlock a door. A locked door cannot be opened by `ObjectOpen` either. |
| `ObjectGetDestroyStage` | 7 | Read the destruction stage. nil, so `== 0` and `== 1` are false and a `while .. == 0` loop ends at once. |
| `ObjectGetHP` | 4 | Object hit points. nil; retail compares it with `<`, which is a script error. |
| `ObjectRestoreFromPocket` | 3 | Bring back a hidden object. |

---

## 4. Lua-side helpers

Loaded into every world before the mission script, in this order: `Constants.l`, `TriggersManager.l`, `Common.l`, `Hint.l` (AutoLoadScripts table, `Main/wMain.cpp:408`). `Hint.l` only prints a line. All waits are polling loops built on `Sleep`, so they must be called from a thread that may block.

"No-op dep." names the section 3.2 function a helper relies on and what that does to the helper.

### 4.1 Waiting (`Common.l`)

| Helper | Line | What it does | No-op dep. |
|---|---|---|---|
| `WaitForUI( id )` | 25 | Polls `IsUIActionIDPresent( id )` every 2 ticks until the action is over. Returns at once when `id` is nil or while the delayed-start flag is set (between `DelayGameStart` and `StartGame`). | - |
| `WaitForUnit( unit )` | 40 | Sleeps 2 ticks, then waits until the unit can fight **and** is not executing an order. Never returns if the unit is dead, unconscious or nil. | - |
| `WaitForUnitCommand( unit )` | 75 | Waits until the unit **starts** an order. | - |
| `WaitForGroup( group )` | 83 | Waits until no member is executing an order. | - |
| `WaitForObject( obj )` | 48 | Waits until an object animation ends. | - |
| `WaitForUnitRoute( unit, bBreakIfDead )` | 100 | Takes the unit's current route and waits until it is finished; with `bBreakIfDead` also stops when the unit cannot fight. Returns after 2 ticks for a unit with no route (any human-player unit). | - |
| `WaitForGroupRoute( group, bBreakIfDead )` | 113 | Same for every member. | - |
| `WaitForUnitWaypoint( unit, wp, dist )` | 266 | Polls every 2 ticks until the unit is within `dist` tiles (default 0.1) of the waypoint's exact position. Does not end if the unit never gets that close. | - |
| `WaitForPassCalc()` | 56 | Meant to wait for the AI pass map to be rebuilt after the level changed. | `SlowSyncAIMap`, `PassCalcerIsActive`: just sleeps 2 ticks. |
| `SleepForTurn( n )` | 65 | Waits `n` turns (default 1), polling `GetTurn` every 10 ticks. Does not end inside a sequence, where the turn counter is frozen. | - |

### 4.2 Game start and sequences (`Common.l`)

| Helper | Line | What it does | No-op dep. |
|---|---|---|---|
| `BeginSequence( bBlockInput )` | 252 | `c_BeginSequence`. Does not block. | - |
| `DelayGameStartEx()` | 485 | Sets `G_DelayGameStartFlag`, which makes `WaitForUI` return at once. | `c_DelayGameStartEx`: the game start is not held. |
| `DelayGameStart()` | 490 | `DelayGameStartEx()` then `BeginSequence( true )`. In this build: starts a sequence and disables `WaitForUI`. | as above |
| `StartGameEx()` | 495 | Clears the flag, sleeps 1 tick. | `c_StartGameEx` |
| `StartGameWithSequence()` | 502 | `StartGameEx()`; leaves a running sequence open. | as above |
| `StartGame()` | 506 | `StartGameEx()` then `EndSequence()`. | as above |
| `CameraSet( cam )` | 35 | `WaitForUI( CameraMove( cam, 0 ) )`: jump the camera and wait. | - |
| `DialogPlayWithSequence( code, bHeroOnLeft )` | 538 | `BeginSequence()`, `DialogPlay`, `EndSequence()` without waiting for the dialogue. | - |

### 4.3 Party and deployment (`Common.l`)

| Helper | Line | What it does | No-op dep. |
|---|---|---|---|
| `GetParty()` | 189 | `PlayerGetUnits( 0 )`: a new group with the human player's units. | - |
| `DividedDeploy( variant )` | 195 | Teleports the hero to waypoint `UnitHero<variant>` and the other party members to `Unit1<variant>`, `Unit2<variant>`, ... in party order (`variant` defaults to ""). Units that cannot fight are skipped. Prints a message and does nothing if there is no hero. | `UnitStop` via `GroupStop`: harmless. |
| `DividedDeployDemo( variant )` | 220 | Same without the hero special case: every member goes to `Unit<i><variant>`. | as above |
| `PartyMoveToDeploy( variant )` | 351 | Like `DividedDeploy` but the party walks there (`UnitMoveToWaypoint`). | as above |
| `OnExit()` | 377 | Default leave-zone handler. | `ShowLeaveZoneDialog`: does nothing. Not called by this engine anyway. |
| `OnPlayerLose( bScenarioLose )` | 524 | Default defeat handler. | `ShowLoseDialog`: does nothing. Not called by this engine. |
| `OnRealExit()` | 533 | `ExitToChapter()`. Not called by this engine. | - |

### 4.4 Unit and group utilities (`Common.l`)

Truth results are `TRUE` (1) / `FALSE` (nil).

| Helper | Line | What it does | No-op dep. |
|---|---|---|---|
| `UnitCanFight( unit )` | 19 | Valid handle and neither dead nor unconscious. Safe with nil. | - |
| `UnitAIMode( unit, bAI )` | 237 | `UnitCheat( unit, CHEAT_NOAI, not bAI )`, then sleeps 2 ticks. `UnitAIMode( u, FALSE )` takes a unit away from the AI so scripted orders stick. | - |
| `GroupAIMode( group, bAI )` | 243 | `UnitAIMode` for each member (2 ticks each). | - |
| `GroupCanFight( group )` | 302 | TRUE if any member can fight. | - |
| `GroupCanFightSize( group )` | 396 | Number of members that can fight. | - |
| `GroupIsDead( group )` | 178 | TRUE if every member is dead (unconscious does not count). | - |
| `GroupIsCross( g1, g2 )` | 141 | TRUE if the groups share a unit. | - |
| `UnitCanSee( unit, group )` | 150 | TRUE if the unit sees any member. | - |
| `UnitCanSeeUnit( u1, u2 )` | 156 | TRUE if `u1` sees `u2`. Builds a group from `UnitGetName( u2 )`, so `u2` must be a named unit (see `CreateGroup`). `UnitIsSeeUnit` avoids that. | - |
| `GroupCanSee( g1, g2 )` | 163 | TRUE if any member of `g1` sees any member of `g2`. | - |
| `GroupCanSeeUnit( group, unit )` | 417 | TRUE if any member sees the unit. | - |
| `GroupSetDirection( group, dir )` | 277 | `UnitSetDirection` for each member. | - |
| `GroupSetPose( group, pose )` | 332 | `UnitSetPose` for each member, then `WaitForGroup`. Blocks. | - |
| `GroupSetWishPose( group, pose )` | 342 | `UnitSetWishPose` for each member. | - |
| `GroupRoaming( group, wp, radius )` | 314 | `UnitRoaming` for each member. | - |
| `GroupCancelAction( group )` | 324 | `UnitCancelAction` for each member. | - |
| `GroupActivateWeapon( group, bReady )` | 463 | `UnitActivateWeapon` for each valid member. | - |
| `GroupRemove( group )` | 257 | `UnitRemove` for each member. | - |
| `GroupDeleteUnit( group, unit )` | 293 | Removes the unit from the group if it is a member. | - |
| `GetPosition( x )` | 287 | `GetPos( x )`. | - |
| `outGroup( group )` | 169 | Prints the group size and each member. | - |
| `GroupStop( group )` | 7 | Meant to stop every member. | `UnitStop`: does nothing. |
| `GroupKeepMoving( group )` | 428 | | `UnitKeepMoving`: does nothing. |
| `GroupSwarmToWaypoint( group, wp )` | 474 | | `UnitSetRetreatLogic`: does nothing. |
| `GroupInArea( group, wp1, wp2 )` | 383 | Meant: all fighting members inside the rectangle. | `UnitInArea`: FALSE whenever any member can fight. |
| `GroupIsWearingPK( group )` | 408 | | `UnitIsWearingPK`: always FALSE. |
| `UnitIsHearGroup( unit, group )` | 440 | | `UnitIsHearUnit`: always FALSE. |
| `GroupGiveXP( group, xp )` | 512 | | `UnitGiveXP`: does nothing. |
| `GiveGoodWeapon( unit )` | 452 | Meant to hand out a weapon and ammunition. | `UnitCreateItem`, `CreateAndActivateItem`: only waits for the unit. |

### 4.5 Triggers (`TriggersManager.l`)

| Helper | Line | What it does |
|---|---|---|
| `Trigger( condition, handler, cycled, latency )` | 4 | Registers a trigger. The manager calls `condition()` every `latency` ticks (default 20, rounded up to a multiple of 10); when it returns non-nil, `handler` is started as a new thread. With `cycled` nil the trigger is removed after firing once. `condition` runs on the manager's thread: it must not block, and a script error inside it kills the manager and with it every trigger. |
| `TriggersManager()` | 18 | The polling loop (every 10 ticks). Already running in every world; do not call it. |

Example: `Trigger( function() return GroupIsDead( raiders ) end, OnRaidersDead )`.

---

## 5. Constants

From `Constants.l`. All are plain global variables, so a script can overwrite them by accident.

| Family | Values | Used by |
|---|---|---|
| Direction | `DIR_RIGHT` 0, `DIR_UPRIGHT` 1, `DIR_UP` 2, `DIR_UPLEFT` 3, `DIR_LEFT` 4, `DIR_DOWNLEFT` 5, `DIR_DOWN` 6, `DIR_DOWNRIGHT` 7 | `UnitSetDirection` |
| Pose | `POSE_CRAWL` 0, `POSE_CROUCH` 1, `POSE_WALK` 2, `POSE_RUN` 3 | `UnitSetPose`, `UnitSetWishPose` |
| Hit location | `HL_ANY` -1, `HL_BODY` 0, `HL_HEAD` 1, `HL_RHAND` 2, `HL_LHAND` 3, `HL_RLEG` 4, `HL_LLEG` 5 | `UnitShoot` |
| Tile hit location | `THL_LOWER` 0, `THL_MIDDLE` 1, `THL_UPPER` 3 | Nothing in this build. The engine's value for upper is 2 (`Main/aiPosition.h:191`). |
| Shoot mode | `SM_SNAP` 0, `SM_AIMED` 1, `SM_CAREFUL` 2, `SM_SHORTBURST` 3, `SM_LONGBURST` 4, `SM_SNIPE` 5 | `UnitSetShootMode` |
| Time of day | `ANYTIME` 0, `NIGHT` 5, `DAY` 6 | `SetTimeOfDay` (no-op) |
| Cheat | `CHEAT_GODMODE` 1, `CHEAT_SEEALL` 2, `CHEAT_TELEPORT` 4, `CHEAT_AP` 8, `CHEAT_SCRIPTSEQUENCE` 16, `CHEAT_NOAI` 32, `CHEAT_TOHIT` 64 | `UnitCheat`, `GroupCheat` |
| Diplomacy | `DS_ENEMY` 0, `DS_NEUTRAL` 1, `DS_ALLY` 2 | the diplomacy functions |
| UI action | `AT_CAMERA` 0, `AT_DIALOG` 1 | `WaitForUI`, `IsUIActionIDPresent` |
| Truth | `TRUE` 1, `true` 1, `FALSE` nil, `false` nil | everywhere |
| Clue action | `ACTION_TAKE` 1, `ACTION_DESTROY` nil | `ScenarioGiveClue` second argument |
| Difficulty | `DIFFICULTY_EASY` 1, `DIFFICULTY_NORMAL` 2, `DIFFICULTY_HARD` 3 | `Difficulty` (record IDs, **unverified** against the table) |
| Explosion | `EXPLOSION_CONC` 29, `EXPLOSION_FRAG` 30 | `Explosion` (grenade record IDs) |
| Skill and stat | `ST_MELEE` 0, `ST_SHOOTING` 1, `ST_THROWING` 2, `ST_BURST` 3, `ST_SNIPE` 4, `ST_STEALTH` 5, `ST_SPOT` 6, `ST_MEDICINE` 7, `ST_ENGINEERING` 8, `ST_VP` 9, `ST_AP` 10, `ST_IC` 11, `ST_INTERRUPT` 12, `ST_LEVEL` 13, `ST_STR` 14, `ST_DEX` 15, `ST_INT` 16 | the skill functions |
| Scenario | `SCEN_ALLIES` 1, `SCEN_AXIS` 2 | `GetScenarioNumber` (no-op) |
| Weapon kind | `WP_GRENADE` 0, `WP_MELEE` 1 | `UnitIsWeaponInHand` (no-op) |

The direction, pose, hit location, shoot mode, cheat, diplomacy and skill values match the engine enums (`Main/aiPosition.h:168-190`, `DBFormat/DataRPG.h:46,321`, `Main/rpgCheatConstants.h`, `DBFormat/DataMap.h:274`).

What the cheat bits do, by code: `GODMODE` takes no damage (`Main/RPGGame.cpp:350`); `SEEALL` sees every unit (`Main/wUnitServer.cpp:851,966`); `AP` orders cost nothing (`Main/RPGUnitMission.cpp:444`); `SCRIPTSEQUENCE` orders cost nothing, the unit does not react to enemies it sees (`Main/aiCommander.cpp:222`) and makes no acknowledgements (`Main/wAckBase.cpp:274`); set on everyone by `BeginSequence`; `NOAI` the AI assigns the unit no new control below script level (`Main/aiUnit.cpp:185`); `TOHIT` every shot rolls a hit (`Main/RPGGame.cpp:681`); `TELEPORT` has no live use site (**unverified**).

`Common.l` adds `N_WAIT_TIME_TO_SLEEP` 2 and `N_WAIT_TIME_TO_SLEEP1` 1 (poll intervals in ticks) and the flag `G_DelayGameStartFlag`.

---

## 6. Lua 4.0 notes

**The language.** Lua 4.0 with a modified VM. There is **no standard library**: `tostring`, `tonumber`, `type`, `getn`, `tinsert`, `format`, `strsub`, `print`, `dofile`, `call` and the rest are not registered (`Script/` has no library sources), and calling one is a silent no-op through the backstop in section 3. What exists is the core language (`..`, arithmetic, tables, `for i = a, b do`, `for k, v in t do`, `while`, closures with `%upvalue`) plus the functions in this note. There are no booleans: nil is false, everything else is true, and `true` / `false` are ordinary globals set in `Constants.l`. `not x` yields 1 or nil.

**Threads.** One Lua state per world; all threads share the globals. A thread is created for every chunk (each autoload file, the mission script, each `PlaceTemplate` script, a console `@` line), for every `StartThread`, and for every engine callback. A chunk does not run when it is loaded: it is queued and starts on the next world tick (`lua_dobuffer`, `Script/ldo.cpp:369`), after the autoload files, so the helpers and constants are defined by then.

Threads are cooperative. Once per world tick `lua_executeThreads` (`Script/lapi.cpp:460`, called from `CWorld::Segment`, `Main/wMain.cpp:1867`) runs each thread in creation order until it calls `Sleep` or returns. Nothing preempts a thread: **a loop without `Sleep` freezes the game.** A thread started with `StartThread` gets its first run later in the same tick.

**`Sleep( n )`.** `n` counts world ticks, not milliseconds (`Script/lapi.cpp:437`). A tick is one `CWorld::Segment`, which advances game time by 50 ms (`DW_SEGMENT_TIME`, `Main/wMain.cpp:82,1905`), so `Sleep( 20 )` is one second of game time and nothing passes while the world is not updated. `docs/content-pipeline.md` quotes about 70 ms per tick measured on the wall clock; the two figures have not been reconciled. `Sleep()` is `Sleep( 1 )`. The value is truncated to an integer, and **`Sleep( 0 )`, a negative value or a fraction below 1 does not yield at all**. `Sleep` is ignored inside the error hook and tag methods.

**Errors.** A runtime error (bad argument to an engine function, arithmetic on nil, calling a non-function that is not nil) prints `Script error: <message>` in red to the in-game console, marks the thread as failed and removes it at the end of its run (`Script/ldo.cpp:440-456`, `Script/lapi.cpp:483`). Other threads and the mission carry on; functions defined before the error stay defined. A syntax error means the whole chunk never runs, with only the console line to show for it; the mission still loads (`Main/wMain.cpp:1412`). Console commands (`Main/A5Script.cpp:38,150,259`): `scripterror` prints the last error with a stack trace, `script_show all` or `script_show <global>` dumps script state, `script_run <file or script ID>` runs a script, and a line starting with `@` is executed as Lua, for example `@out( GetTurn() )`.

**Handles.** Engine objects reach Lua as tagged userdata (`Main/scriptPtr.cpp`, `Script/lobject.h:153`). A **Ptr** handle (tag 6) is a weak reference: when the engine destroys the object the handle goes stale, `IsValid` returns nil and functions treat it as null. An **ObjPtr** handle (tag 7) is an owning reference that keeps the object alive while any script variable holds it. Lookups of things that live in the world return Ptr (`GetUnit`, `GetGroup`, `GetObject`, `GetItem`, `GetHero`, `GroupGetUnit`, `CreateUnit`, `CreateObject`, `UnitGetRoute`); things made for the script return ObjPtr (`CreateGroup`, `PlayerGetUnits`, `GroupAddGroup`, `GroupGetCross`, `UnitGetVisible`, `GroupGetVisible`, `CreateRoute`, `GetPos`, `GetWaypointPos`, `GetCamera`). `Ptr( h )` and `ObjPtr( h )` convert.

- A **unit** handle refers to the unit in the world (`NWorld::CUnitServer`). It stays valid after the unit dies (the body remains) and goes stale when the unit is removed.
- A **group** handle refers to an ordered unit set (`NWorld::CUnitGroup`, `Main/wUnitGroup.h`). Groups placed in the map have integer IDs for `GetGroup`; script-made groups have ID 0, except the ones from `UnitGetVisible` / `GroupGetVisible`, which are registered in the world under a fresh ID. `PlayerGetUnits`, `GroupGetCross` and the others return a snapshot: it does not follow later changes.
- The script state, with all threads, globals and handles, is saved and loaded with the world (`Script/lstate.cpp:137`).

**Names.**

- Units, map objects and ground items share one name table (`Main/wMain.cpp:374,526,550,1240,2042`). Names are trimmed and upper-cased, so lookups are case-insensitive and `UnitGetName` returns upper case. A unit's name is the one given in the map or to `CreateUnit`; if that is empty, its RPGPers `UserName`. A later registration of the same name replaces the earlier one. `GetUnit` on a name that belongs to an object returns nil.
- Waypoints have their own table, lower-cased (`Main/wMain.cpp:1056,2393`). Of two waypoints with the same name the first wins and a warning is printed. For unit movement a waypoint means the nearest pathable tile (`Main/aiRoute.cpp:33`); for objects and `GetWaypointPos` it is the exact map position. An unknown name prints `Script warning: waypoint "x" not found` and the function does nothing.
- Players are numbered by scenario player ID: 0 is the human player (`Main/wMain.cpp:1481`), AI sides take the IDs given to their units in the map.
- Dialogues are found by `Code`, clues and zones by `SmallDescription`, cameras, templates, animations, perks, items and grenades by record ID.
