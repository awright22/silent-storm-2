# Dialogue and text in the Jan03 engine build

Reference for authoring mission text (briefings, in-mission dialogue, objective messages) for Silent Storm 2.

**Status, 2026-10-02.** Everything here comes from reading the engine source, querying the retail `game.db.retail`, parsing `res/Fonts.res`, and reading earlier run logs in `build/shots`. **No dialogue was played at runtime for this note**: no existing mission script on maps 50001 or 167 calls a text function, and test scripts were out of scope. Statements about on-screen behaviour are therefore "by code" unless a log is cited. Anything inferred beyond the code is marked **unverified**. A test to confirm the main path is in [Things to try](#things-to-try).

Path conventions:

- `Main/…`, `DBFormat/…`, `Script/…`, `MiscDll/…` are under `D:\Code\Silent-Storm\Soft\Andy\Jan03\a5dll\`.
- `port/…` is under `D:\Code\Silent-Storm\`.
- Row IDs are from `build/run/game.db.retail`.
- The staged `build/run/SS2.exe` was built 2026-10-01 23:55. The dialogue sources were last changed in commit `565a016e3` (23:42), so the exe matches what is described here. Scenario-goal work in the engine tree (2026-10-02, uncommitted) is **not** in the staged exe.

## Summary: what a script can put on screen

| Channel | Script call | Works in this build? | Data needed |
|---|---|---|---|
| Full-screen dialogue (letterbox, speakers, paged text) | `DialogPlay("code")` | Yes, by code. Retail UI container 364 is complete. | Dialogs, DialogSeqs, AckInfos, Strings |
| One-line bark with face | `DialogPlayAsAcks("code")`, `UnitSayAck(unit, n)` | Logic runs, but **nothing is drawn**: retail container 123 has no `ack` control. Data fix possible (unverified). | As above, plus one UIControls row; `UnitSayAck` also needs Acks and AckSeqs |
| Clue / journal page (scrolling paper) | `ClueShow("name")` | Only inside a scenario. A mission started with `map <id>` has none, so it does nothing. | ScenarioClues, ScenarioObjectives, Strings, a running scenario |
| Hint window | `ShowHint(n)` | **No.** Logged no-op from `port/luacompat`. | — |
| Objectives | `ScenarioAddGoal` etc. | **No** in the staged exe (no-op stubs). No objectives UI exists in Jan03. | — |
| On-screen message line (8 s, top of view) | none | The panel exists but no script function feeds it. | Engine change |
| Message box, tutorial window, floating text | none | **No.** Not in Jan03. | Engine change |
| Console | `out(...)` | Yes, but only visible with the console open (`` ` ``) and in the run log. | — |
| Speech audio | via AckInfos.SoundID | **No.** FMOD is stubbed in the port. | Engine change |

For a mission launched with `map`, **`DialogPlay` is the only working way to show authored text to the player.**

---

## 1. Dialogue: `DialogPlay`

### Answer

`DialogPlay("code")` looks up a Dialogs row by `Code`, collects its DialogSeqs rows, and opens a modal letterbox screen. Each line is an AckInfos row: who speaks (`WhoID`, an RPGPers ID), what is shown (`StringID` → Strings), and optional voice and head animation. The player pages through with Next (SPACE) / Back / Exit; ESC closes the whole dialogue. Nothing is timed. A line with no sound still shows its text and stays until the player advances.

### Tables and columns

Only the columns marked **read** are imported by the engine. The rest are editor leftovers and can be left empty.

**Dialogs** (0x61), one row per dialogue.

| Column | Read? | Meaning |
|---|---|---|
| `ID` | read | Dialogue ID, referenced by DialogSeqs.DialogID |
| `Code` | read | Name passed to `DialogPlay`. Compared case-insensitively; the first match in table order wins, so codes must be unique |
| `Description`, `SrcName`, `UserName` | no | Authoring notes (retail: path of the source .xls) |

**DialogSeqs** (0x67), one row per line of a dialogue.

| Column | Read? | Meaning |
|---|---|---|
| `ID` | read | **Defines line order**: lines are sorted by this ID, ascending |
| `DialogID` | read | Owning Dialogs.ID |
| `AckInfoID` | read | The line (AckInfos.ID). Must resolve; see hazards |
| `AckInfoOrder` | imported, never used | 0 in all 470 retail rows |

**AckInfos** (0x36), one row per spoken line. Shared by dialogues and combat barks.

| Column | Read? | Meaning |
|---|---|---|
| `WhoID` | read | Speaker: an RPGPers ID, or the hero placeholder (section 5) |
| `StringID` | read | Strings.ID of the text |
| `SoundID`, `SoundID1`…`SoundID5` | read | Voice file per voice slot 0–5 (Sounds.ID). 0 = none |
| `HeadSequenceID`, `HeadSequenceID1`…`5` | read | Lip-sync sequence per voice slot (HeadSeqs.ID). 0 = none |
| `UserName`, `IntonationID`, `FaceExpression`, `FemaleStringID` | no | Not read by Jan03. A female hero gets the same `StringID` text |

The voice slot is the speaking unit's RPGPers.`Voice` (0–5). Single-voice NPCs use slot 0 only; hero lines in retail carry all six.

**DialogPers** (0x68): only `PersID` is read, and only through Sides.`HeroDialogPersID`. It is not consulted when a line is played. See section 5.

**AckSeqs** (0x37) and **Acks** (0x38) are not used by `DialogPlay`. They drive automatic barks and `UnitSayAck` (section 2).

**Sounds** (0x25) and **HeadSeqs** (0x46) are only needed for voiced lines.

Evidence:

- Import of every table above: `DBFormat/DataAck.cpp:12-29` (AckInfos), `:42-48` (AckSeqs), `:61-70` (Acks), `:94-97` (Dialogs), `:101-106` (DialogSeqs), `:110-113` (DialogPers).
- Lookup by code: `DBFormat/DataAck.cpp:116-127` (`stricmp`, returns first match).
- Ordering by record ID, not `AckInfoOrder`: `Main/wDialog.cpp:18-21`, `:40`.
- Voice slot selection: `Main/iMissionDlgUI.cpp:326` (direct index, no fallback to slot 0 in the dialogue screen).

### End-to-end flow

1. `DialogPlay` finds the dialogue. Unknown code: returns nothing, so `WaitForUI(DialogPlay(...))` falls straight through. Known code: marks a dialogue action as started, queues the UI command, returns the action type `1`. `Main/scriptDialog.cpp:14-24`.
2. `MakeDialogData` builds the line list. For each line it resolves the speaker to a unit (section 5) and creates a phrase. `Main/wDialog.cpp:78-122`.
3. The mission UI pops the command and opens `CMissionDlgUI` on UI container **364**. `Main/iMission.cpp:1838-1848`.
4. Stages: 1 s fade to letterbox, 1 s speaker slide-in, then the first page. `Main/iMissionDlgUI.cpp:26-28`, `:105-159`. The normal mission panels are hidden for the duration and restored after (`:113-114`, `:196`).
5. Each page: text is set, the active speaker is lit (ambient light 7) and the others dimmed (light 113), the sound is played if there is one, the head sequence is started if there is one. `Main/iMissionDlgUI.cpp:275-311`.
6. Input: `next` (SPACE) advances, the Back button goes back, `cancel` (ESC) ends the dialogue at once. All other input is swallowed. `Main/iMissionDlgUI.cpp:208-232`; binds in `build/run/cfg/input.cfg:5`, `:104`. No key is bound to `back`.
7. On close: 1 s slide-out, 1 s fade, then the dialogue action is marked finished. `Main/iMissionDlgUI.cpp:160-199`, `:413-417`.

Script side:

- `WaitForUI(DialogPlay("code"))` blocks the calling script thread until step 7. `WaitForUI` polls `IsUIActionIDPresent`, which the port maps to Jan03's per-type counter. `build/run/scripts/Common.l:25-32`, `Main/ScriptFunctions.cpp:62`, `Main/scriptSequence.cpp:71-80`, `Main/wMain.cpp:2380-2391`.
- The engine calls two global Lua functions if they exist: `OnDialogPhrase(code, n)` each time a page is shown (`n` is the 0-based page index), and `OnDialogFinished(code)` at the end. `Main/iMissionDlgUI.cpp:310`, `:416`. They are global, so one handler serves all dialogues; branch on `code`.
- Extra arguments are ignored: Gold's `DialogPlay(code, heroOnLeft)` is accepted. `Script/Script.cpp:118` (`CheckArgs`).
- `UnitSetDialog(unit, "code")` attaches a dialogue to an NPC. When the hero is ordered to talk to that unit the engine calls global `OnTalk(hero, target)` and then plays it. `Main/scriptUnit.cpp:455-468`, `Main/wUnitAttackExec.cpp:2576-2590`. Not exercised here; **unverified**.

### How the text is found and laid out

- Text = `GetDBString(11209) + Strings[AckInfos.StringID]`. String 11209 is the format prefix `<font face=Impact size=24pt><color=FFB4997C><center>`. `Main/iMissionDlgUI.cpp:287`, `:329`.
- The text box is control `dialogtext` in container 364: (302,623)–(720,699), which is 418×76 in the 1024×768 UI space. That is **three lines of Impact 24pt**.
- Measured with the retail Impact metrics, average English text runs about 52 characters per line, so about **150 characters per page**. Of 399 resolvable retail dialogue lines, 26 exceed that; median length is 53, 90th percentile 129, maximum 279.
- Longer lines are split automatically into extra pages. `Main/iMissionDlgUI.cpp:313-405`. The split is by character count and can fall mid-word, and the remainder is measured without the Impact prefix, so a later page can overflow. To stay safe, **keep each line under about 140 characters** and split long speeches into several lines yourself. (Split behaviour **unverified** at runtime.)
- A line's sound is replayed on every page of that line, and again when the player goes Back.
- Markup rules are in section 4. In dialogue text a newline character renders as a space; use `<br>`.

### Speakers on screen

- There are four speaker slots: `unitview1` (left, camera 62), `unitview2` (right, camera 63), `unitview3` (left, inset), `unitview4` (right, inset). `Main/iMissionDlgUI.cpp:255-259`.
- Slots are filled in order of first appearance in the dialogue. The first speaker is on the left. The code that moves the hero to the front never fires, because it compares pointers of two unrelated classes. `Main/wDialog.cpp:111-117`.
- A fifth distinct speaker gets no slot; the text still shows. Retail never uses more than three.
- Each slot is a live 3D render of the unit, not a 2D portrait. `Main/iCommonUI.cpp:623` (`CUnitView::SetUnit` with a camera).
- **No speaker name is shown anywhere** in the Jan03 dialogue screen. The only cue is which figure is lit.

### Worked example: `GFirstG1` (script 95, line 410)

Script 95 (`GFirst`, map variant 6213) calls `WaitForUI( DialogPlay("GFirstG1") )` after a camera move.

| Step | Row |
|---|---|
| Dialogs | ID **217**, Code `GFirstG1` |
| DialogSeqs | IDs **1264–1270, 1469, 1470** (nine lines, played in that ID order), all `DialogID=217`, `AckInfoOrder=0` |
| AckInfos | **10065–10071, 10602, 10603**, alternating `WhoID=160` and `WhoID=165` |
| Speaker 160 | RPGPers 160 `CivilMale`, DisplayName string 18988 "Civilian", Voice 0. One sound per line |
| Speaker 165 | RPGPers 165 `AxisEngineer` = the Axis hero placeholder: Sides 1 `HeroDialogPersID=5` → DialogPers 5 `nmdHeroAxis` → `PersID=165`. Six sounds per line, one per hero voice |
| Strings | **18826–18832, 20160, 20162** |

First two lines in full:

| DialogSeqs | AckInfos | WhoID | StringID → text | SoundID (slot 0) | HeadSequenceID |
|---|---|---|---|---|---|
| 1264 | 10065 | 160 | 18826 "Did you see it? Did you see? " | 14556 | 6664 |
| 1265 | 10066 | 165 | 18827 "I have seen a lot. What are you talking about? " | 14557 (slots 1–5: 14558–14562) | 6495 (6496–6500) |

On screen: the civilian is the first speaker, so he takes the left slot; the hero takes the right. Line 8 (string 20160, 93 characters) fits on one page.

### Does a line without sound still show its text?

Yes, by code. The text is set unconditionally; the sound and head sequence are each guarded by a validity check. `Main/iMissionDlgUI.cpp:287`, `:298-301`. The page stays until the player presses Next or Exit.

No retail dialogue line lacks a sound (0 of 470), so this path has no retail precedent. It is moot in the current port anyway: FMOD is a stub and nothing is audible (`port/README.md:34`, `port/ROADMAP.md:36`).

### Hazards

- **DialogSeqs row pointing at a missing AckInfos row.** The null pointer is dereferenced at `Main/wDialog.cpp:98`. 71 retail DialogSeqs rows are like this, across 19 dialogues (for example `GBaseG1a`, `RTLabE1`, `EVipG1`). Do not reuse those dialogues, and never leave a dangling `AckInfoID`. (Crash **unverified**; by code.)
- **`WhoID` that is not a valid RPGPers ID.** When no live unit matches, a temporary unit is created from `NDb::GetPers(id)` with no null check. `Main/wDialog.cpp:63-73`.
- **Dialogue with no playable lines** (for example hero-only lines when no hero exists). The letterbox opens with no text and no buttons; only ESC closes it. `Main/iMissionDlgUI.cpp:275-281`.
- **ESC during a `BeginSequence` movie.** The engine then drops dialogue commands (`Main/iMission.cpp:1840-1844`) without marking the action finished, so a thread blocked in `WaitForUI(DialogPlay(...))` would never resume. **Unverified.**

### Minimal rows for a two-line, text-only dialogue

2 × Strings, 2 × AckInfos, 1 × Dialogs, 2 × DialogSeqs. Nothing else. Exact values are in the [recipe](#recipe-add-a-text-only-dialogue).

---

## 2. Other ways to show text

### `DialogPlayAsAcks("code")` and acks in general

**Answer.** The call exists and runs, but in the current data nothing appears. It is meant to show **only the first line** of the dialogue as a small panel (speaker's head plus text) for a fixed **3 seconds**, without interrupting play.

- Only the first phrase is used: `Main/iMission.cpp:1850-1851` (`phrases.front()`). Every dialogue retail plays this way has exactly one line. An empty dialogue would call `front()` on an empty vector.
- Display time is a constant: `N_ASK_TTL = 3000` ms, `Main/iDesktopWindow.cpp:16`, `:20-24`. Clicking the panel dismisses it. It does not depend on text length or sound length.
- The panel is `CAckIcon`, built from control `ack` in container 123 (`missionUI`). `Main/iMissionUI.cpp:495`, `:95-114`. Retail container 123 has no such control, so the engine fabricates a zero-size window. Run-log evidence, `build/shots/base167.log:407`, `:467`, `:469`: "control ack in container missionUI not found", "control face in container ack not found", "control text in container ack not found".
- During a `BeginSequence` movie an ack plays its sound only; during a full dialogue it does nothing. `Main/iMissionMovieUI.cpp:146-155`.
- A new ack replaces the current one unless the current one has higher priority. Dialogue acks have priority 1; all 4,693 retail AckSeqs have priority 0. `Main/iDesktopWindow.cpp:58-66`, `Main/wDialog.cpp:119`.

**Probable data-only fix (unverified).** Retail still ships the panel layout as container **50** "Ack icon" (512×112: `face` window, `text` control, background image). Add one UIControls row:

| Column | Value |
|---|---|
| `ID` | new |
| `UIContainerID` | 123 |
| `IDText` | `ack` |
| `Type` | 13 (window) |
| `NestedUIContainerID` | 50 |
| `Left, Top, Right, Bottom` | 256, 470, 768, 582 (any 512×112 rect above the unit panel, which starts at y=596) |
| `Visible` | 0 |

Ack text uses the other text engine (section 4): default font System 22pt white, newlines become line breaks, and the box is 368×86.

### `UnitSayAck(unit, conditionID)`

**Answer.** Implemented. It queues every Acks row with `WhoID` = the unit's RPGPers ID and `ConditionID` = the number; one is then picked by weighted roulette and shown as an ack. It has the same invisibility problem as above.

- `Main/scriptUnit.cpp:79-84`, `Main/wAckBase.cpp:235-248` (queue), `:202-233` (roulette: if the `Probability` values sum to less than 100, the remainder is the chance that nothing is said), `Main/wMain.cpp:1746-1769` (dispatch; skipped during forced real-time).
- Data: Acks (`WhoID`, `ConditionID`, `AckSeqID`, `Probability`), AckSeqs (`AckID0`…`AckID2`, `Priority`; only `AckID0` is ever shown), AckInfos, Strings.
- Retail scripts use condition 110 for scripted hero remarks. Conditions 68–118 are also triggered by the engine itself.
- For a scripted line, `DialogPlayAsAcks` with a one-line dialogue needs fewer rows and has no roulette.

### `ClueShow("name")`

**Answer.** Implemented, and it is the nicest long-text view in the build: a modal paper page with scrolling marked-up text (container 322 / 321). It only works inside a scenario, so it does nothing under `map`.

- `Main/scriptScenario.cpp:64-73`, `Main/iShowClue.cpp:52-64`, `:173`.
- The clue is found by ScenarioClues.`SmallDescription` (case-insensitive): `Main/scFlowChart.cpp:113-125`. With no scenario the lookup returns null: `Main/scScenarioTracker.cpp:96-101`. `map` creates the game with scenario −1: `Main/iMission.cpp:2208`, `Main/RPGGlobal.h:151`, `Main/scScenarioTracker.cpp:612-618`.
- The text shown is ScenarioObjectives.`Description` of a *finished* objective linked to the clue, not the clue's own description; otherwise "[ERROR]Description not set". `Main/scScenarioTracker.cpp:58-70`.
- Using it for SS2 means building a whole scenario graph (it must contain zones named BASE and FFIGHT, `Main/scFlowChart.cpp:29-35`) and launching through `zone`/`global` instead of `map`. Not practical yet.

### Hints: `ShowHint(n)`, `AddHints`

**Answer.** Not implemented. Both are in the port's no-op list; the call logs once and returns nil, so `WaitForUI(ShowHint(n))` returns immediately.

- `port/luacompat/lua_compat.cpp:42`, `:52` (names), `:84-88` (stub returns nil), `:116-133`.
- Jan03 registers no such function: `Main/ScriptFunctions.cpp:32-183`.
- Retail data for Gold's hint window exists but has no engine class: table 0x6D (72 rows: `ID, UserName, Sequence, StringID, TitleID`). `scripts/Hint.l` only prints "Hints were loaded".

### Objectives

**Answer.** Not available in the staged exe, and Jan03 has no objectives screen at all.

- `ScenarioAddGoal`, `ScenarioSetGoalComplete`, `ScenarioSetTaskComplete` are no-op stubs in the staged exe. Real implementations appeared in the engine working tree on 2026-10-02 (`Main/scriptScenarioGoal.cpp`, `Main/ScriptFunctions.cpp:167-169`, tables 0x6E/0x6F), uncommitted and not yet built into `SS2.exe`. They track state only.
- The top-bar "Objectives" button (UIControls 2130) is drawn from retail data but no Jan03 code handles it. "Journal" opens the clue list, which needs a scenario.

### On-screen message line (log panel)

**Answer.** The mission UI has a message area that shows lines for 8 seconds in Impact 20pt at the top-left of the view, with markup. It only shows the engine's own `csGame` messages ("Not enough AP", "Path not found"). No script function writes to it. `out()` goes to a different stream.

- Panel: `Main/iMissionUI.cpp:493`, `:586-593`; `Main/iLogPanel.cpp:17` (8000 ms), `:74` (font prefix).
- Writers: `Main/iGameStates.cpp:102-135`.
- `out()` writes to `csScript`: `Main/scriptCommon.cpp:101-143`.
- This is the cheapest route to objective toasts: one new Lua function that does `csGame << text << endl`. Needs an engine change.

### Message box, tutorial window, floating text

**Answer.** None exist for scripts. The world-to-UI command list is closed: camera move, sequence begin/end, dialogue, ack, floor, chapter exit, template load, store, team management, clue. `Main/wUICommands.h:47-211`. `UI_MESSAGEBOX` is only an enum value (`DBFormat/DataInterface.h:29`). Floating text exists only for damage numbers and item labels (`Main/iMissionUI.cpp:337-390`, `:146-175`). Gold's `CreateWindow`/`GetWindow`/`windowSetProperty` are no-op stubs.

### Console

**Answer.** Works; it is a developer tool, not a player channel.

- Toggle with `` ` `` (`input.cfg:13`). Lines are drawn with markup, so `out("<color=red>text")` is red. `Main/Console.cpp:110`.
- `out(...)` also reaches the debugger output, which is what `tools/run.py` logs.
- A console line starting with `@` runs as Lua in the current mission's script state, for example `@DialogPlay("GFirstG1")`. `Main/A5Script.cpp:150-170`. Useful for trying a dialogue by hand.
- Other commands: `script_run <id|file>`, `script_show all`, `scripterror`. `Main/A5Script.cpp:258-263`, `:38-60`.

---

## 3. Strings and localisation

### Answer

All player-visible text is a row in **Strings** (0x2D): `ID`, `String` (the text, with markup), plus `UserName` and `Comment` which the engine ignores. Other tables point to it by ID. UI code fetches by number with `GetDBString(id)`, which returns an empty string for a missing ID. There is no script function to read or display a string.

**TranslatedStrings is dead.** One `game.db` holds one language; to localise, ship different Strings rows.

### Details

- `GetDBString`: `Main/UIInterface.cpp:22-40`. Missing ID or −1 gives `L""`, never a crash.
- Import: `DBFormat/DataFormat.cpp:174-184`. Carriage returns are stripped; `\n` stays.
- **Encoding.** Cells are UTF-16LE in `game.db` and `wstring` in the engine, with no conversion (`port/dbcompat/FORMAT_SPEC.md`, section 5.4). `ssdb` takes ordinary Python `str`. What can actually be *drawn* is limited by the fonts (section 4).
- **Length.** No limit in the format or the importer. The longest retail string is 3,923 characters (ID 17899). Practical limits come from the widget: about 150 characters per dialogue page, about three lines for an ack.
- **IDs.** Retail uses 2–21067 (9,953 rows). Any unused integer works; the SS2 ID plan in `tools/content.py` (1,000,000 + slot × 10,000 + n) is fine.
- **Narrow strings.** Dialogs.`Code`, UIControls.`IDText` and Scripts.`CodeText` are stored as UTF-16 but narrowed through CP1251 on load (`port/dbcompat/db_storage.cpp:132-146`; `DBFormat/DataRPG.cpp:755`). Keep them ASCII.
- **TranslatedStrings.** The class copies its `String` over the Strings row with the same ID, but only when the import pass is run with `bTranslate` (`DBFormat/DataMap.cpp:838-852`). The port always passes `false` (`port/stubs/ado_stub.cpp:392`). The retail table 0x64 is empty and its columns are diplomacy fields, not strings.
- UIControls.`StringID` sets a control's initial text (`Main/UIBaseCtrls.cpp:41-42`, `:163-164`). UIControls.`Text` is not read.

### String IDs the mission UI uses

Format-prefix strings are concatenated in front of label strings. Changing a prefix restyles every use.

| IDs | Used by | Content |
|---|---|---|
| 11209 | Dialogue text prefix | `<font face=Impact size=24pt><color=FFB4997C><center>` |
| 11203 / 11204 / 11205 | Dialogue button state prefixes (normal / hover / disabled) | Impact 24pt, grey / white / dark |
| 11206 / 11207 / 11208 | Dialogue buttons | `<right>Next`, `<left>Back`, `<right>Exit` |
| 4364, 17432, 17327, 4435 | Top bar (UIControls 1293, 1344, 2130, 2131) | Menu, Leave, Objectives, Journal |
| 20992 | `pause` control (UIControls 2729) | PAUSE |
| 11143–11145, 11146–11151 | In-game menu prefixes and buttons | OPTIONS … RETURN TO GAME |
| 11197, 11198, 11235, 11236 | Defeat screen | Exit, Load |
| 7049–7053 | Journal (clue list) | prefixes, Sort by Date / Zone / Point |
| 5343, 7542 | Chapter map | Random Encounter, Exit zone |
| 4468–4470, 4511, 4512, 4690 | Item tooltips | templates with `<value id=…>` fields |
| 11177–11195 | Critical-injury tooltips | |
| 16837, 20984, 20985 | `Common.l` leave-zone and defeat dialogs | Gold-only functions; no-ops in this build |

Evidence: `Main/iMissionDlgUI.cpp:241-253`, `:287`; `Main/iInGameMenu.cpp`, `Main/iLoseFake.cpp:49-54`, `Main/iCluesMenu.cpp`, `Main/iChapterMapUI.cpp`, `Main/iCommonUI.cpp`, `Main/iUnitPanel.cpp`; `build/run/scripts/Common.l:378`, `:526-528`.

### Unit names

RPGPers.`DisplayName` is a Strings ID. The text is copied into the unit when it is created; without it the name is `[UNKNOWN]`.

- `DBFormat/DataRPG.cpp:701`, `Main/RPGUnit.cpp:89-95`.
- Shown in the unit panel under each portrait (`<font face=Courier size=10pt><nowrap>` + name, in a 63-pixel-wide control, so roughly ten characters are visible) and on the character sheet. `Main/iUnitPanel.cpp:143`, `Main/iTeamMngMenu.cpp:303-306`.
- The character sheet formats the name into a 256-character stack buffer with no bound. The longest retail name is 33 characters; stay near that.
- Markup in a name is processed.
- `LongNameID`, `BiographyID`, `PhotoID`, `CanBeListed` are later columns that Jan03 does not read (`DBFormat/DataRPG.cpp:693-740`).
- 54 of 728 retail RPGPers rows have no DisplayName.
- Names are **not** shown in dialogue or acks.

---

## 4. Fonts and markup

### Which characters exist

**Answer.** ASCII and Cyrillic. No accented Latin letters. All 18 fonts registered in the retail Fonts table carry the Windows-1251 repertoire and nothing else:

- U+0020–U+007E (all ASCII)
- Cyrillic U+0401–U+045F, U+0490–U+0491
- Punctuation and symbols: `‘ ’ ‚ “ ” „ – — … • † ‡ ‰ ‹ › « » € № ™ © ® ° ± µ ¶ · § ¦ ¤ ¬` and the no-break space

Missing: every U+00C0–U+00FF letter (ä ö ü ß é è ñ …) and everything else. A missing character is drawn as the font's default glyph (code 0x1F); in the System font the default glyph is itself absent and an arbitrary glyph is used. Write "Muller", not "Müller", as retail does for General Uwe Muller. Supporting accented Latin means regenerating font resources (the `FontGen` tool is in the engine tree); untested.

Evidence: glyph maps parsed from `build/run/res/Fonts.res` for font IDs 1, 6, 11, 12, 14, 16, 17, 19–23, 25–27, 30, 31, 33 (224–225 glyphs each, charset byte 204 = Russian); `Main/FontFormat.h:36-49` (fallback).

### Faces and sizes

- Faces (Fonts.`Name`, matched exactly and case-sensitively): `System`, `Arial`, `Courier`, `CourierBold`, `Impact`. An unknown face falls back to System. `Main/GLocale.cpp:53-91`.
- Native heights: System 16; Arial 11; Courier 12, 16, 18; CourierBold 13, 16, 17, 20, 27, 34; Impact 16, 19, 20, 23, 28, 36, 54.
- Fonts are bitmaps. The engine picks the nearest native height for the face and scales it, so any size works but looks best near a native one.
- `size=24pt` means 24 pixels at a 1024-wide screen, scaled with resolution. `size=24px` is fixed pixels. `Main/GText.cpp:595-629`, `Main/UIML.cpp:174-198`.

### Two text engines, two tag sets

Tags like `<color=red>` in the log are this markup. They **are usable in dialogue text**; the retail format prefix 11209 is itself made of them.

| | Dialogue, clue pages, tooltips (`CMLText`) | Acks, plain labels, console, log panel (`CText`) |
|---|---|---|
| Source | `Main/UIML.cpp:672-686`, `:704-785`; `Main/UIMLHandlers.h` | `Main/GText.cpp:155-280`, `:371-414` |
| Default font | System 16pt, white (`UIML.cpp:415-416`) | System 22pt, white (`GText.cpp:163`) |
| Line break | `<br>` only. A newline character becomes a space | `<br>` or a newline |
| Alignment | `<left> <right> <center> <justify>`; `<top> <middle> <bottom>` | `<left> <right> <center> <justify> <nowrap>` |
| Font | `<font face=F size=N[pt|px] outlinesize=N outlinecolor=C>` | `<font face=F size=N[pt|px]>`; also `size=small|normal|large|xlarge|xxlarge` |
| Colour | `<color=C>` | `<color=C>` |
| Images | `<image id=UITextureID align=left|right width=N height=N>`; `<wrapleft>`, `<wrapright>` | none |
| Literal `<` `>` | not possible | `<lb>`, `<rb>` |
| Values | `<value id=name>` only where the code supplies values (tooltips); not in dialogue | none |

Rules that apply to both:

- **Tags are lowercase and case-sensitive.** `<BR>` is ignored.
- **There are no closing tags.** A tag changes state until the next tag of the same kind. Unknown tags are skipped silently (`</br>`, `<tab>`, `<justified>` in retail data do nothing here).
- **Colour** is a name or hex. Names: `white red green blue yellow cyan orange pink brown grey black darkyellow beige lightblue`. Hex is **AARRGGBB** with or without `0x`: `FFB4997C`. A six-digit value has alpha 0 and is invisible. `Main/UIMLHandlers.h:10-46`, `Main/GPixelFormat.h:41-57`.
- **Wrapping** is automatic at word boundaries to the control's width. A single word wider than the box is not broken.
- In dialogue text **never use a bare `<` or `>`**: `<` swallows text up to the next `>`, and a stray `>` re-runs the previous tag. `Main/UIML.cpp:729-768`.
- A `<font …>` tag in dialogue text resets any outline. `Main/UIMLHandlers.h:124-127`.
- In ack text the engine replaces character U+0085 with `...`. The real ellipsis `…` (U+2026) is in the fonts and is what retail strings use (723 times). `Main/iMissionUI.cpp:67-93`.

Since the dialogue prefix already sets Impact 24pt, beige, centred, a dialogue string normally needs no tags. Use `<color=…>` for emphasis and `<br>` for a forced break; a larger font reduces the three-line capacity.

---

## 5. Speakers who are not in the party, and the hero

### Answer

A speaker needs only a valid **RPGPers** row. `AckInfos.WhoID` is an RPGPers ID. When the line plays, the engine uses the first unit on the map with that pers ID; if there is none, it builds a temporary unit from the RPGPers row (model, uniform, face) just for the dialogue screen. So an off-map radio contact or commanding officer works without placing anyone.

DialogPers plays no part in this lookup. No name is displayed.

- Live unit first: `Main/wDialog.cpp:49`, `Main/wMain.cpp:2067-2075` (first match; several units sharing a pers ID are indistinguishable).
- Temporary unit: `Main/wDialog.cpp:63-73`.
- Every retail dialogue speaker also has a DialogPers row (52 rows: `Code` such as `NmdOrlov`, `GFirstGCiv`), but the engine reads only `PersID` and only for the hero. The codes look like speaker keys from the original spreadsheet import; **unverified**.
- The figure shown is the pers's 3D model through cameras 62 and 63, not a photo. RPGPers.`PhotoID` is not read.
- The port stubs the LifeStudio head library (`port/README.md:34`, `port/ROADMAP.md:38`). Heads do render in the unit panel (`build/shots/m00n_120.png`), but expect no lip movement from `HeadSequenceID`. **Unverified.**

### The hero

In the campaign a hero line is authored against a placeholder pers and swapped for the real hero at play time:

- Sides.`HeroDialogPersID` → DialogPers.`PersID`. Retail: Axis side 1 → DialogPers 5 → pers **165**; Allies side 2 → DialogPers 1 → pers **176**. `DBFormat/DataRPG.cpp:1077`, `Main/RPGGlobal.cpp:324-330`.
- If `WhoID` equals that placeholder, it is replaced by the actual hero's pers ID; if there is no hero, the line is skipped. `Main/wDialog.cpp:90`, `:98-105`.
- The hero's RPGPers.`Voice` then selects which of the six sounds plays.

**Under `map <id>` this does not work as authored.** The player has no side, so the placeholder ID evaluates to 0. `Main/RPGGlobal.cpp:324-330`; the default party is pers 54, 53, 14, all flagged hero, and `GetHero()` returns the first, pers 54 (`Main/RPGGlobal.cpp:212-229`, `:309-321`). Consequences:

- A line with `WhoID=165` shows a generic Axis Engineer stand-in, not your squad leader.
- For SS2 missions launched with `map`, **put the party member's real RPGPers ID in `WhoID`** (54 for the default first merc "Fritz", or whichever pers you pass on the `map` line). The engine then finds the live unit.
- `WhoID=0` also resolves to the hero under `map`, because 0 equals the unset placeholder. This would dereference a null pers once a side exists, so treat it as a test trick only. **Unverified.**

When SS2 gets a real campaign entry (a side with `HeroDialogPersID`), switch hero lines to the placeholder pers.

In scripts, `GetHero()` returns the hero's unit (`Main/scriptUnit.cpp:470`).

---

## Blockers: what this build cannot do without engine changes

1. **No speech.** FMOD is stubbed; `SoundID` values are accepted and silently do nothing.
2. **No hints.** `ShowHint` / `AddHints` are no-ops; the Gold hint window and table 0x6D have no code.
3. **No script-driven message line, message box, tutorial window or floating text.** The log panel is there but unreachable from Lua.
4. **No objectives UI**, and the goal functions are no-ops in the staged exe.
5. **Acks last a fixed 3 seconds and show one line**, and are invisible until the `ack` control is added (that part is data).
6. **No speaker names** in the dialogue screen.
7. **No accented Latin characters** without new font resources.
8. **`ClueShow` needs a scenario**, which `map` does not create.
9. **Hero placeholder is not resolved under `map`** (workaround: real pers ID).
10. **`FemaleStringID` is ignored**; one text per line regardless of hero sex.
11. **One language per `game.db`**; TranslatedStrings is never applied.

---

## Things to try

Not run for this note. Suggested test in the sandbox mission script, after adding the recipe rows (or first with retail `GFirstG1`):

```lua
function OnDialogPhrase( code, n ) out( "SS2: phrase ", code, " ", n ) end
function OnDialogFinished( code ) out( "SS2: finished ", code ) end
function Talk()
	Sleep( 40 )
	out( "SS2: dialog start" )
	WaitForUI( DialogPlay( "SS2_m00_intro" ) )
	out( "SS2: dialog returned" )
end
StartThread( Talk )
```

Run `python tools/run.py map 50001 --shots 8,14 --out dlg`. Expected:

- Log: `WARNING: Dialog start!` (`Main/iMissionDlgUI.cpp:92`), then `SS2: phrase SS2_m00_intro 0`.
- Screenshot at +8 s or later: black bars top and bottom, a figure bottom-left, the first line centred at the bottom in beige Impact, a Next button.
- `SS2: dialog returned` must **not** appear, because nobody presses Next. If it appears at once, `WaitForUI` is not waiting (check that the dialogue code was found).

For acks: add the UIControls row from section 2, call `DialogPlayAsAcks("…")` with a one-line dialogue, and take a shot within 3 seconds. The three `UI-ERROR … ack` lines should also disappear from the log.

---

## Recipe: add a text-only dialogue

Two lines: the first party member speaks, an off-map officer answers. IDs follow the SS2 plan for mission slot 1 (`1010000 + n`); any unused IDs work. Columns not listed stay 0 or empty, which is what `ssdb` `upsert` writes for a new row.

**1. Strings** — the text

| ID | UserName | String |
|---|---|---|
| 1010000 | `SS2\m00\intro.1` | `The bank is on the far side of the square. We go in quiet.` |
| 1010001 | `SS2\m00\intro.2` | `Understood. Keep the civilians out of it.<br><color=white>Out.` |

**2. AckInfos** — one per line

| ID | UserName | WhoID | StringID | SoundID, SoundID1–5 | HeadSequenceID, 1–5 |
|---|---|---|---|---|---|
| 1010000 | `SS2\m00\intro.1` | 54 (party member on the map) | 1010000 | 0 | 0 |
| 1010001 | `SS2\m00\intro.2` | 409 (any existing RPGPers; 409 is retail `EBaseEBoss`) | 1010001 | 0 | 0 |

**3. Dialogs** — the dialogue

| ID | Code | UserName |
|---|---|---|
| 1010000 | `SS2_m00_intro` | `SS2_m00_intro` |

**4. DialogSeqs** — the order (ascending `ID` = play order)

| ID | DialogID | AckInfoID | AckInfoOrder |
|---|---|---|---|
| 1010000 | 1010000 | 1010000 | 0 |
| 1010001 | 1010000 | 1010001 | 0 |

**5. Script**

```lua
WaitForUI( DialogPlay( "SS2_m00_intro" ) )
```

`WaitForUI` sleeps the calling script thread. Retail calls it at the top level of the mission chunk (script 95 sleeps and waits there, lines 373–410), and the sandbox's `StartThread` pattern should work equally well. Neither was run for this note.

Checklist:

- `Code` is unique across Dialogs (retail has 142) and ASCII.
- Every `AckInfoID` exists in AckInfos; every `WhoID` exists in RPGPers.
- Each string is under about 140 characters, uses only ASCII or Cyrillic plus the listed punctuation, has no bare `<` or `>`, and uses `<br>` rather than newlines.
- Not needed: DialogPers, AckSeqs, Acks, Sounds, HeadSeqs, TranslatedStrings.

With `ssdb`:

```python
db['Strings'].upsert(1010000, UserName='SS2\\m00\\intro.1', String='The bank is on the far side of the square. We go in quiet.')
db['AckInfos'].upsert(1010000, UserName='SS2\\m00\\intro.1', WhoID=54, StringID=1010000)
db['Dialogs'].upsert(1010000, Code='SS2_m00_intro', UserName='SS2_m00_intro')
db['DialogSeqs'].upsert(1010000, DialogID=1010000, AckInfoID=1010000, AckInfoOrder=0)
```

To add a voice later: a Sounds row (retail dialogue sounds use `MinDistance=20`, `MaxDistance=10000`, `Priority=1`) with its audio under the sound's ID, referenced from `SoundID`. This cannot be heard until the port has a real audio backend, and the resource layout for new sounds is **unverified**.
