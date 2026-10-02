# Visual issues from adversarial screenshot review

Open findings from the reviewer agents (`docs/screenshot-review.md`). The full
reviews are in `build/reviews/` (not committed; regenerate by re-reviewing).

**First pass, 2026-10-02: 55 screenshots reviewed, 48 rejected, 7 accepted with
issues, none accepted clean.** Two calibration shots (`cal_03`, `cal_08`) and
five late survey shots are not reviewed yet.

No screenshot taken so far is valid evidence of what its claim said. In
particular the three images in `docs/screenshots/` overstate what was shown:
see S-10 to S-13.

## SS2 content and tools (ours to fix)

| ID | Finding | Seen in | Status |
|---|---|---|---|
| S-01 | Cameras are not where the mission file says. Camera anchors are world units (tile x 0.625, read raw in the engine's `DataCamera.cpp`), but `tools/content.py` and `tools/survey.py` write tile coordinates. Every camera so far looks past its subject, toward the far corner of the level. | all survey shots, all mission shots | open; calibration shots taken, not yet reviewed |
| S-02 | Framing ignores the bottom interface panel (170 px): subjects are centred on the full frame and cut off by the panel. | all | open |
| S-03 | Levels are drawn as a diamond (yaw -0.8), so 30-80% of each frame is black void while the level runs out of frame. | all survey shots | open |
| S-04 | One fixed camera distance for every level size: 48-tile and larger levels show a third or less. The engine caps script cameras at distance 65 (`mission_camera_limits` in autoexec.cfg); a larger level needs raised limits or several shots. | survey | open |
| S-05 | Straight-down views with roofs on show nothing of interiors. Take a second shot with the view cut at the ground floor (`Floor( 0 )`). | survey | open |
| S-06 | Claims asserted things an image cannot show (level name, tile size, "placed by SS2", "empty mission"). Claims must describe only what should be visible. | all | open |
| S-07 | "Empty" survey missions are not empty: the engine adds a default three-person party, and several retail levels bring their own soldiers through nested templates and start in turn-based combat (2253, 3116, 4096, 8006). A mission's shell can add enemies the mission file does not list. | survey | open; mission tests must count every unit on the map |
| S-08 | Night scenes are too dark to judge (mean brightness 10-40 of 255). Survey in daylight. | many | open |
| S-09 | Near-identical shots for different names (6084 and 6102; 7762, 7811 and 7944). The survey lists variants of one layout as separate levels. | survey | open |
| S-10 | `m00_sandbox_first_run.png`: stale (taken with an earlier camera), two of three units cut off by the panel. The later overview shot showed only off-screen enemy markers, not the units. | docs/screenshots | open; retake |
| S-11 | `m00_compose_new_level.png`: the sentry box is not visible and the well cannot be identified; the house was dropped onto forest, with trees growing through its roof; the mission was in combat. Only the house is shown. | docs/screenshots | open; needs a way to clear the shell's trees under added buildings |
| S-12 | `m00_compose_dialogue.png`: the dialogue screen and the authored line are shown, but the line contradicts the scene ("the house is dark" in daylight with a smoking chimney; no fence), and it breaks badly ("dark." alone). | docs/screenshots | open |
| S-13 | Mission 1 shots do not show the team: `m01_03` is 95% black with no interface, `m01_10` shows one or two hooded figures at the map edge. Same cause as S-01. | m01 | open |
| S-14 | Farm scouting grid: no unit is drawn under a roof, and some grid units stand inside trees. | farm_* | open |

## Engine port (passed to the remaster session 2026-10-02)

| ID | Finding | Status |
|---|---|---|
| E-01 | The real mouse and keyboard reach a background game: the cursor is parked at a screen edge in some shots, the camera has edge-scrolled, and in one the posture menu is open. Unattended runs are not repeatable while someone uses the machine. | requested: an option to ignore device input |
| E-02 | The mouse cursor is in every engine screenshot, at screen centre, as an aimed-shot body diagram on an opaque card; the pistol action button is drawn selected at mission start. | requested: screenshot without cursor and interface |
| E-03 | The turn bar in the top panel is a flat cyan block; turn text on it is barely legible. | reported |
| E-04 | Unit tab names are about 6 px high and unreadable. | reported |
| E-05 | "Leave" is drawn highlighted (green in real time, red in turn-based) unlike the other top buttons. | reported |
| E-06 | The right half of the weapon panel is blank. | not yet reported |
| E-07 | Enemy markers show a helmeted soldier over civilians in hats. | not yet reported; may be retail |
| E-08 | Telegraph wires drawn as dotted or broken white lines (6084, 6102, 4096). | not yet reported |
| E-09 | No speaker name or highlight on the dialogue screen; both figures cropped by the frame. | not yet reported; compare with retail |
| Known | Red "PAUSE" label, "Work in progress", faceless portraits and dialogue figures, no objectives screen. | known to the port |

## Needs a comparison with the retail game before it has an owner

- Night lighting far darker than a player could read.
- Partial or missing roofs (4794, 4798, the forest churches).
- Pale, washed-out plank roofs on the farmhouse in a summer forest.
- Hard map edges with tree crowns and grass hanging over black void.
- Shadows the wrong colour or with no caster (sandbox plaza, 5354).
