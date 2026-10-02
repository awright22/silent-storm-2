# Game Concept: Silent Storm 2

*Created: 2026-03-29*
*Status: Draft (technical sections revised 2026-10-02)*

---

## Elevator Pitch

> It's a turn-based tactical RPG where you lead a WWII special operations squad
> across multiple theaters, using physically-simulated destructible environments
> and deep infiltration mechanics to complete missions your way — with an
> optional sci-fi conspiracy that reveals itself only to players who go looking.

---

## Core Identity

| Aspect | Detail |
| ---- | ---- |
| **Genre** | Turn-based tactics / tactical RPG |
| **Platform** | PC (Steam, GOG) |
| **Target Audience** | Fans of classic tactical games (JA2, XCOM, original Silent Storm) |
| **Player Count** | Single-player |
| **Session Length** | 1-2 hours (one mission = one session) |
| **Monetization** | Non-commercial fan sequel (free release under Nival's non-commercial license) |
| **Estimated Scope** | Large (12+ months, solo/tiny team) |
| **Comparable Titles** | Silent Storm (2003), Jagged Alliance 3, XCOM 2, Desperados III |

---

## Core Fantasy

You are the unseen hand that reshapes the battlefield. Every building is a
puzzle of load-bearing walls and structural weak points. Every compound has a
front door — and a dozen other ways in that only your engineer can see. You
don't fight on the terrain; you fight *with* it.

The original Silent Storm proved that destructible environments could be a
core tactical mechanic, not just a cosmetic feature. Silent Storm 2 pushes
this further: structural integrity is a weapon, stealth is a full playstyle,
and every mission is a sandbox you can approach from any angle.

---

## Unique Hook

Like XCOM, AND ALSO every building is a physics sandbox where structural
integrity determines whether you snipe through a hole in the wall or collapse
the entire floor onto the enemies below — and you can skip the fight entirely
through deep infiltration mechanics.

The "player's choice" sci-fi layer means the game serves two audiences
simultaneously: players who want a grounded WWII experience and players who
want to unravel a pulp-conspiracy rabbit hole. The depth of weirdness is
proportional to your curiosity.

---

## Player Experience Analysis (MDA Framework)

### Target Aesthetics (What the player FEELS)

| Aesthetic | Priority | How We Deliver It |
| ---- | ---- | ---- |
| **Sensation** (sensory pleasure) | 3 | Building collapses, bullet impacts, explosion physics, environmental destruction feedback |
| **Fantasy** (make-believe, role-playing) | 2 | WWII commando squad leader, tactical genius, the person who finds the third option |
| **Narrative** (drama, story arc) | 4 | Character permadeath stakes, branching conspiracy, theater-specific storylines |
| **Challenge** (obstacle course, mastery) | 1 | Deep tactical combat, environmental puzzle-solving, resource-constrained infiltration |
| **Fellowship** (social connection) | N/A | Single-player — delivered through squad bonds instead |
| **Discovery** (exploration, secrets) | 3 | Hidden conspiracy layer, environmental secrets, creative tactical solutions |
| **Expression** (self-expression, creativity) | 2 | Multiple valid approaches per mission (assault, stealth, demolition, mixed), squad composition |
| **Submission** (relaxation, comfort zone) | N/A | Not a relaxation game |

### Key Dynamics (Emergent player behaviors)

- Players experiment with destruction to create novel tactical advantages
  (breach points, sniper nests, collapsed cover, improvised bridges)
- Players develop preferred playstyles (ghost infiltrator, demolition crew,
  precision sniper team) and build squads to match
- Players weigh the risk of loud approaches (alert enemies, structural
  collapse risk) against quiet ones (fewer resources, higher tension)
- Players who investigate anomalies discover the conspiracy layer, creating
  a natural community of mystery-hunters sharing findings
- Players replay missions to discover approaches they missed

### Core Mechanics (Systems we build)

1. **Structural Destruction** — physically-simulated buildings with load-bearing
   walls, floor integrity, material properties. Damage propagates structurally.
2. **Ballistic Simulation** — projectiles with trajectory, penetration through
   materials, ricochet, body-part targeting, cover degradation.
3. **Infiltration System** — multi-state detection (unaware → suspicious →
   alert → combat), disguises, distractions, silent takedowns, noise
   propagation, line-of-sight stealth.
4. **Squad Tactics** — action-point turn system, class abilities, overwatch,
   suppression, morale, inter-character synergies.
5. **Strategic Layer** — theater selection, intel gathering, squad management,
   equipment procurement, mission consequences that carry forward.

---

## Player Motivation Profile

### Primary Psychological Needs Served

| Need | How This Game Satisfies It | Strength |
| ---- | ---- | ---- |
| **Autonomy** (freedom, meaningful choice) | Multiple valid approaches per mission; squad composition; theater selection; conspiracy depth is player-driven | Core |
| **Competence** (mastery, skill growth) | Tactical depth rewards planning; destruction system rewards spatial reasoning; stealth rewards patience and observation | Core |
| **Relatedness** (connection, belonging) | Squad member personalities, permadeath stakes, character growth and bonds | Supporting |

### Player Type Appeal (Bartle Taxonomy)

- [x] **Achievers** (goal completion, collection, progression) — Mission ratings, squad advancement, equipment collection, conspiracy progress tracker
- [x] **Explorers** (discovery, understanding systems, finding secrets) — Environmental destruction experimentation, hidden conspiracy content, alternative mission approaches
- [ ] **Socializers** (relationships, cooperation, community) — Limited (single-player), but squad personality provides some of this
- [ ] **Killers/Competitors** (domination, PvP, leaderboards) — Not applicable

### Flow State Design

- **Onboarding curve**: First 3 missions are tutorial theater (training compound,
  then two low-stakes operations). Introduce destruction in mission 1, basic
  combat in mission 2, stealth option in mission 3. Each mission teaches one
  system without overwhelming.
- **Difficulty scaling**: Enemy count, equipment quality, and map complexity
  increase. Later missions have multiple enemy types requiring mixed tactics.
  Optional conspiracy missions scale independently based on how deep the player
  goes.
- **Feedback clarity**: Destruction is immediate and visceral (visual + audio).
  Hit percentages shown before shooting. Stealth state always visible per
  character. After-action report shows stats and alternative approaches hinted.
- **Recovery from failure**: Mission failure doesn't end the campaign — squad
  members can be captured (rescue mission generated), killed (permanent), or
  the mission can be retried. No ironman by default; optional ironman mode.

---

## Core Loop

### Moment-to-Moment (30 seconds)
Move a squad member, observe the environment, make a tactical decision: shoot
through this wall or breach it? Go around or go through? The 30-second loop
is **observe → decide → act → observe consequences**. Destruction feedback
makes every action feel impactful — walls crack, debris falls, dust clouds
obscure vision.

### Short-Term (5-15 minutes)
Clear a room, secure a floor, reach an objective. Each engagement is a
mini-puzzle: how do I neutralize these enemies with minimum casualties and
resource expenditure? Stealth players are managing detection states. Assault
players are managing structural integrity and ammo. Engineers are creating
advantages for the rest of the team.

### Session-Level (30-120 minutes)
One complete mission: briefing → deployment → execution → extraction → debrief.
Missions have primary objectives and optional objectives (intel, rescue,
sabotage). The debrief shows what you accomplished, what you missed, and how
your approach compared to alternatives. Natural stopping point after debrief.

### Long-Term Progression
- **Squad growth**: Characters level up, unlock class abilities, build
  relationships with squadmates
- **Equipment acquisition**: Better weapons, specialized gear, engineering tools
- **Theater progression**: Advance across multiple fronts, unlock new theaters
- **Conspiracy depth**: Optional investigation reveals increasingly strange
  findings, culminating in a choice about how to handle Thor's Hammer tech
- **Campaign stakes**: Cumulative mission outcomes affect the war's progress

### Retention Hooks
- **Curiosity**: What's in the next theater? What's behind the conspiracy?
  What happens if I collapse that building differently?
- **Investment**: Squad members you've leveled for 20 hours. The character
  who saved your sniper in North Africa. Permadeath makes them irreplaceable.
- **Mastery**: "I bet I can ghost this mission." "I wonder if I can collapse
  the whole compound from outside." The systems invite creative problem-solving.

---

## Game Pillars

### Pillar 1: The Environment Is Your Weapon
Every wall, floor, and ceiling is a tactical tool. Destruction isn't cosmetic —
it's the defining mechanical differentiator. Buildings have real structural
integrity. Creating a sniper hole, collapsing a floor, or demolishing cover
should always be a viable and satisfying option.

*Design test*: If we're debating between a simpler environment and one with
richer structural properties, this pillar says we choose structural richness
every time, even at the cost of visual fidelity.

### Pillar 2: Every Mission, Your Way
The player should always have at least three valid approaches: assault, stealth,
and a creative third option enabled by the environment or mission-specific tools.
No mission should have a single intended solution.

*Design test*: If we're debating between a scripted cinematic moment and a
sandbox encounter, this pillar says sandbox. If a mission can only be completed
one way, it needs redesign.

### Pillar 3: Grounded Until You Go Looking
The game's default tone is authentic WWII — real weapons, real theaters, real
stakes. The sci-fi conspiracy exists but never intrudes on players who don't
seek it out. The weird stuff is a reward for curiosity, not a forced tonal shift.

*Design test*: If we're debating whether to make a conspiracy element mandatory
or optional, this pillar says optional. If a player can finish the entire
campaign without seeing a Panzerklein, we've succeeded.

### Pillar 4: Consequences That Matter
Permadeath is real. Mission failures have campaign consequences. Resources are
finite. Decisions in one theater affect options in another. The player should
feel the weight of command.

*Design test*: If we're debating between a forgiving system and a consequential
one, this pillar says consequential — but fair. The player should always
understand why something went wrong.

### Anti-Pillars (What This Game Is NOT)

- **NOT a real-time game**: Turn-based is core to the tactical identity. We will
  never add a real-time mode or real-time-with-pause. The deliberate pace is a
  feature.
- **NOT a hero shooter**: No single overpowered character. This is a squad game.
  If one character can solo a mission, the balance is broken.
- **NOT a Panzerklein game**: The original's biggest mistake was making mechs
  standard equipment. Panzerkleins, if they appear at all, are rare encounters —
  terrifying enemy-only boss fights, not player gear (unless the player pursues
  the deepest conspiracy path, and even then, they're fragile prototypes).
- **NOT a procedural game**: Missions are hand-crafted. No random encounters.
  Quality over quantity. Every mission should feel designed and purposeful.

---

## Inspiration and References

| Reference | What We Take From It | What We Do Differently | Why It Matters |
| ---- | ---- | ---- | ---- |
| Silent Storm (2003) | Destructible environments, ballistics, squad system, WWII setting, class system | Fix stealth, remove forced Panzerkleins, no random encounters, better AI, multiple theaters | Direct predecessor — we inherit its DNA and fix its flaws |
| Jagged Alliance 2 | Deep squad personality, strategic layer, sector control, memorable characters | More environmental interaction, less inventory management tedium | Proves tactical RPGs can have characters you genuinely care about |
| XCOM 2 | Modern tactical UI, clean action economy, mod support, procedural maps mixed with scripted | Hand-crafted maps (no procedural), real destruction (not cosmetic), WWII not sci-fi | Modernized the genre's UX — we learn from their interface design |
| Desperados III | Stealth-tactics hybrid, showing detection cones, multi-character stealth planning | Turn-based not real-time, destructible environments, RPG progression | Proves stealth + tactics works and that showing enemy awareness is good UX |
| Brothers in Arms | WWII authenticity, squad-based, suppression mechanics | Turn-based not FPS, deeper tactics, multiple theaters | Authenticity standard for WWII setting |

**Non-game inspirations**:
- Band of Brothers / The Pacific (HBO) — tone, camaraderie, theater variety
- The Dirty Dozen / Where Eagles Dare — commando fantasy, creative problem-solving
- Wolfenstein: The New Order — sci-fi conspiracy done right (escalating gradually)
- Real WWII special operations (SOE, OSS, Brandenburgers) — mission variety and creativity

---

## Target Player Profile

| Attribute | Detail |
| ---- | ---- |
| **Age range** | 25-45 |
| **Gaming experience** | Mid-core to hardcore; comfortable with turn-based systems and complexity |
| **Time availability** | 1-2 hour sessions, a few times per week |
| **Platform preference** | PC (keyboard + mouse) |
| **Current games they play** | XCOM 2, Jagged Alliance 3, BattleTech, Divinity: Original Sin 2, Desperados III |
| **What they're looking for** | A tactics game where the environment is as important as the units — not just cover bonuses but actual physics-based destruction. They miss what Silent Storm did and want it done right. |
| **What would turn them away** | Forced sci-fi tonal shifts, Panzerkleins as standard equipment, mobile-game energy systems, real-time gameplay, oversimplified mechanics |

---

## Technical Considerations

| Consideration | Assessment |
| ---- | ---- |
| **Engine** | The original Silent Storm C++ engine (DirectX 9, Lua 4.0 scripting), ported to a modern compiler in a separate repository. SS2 runs on it as a content layer and does not fork it (ADR-0001). |
| **Key Technical Challenges** | Authoring levels without the original map editor; adding sequel mechanics (deeper stealth, consequences) that need new engine script functions; the engine port's remaining gaps (audio, video, parts of the script API) |
| **Art Style** | Reuse the original Silent Storm assets in place. New levels are composed from existing building templates, objects and units as database rows. New 3D models and textures are out of reach until the engine can load them from outside the retail packs. |
| **Art Pipeline Complexity** | Low: text sources compiled by `tools/build.py` (see `docs/content-pipeline.md`) |
| **Audio Needs** | Moderate: the original sounds are available once the engine port has a real audio backend; new music and voice acting for sequel content |
| **Networking** | None (single-player) |
| **Content Volume** | ~20-30 hand-crafted missions across 3-4 theaters, ~6 character classes, ~50+ weapons, 10-20 squad-recruitable characters |
| **Procedural Systems** | None: all hand-crafted (anti-pillar) |

### Where the engine stands

The engine port builds with a modern MSVC toolchain and plays the retail game
from an owned install: main menu, campaign entry and tactical missions. Audio,
video and facial animation are still stubbed, and about half of the retail
script API is missing or a placeholder. That work is tracked in the port's own
repository, not here.

SS2's side is working end to end: a mission written as text compiles into the
game database and runs in the engine with its own units, waypoints, cameras and
script (`game/missions/m00_sandbox`).

---

## Risks and Open Questions

### Design Risks
- Stealth system complexity could overwhelm a solo/tiny team. Start with the
  stealth the original engine already has and expand from there.
- Multiple theaters multiply content requirements. May need to reduce to
  2 theaters for the first release.

### Technical Risks
- **Sequel mechanics need engine work.** Multi-state detection, disguises and
  distractions go beyond what scripts can do today. Each needs new engine
  functions, which depend on the engine port.
- **No new geometry yet.** Levels can only rearrange what the original shipped.
  Theaters the original never visited (for example North Africa or the Pacific)
  need new art and an engine change to load it.
- **Script API gaps.** Objectives, zone transitions and hints are placeholders
  in the port today, so mission flow (briefing, objectives, win and lose) has
  to be built on what is really implemented.
- **Load times.** Large levels take one to three minutes to load, which slows
  mission iteration.

### Market Risks
- Non-commercial release limits distribution options but also removes
  commercial pressure: the game ships when it's ready.
- Nival could revoke the license at any time (per license terms).
- Players must own the original game.

### Scope Risks
- Solo/tiny team building 20-30 missions across 4 theaters is ambitious.
- The "player's choice" sci-fi system essentially requires designing two
  parallel narrative arcs.

### Open Questions
- Which theaters can be built from the original's level art alone (England,
  Germany, Switzerland, Russia) and which need new art?
- How far can stealth go with script-only changes before engine work is needed?
- How does the campaign layer (theater selection, squad management between
  missions) map onto the original's scenario, chapter-map and base systems?

---

## MVP Definition

**Core hypothesis**: The destruction + stealth tactical loop is fun and
differentiated as a new, hand-crafted mission on the original engine, using
the original assets.

**Required for MVP**:
1. One fully destructible building with structural integrity simulation
   (provided by the engine)
2. Ballistic system with penetration through materials (provided by the engine)
3. Basic stealth (detection states, silent movement, line of sight)
4. Squad of 3-4 characters with action points and basic abilities
5. One complete playable mission (briefing → deployment → execution → extraction)
6. At least one building type and terrain set, composed from original assets

**Explicitly NOT in MVP** (defer to later):
- Multiple theaters (one theater is enough to validate)
- Conspiracy / sci-fi layer
- Full class system and progression
- Strategic between-mission layer
- Character relationships and personality
- Full weapon roster

### Scope Tiers (if time shrinks)

| Tier | Content | Features | Timeline |
| ---- | ---- | ---- | ---- |
| **MVP** | 1 mission, 1 building type, 4 characters | Destruction + ballistics + basic stealth | 3-4 months |
| **Vertical Slice** | 3 missions in one theater, 6 characters | Full class system, equipment, mission debrief | 6-8 months |
| **Alpha** | 10 missions across 2 theaters | Strategic layer, character progression, conspiracy hooks | 12-16 months |
| **Full Vision** | 25+ missions across 4 theaters | Full conspiracy, all classes, all weapons, polished | 18-24+ months |

---

## Next Steps

- [x] Choose the engine: original Silent Storm engine (ADR-0001)
- [x] Content pipeline: text sources compile into a running mission
- [ ] Get concept approval from creative-director
- [ ] Survey the original levels for usable mission locations (`tools/survey.py`)
- [ ] Build the MVP mission: briefing, objectives, extraction, win and lose
- [ ] Decide the first theater and its story
- [ ] Decompose concept into systems (`/map-systems`)
- [ ] Author per-system GDDs (`/design-system`)
- [ ] Plan first sprint (`/sprint-plan new`)
