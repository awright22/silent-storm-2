# Adversarial screenshot review

Standing rule (project owner, 2026-10-02): **every screenshot taken of the game
is reviewed by an adversarial reviewer agent** before anything is concluded
from it. The author of a change does not review their own screenshots.

This file is the reviewer's brief. Whoever takes a screenshot hands the
reviewer the image path and a one-line claim of what it is supposed to show,
and nothing that argues the claim is true.

## Writing the claim (for the author)

The first review pass rejected most screenshots partly because the claims said
things no image can show. A claim is a list of things a viewer can point to.

- Say what should be **visible and where**: "four figures stand among trees in
  the lower right; a farmhouse with a smoking chimney is upper centre".
- Give **counts**: how many units, buildings, interface entries.
- Say the **state** the picture should be in: day or night, real time or
  turn-based, dialogue open or not, which party is in the unit panel.
- Leave out what cannot be seen: level names and IDs, sizes in tiles, who
  placed something, which camera record was used, that a cheat was on.
- One screenshot, one purpose. If it is evidence that three things were added,
  all three must be identifiable in the frame.

## The reviewer's job

Assume the screenshot is wrong until the image itself shows otherwise. You are
looking for reasons to reject it, not for reasons to accept it.

1. **Open the image** with the Read tool and look at it. Do not rely on the
   claim, the file name or the mission source to tell you what is in it.
2. **Test the claim.** For each thing the claim says is shown, point to where
   it is in the image. Say plainly what is claimed but not visible, and what is
   visible that the claim does not mention.
3. **Hunt for defects**, whether or not they relate to the claim:
   - *Rendering*: black, untextured or missing surfaces; holes in terrain or
     buildings; geometry cut off; things floating, sunk or intersecting;
     lighting that makes the scene unreadable; shadows without casters; the
     void beyond the map edge filling much of the frame.
   - *Characters*: missing heads or faces, wrong or duplicate models, units
     standing inside walls or on roofs, units outside the map, wrong facing.
   - *Interface*: debug or placeholder text, overlapping or clipped text, empty
     panels, missing icons, wrong labels, markers pointing at nothing.
   - *Text*: spelling, truncation, lines breaking mid-word, placeholder glyphs,
     text that does not fit its box, wording that contradicts the scene.
   - *Composition*: is the subject in frame and large enough to judge; would a
     player understand what they are looking at.
   - *Consistency*: does the scene fit the mission it belongs to (setting,
     time of day, who is present).
4. **Say what a still image cannot tell you** (motion, sound, whether a unit
   reacts) instead of guessing.

Known engine-port conditions as of 2026-10-02 are listed below. Still report
them when you see them, marked "known", so that the count stays honest. Do not
use this list to wave through anything that merely resembles one of them.

- A dark red "PAUSE" label near the top centre of mission screenshots.
- "Work in progress" in the top right corner.
- Characters without heads or faces in close-ups and dialogue (the facial
  animation library is a stub).
- No objectives shown anywhere; the "Objectives" button does nothing.

## What to write

Write the review to the review path given with the screenshot (`python
tools/reviews.py --batch N` writes screenshot, claim and review path together)
and reply with the same content in brief. Use this shape:

```
Screenshot: <path>
Claim: <the claim as given>
Verdict: REJECT | ACCEPT WITH ISSUES | ACCEPT

Claim check
- <claimed thing>: visible at <where> | NOT visible

Findings
1. [blocker|major|minor|cosmetic] [SS2 content|engine port|retail data|unknown]
   <what is wrong, where in the image, why it matters>
   Check: <how the author can confirm or fix it>

Cannot be judged from this image
- ...
```

- **REJECT**: the claim is not supported by the image, or there is a blocker.
- **ACCEPT WITH ISSUES**: the claim holds and there are findings to act on.
- **ACCEPT**: the claim holds and you found nothing beyond known conditions.
  This should be rare; look again before using it.

Owner means who has to fix it: *SS2 content* (this repository's missions,
scripts, text, placement), *engine port* (rendering, interface, behaviour of
the engine), *retail data* (the original game's own assets look like this).

## What the author does with a review

- Fix every SS2-content finding or record why not.
- Pass engine-port findings to the engine port.
- Keep the open list in `docs/qa/visual-issues.md` current.
- A rejected screenshot is not evidence of anything. Retake it after the fix
  and have the new one reviewed.
