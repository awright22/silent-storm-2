# Vertical slice proposal: Norway, winter 1943

*Created: 2026-10-02*
*Status: Proposal. The theater, the names and the story beats below are
suggestions for the project owner to accept, change or replace. The mission
structure was chosen to fit what the engine and the original level art can do
today.*

---

## Why this theater

The original game's small winter levels all load quickly on the ported engine
and have no mission attached to them: a farm, a railway siding with a goods
train, a saw mill, a radio station and a forest track. Together they make a
complete small theater without any new art.

Occupied Norway fits the concept's pillars:

- **Grounded until you go looking.** Commando raids on Norwegian industry and
  transport are real history (the heavy-water sabotage of 1943 is the best
  known). The setting needs no invention to justify a four-person team working
  behind the lines in the snow.
- **The optional conspiracy has a natural hook.** A plant producing something
  the Germans want badly, and shipments that do not match the paperwork, give
  curious players a thread to pull without forcing it on anyone else.
- **Every mission, your way.** Small, isolated sites with a handful of guards
  suit stealth, assault and demolition equally.

The slice is three missions and a hideout. It is the concept's "Vertical
Slice" tier, built first as the MVP's single mission.

## The squad

Four returning Allied characters from the original game, so their models,
portraits, voices and biographies already exist:

| Role | Character | Original ID |
|---|---|---|
| Scout, squad leader in the field | Lt. Erin "Elf" Farrell (UK) | RPGPers 118 |
| Engineer | Doug (UK) | RPGPers 116 |
| Sniper | Arvid (Norway) | RPGPers 42 |
| Medic | Yves (France) | RPGPers 120 |

Arvid is Norwegian in the original data, which gives the team its local guide.
New characters can replace or join them later; a new character is a set of
database rows, not new art.

## Locations

| Mission | Working title | Level (shell) | Size | Loads in |
|---|---|---|---|---|
| Hideout | The cabin | Back of beyond (5328) | 48x48 | 12 s |
| 1 | Cold Welcome | Farm (5354) | 48x32 | 21 s |
| 2 | Night Freight | Railway (5341) | 24x48 | 51 s |
| 3 | Dead Air | Radio station (5326) | 48x48 | 6 s |

The saw mill (5316) is a spare.

## Mission 1: Cold Welcome (the MVP mission)

**Premise.** The team's resistance contact was due to meet them at an isolated
farm. A German patrol arrived first. The contact is being held in the
farmhouse while the patrol waits for a truck.

**Layout.** Farmhouse with a smoking chimney in the south-east, barn in the
north-west, a walled yard with a well in the south-west, open snow between them,
conifers along the edges. The team arrives on the west edge behind the barn,
which no guard can see (measured in the engine with `tools/vismap.py`).

**Objectives.**

1. Free the contact: no German left standing in or around the farmhouse.
2. Keep the contact alive.
3. Leave: bring the team and the contact back to the tree line.

**Opposition.** Six soldiers of an ordinary patrol: one walking a beat between
the barn and the house, one at the well, two in the yard, an officer and a
guard in the house with the contact.

**Three ways through** (pillar 2):

- *Quiet.* Follow the barn's blind side, take the patrolling sentry when the
  beat carries him out of sight, enter by the back.
- *Loud.* Open from the tree line with the sniper, then push across the yard.
- *Through the wall.* The farmhouse is a destructible building. The engineer
  can open the wall away from the door instead of using it.

**Failure.** The contact dies, or the whole team is down.

**What it proves.** Destruction and ballistics come from the engine. The
mission adds a briefing in dialogue, a patrol the player can time, a neutral
character who must survive, script-tracked objectives and an extraction.

## Missions 2 and 3 (outline)

- **Night Freight.** A goods train is held overnight at a siding. Find which
  wagon carries the plant's shipment and destroy it, or mark it and leave it
  for curious players to open. First use of demolition as the objective.
- **Dead Air.** The area's radio station must be off the air before the raid
  that ends the theater. A site where an alarm changes the mission: guards
  that reach the transmitter call reinforcements.

## How the slice plays in the engine today

| Need | Today | Depends on |
|---|---|---|
| Launch a mission with the SS2 squad | Works: `map <id> 118 116 42 120` | nothing |
| Briefing and in-mission dialogue | Works, text only | audio backend for voices |
| Patrols, neutral characters, scripted reactions | Works | nothing |
| Objectives the player can read | Journal entries only, inside a campaign | engine: objectives screen |
| Win and lose | Script detects both; the lose screen exists; leaving is a button the script cannot gate | engine: script control of leaving |
| Chain the missions into a campaign with a hideout | Possible as data, started by console command with a fixed default party | engine: start a campaign for a new side |
| Carry decisions between missions | Only as "clues" | engine: campaign variables |

The engine items are requests to the engine port. Until they land, missions are
built and tested one at a time with `map`.

## Open decisions for the owner

- Is Norway the first theater, or should the slice use different ground?
- Returning characters, new characters, or a mix?
- Working titles and all names are placeholders.
