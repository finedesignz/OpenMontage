# Motion Doctrine - Meta Skill

## When to Use

Consult this before and during any motion-led stage - scene planning and editing
for animated explainers, motion graphics, kinetic typography, and screen-demo overlay
passes. It is the shared quality bar for how motion should feel across OpenMontage's
motion-led pipelines.

This is a **reference**, not a monolith. It is a compact core (the 11 Laws, the
pre-ship test, the pre-flight checklist, the one-line TL;DR) with deeper reference
sections below. A stage director skill points at just the core and names the laws that
bite at its stage; it does NOT copy the doctrine body. There is one source of truth for
the doctrine, and it is this file.

The laws are engine-neutral. Where a law couples to OpenMontage's Remotion runtime, the
runtime detail is called out explicitly (Law 11, and the easing note in the reference).

---

## Core

### The 11 Laws (memorize)

1. **One idea per beat. Cut fast.** A tight motion piece averages roughly 1.5 seconds
   per scene. Each visual lands ONE word or concept and moves on. If a scene says two
   things, split it into two scenes.
2. **Negative space is the design.** Keep most of the frame quiet. One focal element
   at a time; let the composition breathe. A busy frame reads as noise, not premium.
   Restraint is the point, not decoration.
3. **Depth and light read as premium, not flat color.** Soft halos, gradients on type,
   vignettes, subtle depth cues make a piece look expensive. Flat-lit, evenly-filled
   frames read cheap. The piece should feel lit, not merely colored.
4. **The camera never sleeps.** Even on a "still" frame something drifts - a slow
   parallax, a breathing vignette, a gentle zoom. Fully static is death. Add motion to
   any beat that would otherwise sit frozen.
5. **Every cut rides a motion element.** Transitions carry energy AND hide the seam - a
   streak, a whip, a morph, a slide, a recolor. Bare hard cuts feel cheap; a
   motion-bridged cut feels expensive. Fire the transition element AT the cut, not
   before it.
6. **Recurring motifs carry meaning.** A visual element that returns later - a logo
   mark, a recurring shape, a color that reappears - builds continuity and identity. A
   thing that appears once and never returns wastes its setup.
7. **Palette is symbolic, not decorative.** Each color owns one concept. Do not add a
   color because it looks nice - assign it a meaning. If you cannot name what a color is
   carrying, you have not earned it.
8. **Type is a character.** Words can scale, compress, morph, and glow. Typography often
   drives most of the storytelling; a text-only beat can be the strongest beat. Make
   type act, do not just fade it in.
9. **Hold the hero shot.** Speed earns stillness. A reveal or a closing card holds far
   longer than a mid-section beat - kinetic density collapsing into calm is the payoff.
   Kinetic to calm reads as catharsis.
10. **One unifying texture across everything.** A single spine ties the piece together -
    a grid, a grain, a consistent frame treatment - present even when it is nearly
    invisible. Without a unifying texture you do not have a piece, you have loose clips.
11. **Every timeline fills its slot.** A composition must animate for its entire
    declared duration or its tail goes dark. In OpenMontage's Remotion runtime,
    `calculateMetadata` sets `durationInFrames = ceil((maxOutSeconds + 1) * 30)` at
    30fps - it pads the slot by +1 second, so a 12s timeline renders 13s. If a scene's
    animation ends before its declared slot, the tail black-frame-flashes. Rule: every
    composition's timeline must fill its declared duration, and trim the final mp4 to
    the exact target with `ffmpeg -t`. (This is the OpenMontage equivalent of the
    generic "timelines must fill their slots" law; the runtime specifics are Remotion's,
    documented in project memory `remotion-render-gotchas.md`.)

### The Cut-This-In-Half Test (pre-ship)

Before you ship any motion piece, ask, per beat:

1. **Could I cut this scene in half?** If yes, do it.
2. **Is this color carrying a meaning?** If no, kill it.
3. **Does the camera move during this beat?** If no, add drift.
4. **Where is the motion on the transition?** If the cut has none, add a bridging
   element.
5. **Will the viewer see this visual element again later?** If no, can I make it a
   callback?
6. **Does the type scale or act during its reveal, or just fade in?** Fading in is the
   lowest-effort move. Make it act.
7. **What is the negative space doing?** If most of the frame is busy, you are
   over-designing.
8. **Is this beat ONE idea?** If you cannot summarize it in two words, you packed in too
   much.
9. **What is the unifying texture across all scenes?** If you do not have one, you have
   clips, not a piece.
10. **Where does the viewer rest?** Name the breathing moments. If there are none, build
    them in.

### Pre-flight Checklist (before calling any motion piece "done")

- [ ] **Average scene length is short** in the mid-section (roughly 2s or less); intro
      and outro may hold longer.
- [ ] **No dead air over ~1s** anywhere except deliberate hold moments.
- [ ] **Every transition uses motion** (streak, morph, slide, recolor) - no bare hard
      fades.
- [ ] **Palette is small** (about 5 active hues or fewer across the whole piece), each
      with a meaning.
- [ ] **Text uses depth treatment** (gradient plus glow or equivalent) - no flat,
      unlit type where the piece calls for polish.
- [ ] **The unifying texture is present in most scenes** (grid, grain, or consistent
      frame treatment).
- [ ] **A depth or vignette layer sits over most scenes** - do not ship a flat-lit
      composition.
- [ ] **At least one callback** - a visual element that returns later.
- [ ] **The outro holds** (several seconds of stillness after the kinetic act).
- [ ] **Visual verification done** - extract frames, open them, and confirm: no cropped
      faces, no text overflow, no beat landing on the wrong word, no broken transitions.
      Lint passing is not design working. VIEW THE FRAMES.
- [ ] **Every composition timeline fills its declared duration** (Law 11) - no scene
      ends before its slot, and the final mp4 is trimmed to the exact target with
      `ffmpeg -t` to shed the +1s Remotion tail.
- [ ] **Motion timing snaps to frame boundaries** - at 30fps, ends land on multiples of
      1/30s (0.0333, 0.0667, 0.1, ...). Steep-tail easings visibly alias at sub-frame
      boundaries.

### TL;DR (the philosophy in one sentence)

> One idea per beat, lit not flat, kinetic not still, callbacks not novelty, hold the
> hero and breathe the outro - the unifying texture is always under everything, every
> timeline fills its slot, every timing end snaps to a frame boundary, and every cut
> hides inside a motion element.

---

## Reference

Read this when you need the working numbers behind the laws. The core above is enough
for most scene-planning and editing decisions.

### Easing by Purpose (engine-neutral)

Easing names below are the common GSAP family names, used here as shorthand for a curve
SHAPE. In OpenMontage's Remotion runtime, reach for the equivalent `spring()` or
`Easing.bezier(...)` / `Easing.out(Easing.cubic)` curve - the shape is what matters, not
the API.

| Purpose | Curve shape | Typical duration |
|---|---|---|
| Word or element reveal (slide-in) | strong ease-out (`expo.out`) | 0.20-0.33s |
| Generic element enter | ease-out (`power2.out`) | 0.2-0.5s |
| Generic element exit | ease-in (`power2.in`) | 0.2-0.33s |
| Beat-to-beat bridge, exit side | ease-in (`expo.in` / `power2.in`) | 0.2-0.33s |
| Beat-to-beat bridge, entry side | ease-out (`expo.out` / `power2.out`) | 0.5-1.0s |
| Camera or scroll pan between stops | ease-in-out (`power2.inOut`) | 1.2-2.3s |
| Linear hold after an entry | linear (`none`) | 0.4-0.65s |
| Bouncy settle | slight overshoot (`back.out(1.2-1.5)`) | 0.3-0.5s |
| Click compress | sharp ease-in (`power4.in`) | ~0.07s |
| Click release overshoot | strong overshoot (`back.out(3)`) | ~0.30s |
| UI settle overshoot | elastic settle (`elastic.out(1, 0.3-0.4)`) | ~0.20s |
| Continuous rotation | linear (`none`) | full beat |
| Breathe / drift | ease-in-out yoyo (`sine.inOut`) | 2-4s, repeating |

**Velocity match at the seam.** When an eased move hands off to a hold or to a second
move, make the end-velocity of the first equal the start-velocity of the next. The eye
reads any velocity discontinuity as a stall. In OpenMontage this shows up in screen-demo
**eased scrolls** and **overlay cursor easing**: when an eased page scroll settles into a
hold, or a faux-cursor move arrives at its target, tune the curve so it does not visibly
brake. Derive the matching curve once per seam.

**Stagger values (starting points):**

- Sweep across words: about 0.04s per word.
- Grid ripple: about 0.02s per column, about 0.004s within a column.
- Multi-line reveal (e.g. code or list lines): about 0.06s per line.
- Sequential emphasized items: 0.08-0.12s explicit delays (individual eases, not a
  uniform stagger).

**Discipline:** declare every move's ease and duration explicitly. Inherited defaults
cause bugs that are harder to diagnose than a few verbose declarations.

### Pacing Discipline

- **Default scene length:** roughly 1.0-2.0 seconds. If a scene runs longer, it should
  be a hero moment or the outro.
- **Reveal cadence:** a new visual element every 0.3-0.6s within a scene. No dead air
  over ~1s mid-piece.
- **Word-reveal stagger:** 0.3-0.4s per word for narrative reads, 0.5-0.6s for dramatic
  single-word emphasis.
- **Transition duration:** 0.3-0.4s for a whip or streak. Faster feels glitchy; slower
  loses energy.
- **Hold durations:** a reveal or logo lands over about 1.5-2s; the closing card holds
  about 4-6s (the longest single shot in the piece is usually the outro); a section
  headline gets about 1-1.5s of read time after it is fully revealed.
- **The breathing rule:** after every ~7-8s of kinetic density, give the viewer about a
  1s rest beat (a reveal, a slow hero shot, the outro hold).

### Transition and Motion Vocabulary (engine-neutral)

Named moves to reach for. Each is described by intent, not by any one engine's API -
build it with whatever your runtime provides.

| Move | What it does |
|---|---|
| **Light-streak whip** | A glowing, blurred bar zips across the frame in ~0.3-0.4s. Fire it AT the cut so its brightness masks the seam. Default energy-beat transition. |
| **Camera dolly through type** | Text grows large and fades to zero at its peak - feels like passing through a 3D word. |
| **Ghost reveal** | The next element starts entering while the previous is still leaving (a short overlap), for a continuous read. |
| **Object morph drift** | Element A shrinks and drifts off one vector while element B grows in from the same vector; a streak hides the swap. |
| **Reveal spin** | A 3D rotate from edge-on to face-on with a slight settle bounce. |
| **Crystallize to mark** | An element shrinks and translates into a wordmark or logo position while the mark fades up, both landing on the same point. |
| **Energy pulse along a path** | A glow travels a connector to "activate" a node at the far end. |
| **Recolor with no cut** | The same composition shifts palette via variables in a single move - two related ideas on one shot, no scene change. |
| **Slide-up reveal** | A device or panel enters from the bottom edge with a headline settling in above it. |
| **Wheel plus side-panel** | A central element rotates while text panels slide in from left or right. |
| **Floating cluster drift** | Three or more objects gently bob and drift continuously (sine yoyo, randomized offsets). |
| **Shimmer sweep on hold** | A single glint passes over a held logo every few seconds to keep a still frame alive. |
| **Vignette breath** | Vignette opacity wobbles slowly to keep a "still" frame from freezing. |
| **Velocity-matched vertical whip** | The default adjacent-beat transition - the outgoing beat rides up with blur, the incoming beat rises from below with matching blur, same direction and velocity matched at the seam. |
| **Faux-cursor click** | A short sequence that sells a UI interaction - cursor compress, target compress, ripple, cursor release, target overshoot, settle. The cursor's transform origin MUST sit at the click-tip pixel. |

**Transition selection:**

- Default cut between energetic scenes: light-streak whip.
- Text into 3D space: cinematic zoom-through.
- One object becoming another: cross-warp morph.
- Two related ideas on the same shot: recolor with no cut.
- Product or panel intro: slide-up reveal.
- Brand landing: crossfade with a brief bright pulse.
- Major act break: flash through white.
- Cut on action: align the next scene's start to a whip or streak's peak frame.

### Anti-patterns (what NOT to do)

- Centered, axis-aligned, motionless text fades. The lowest tier - always add scale,
  blur, or directional energy.
- Bare hard cuts between scenes. Every cut needs a bridging motion element.
- Flat, unlit text on a flat background. Depth treatment (gradient plus glow) costs
  nothing and looks far more expensive.
- Six or more colors across the piece. That is decorating, not communicating.
- No callbacks. An element that appears once and never returns wastes a setup.
- An outro that ends on the last beat. Hold the closing card for several seconds.
- Scenes that try to say two things. Split them.
- Static backgrounds. Every background needs at least one slow-moving element -
  parallax, drift, or a breathing vignette.
- Treating grain or vignette as decoration. They are the unifying texture; they go on
  every scene, every time.
- Shipping without rendering a draft and looking at it. Lint passing is not design
  working. VIEW THE FRAMES.
- Unseeded randomness inside a render loop. Renders must be deterministic frame to
  frame; use seeded values or harmonic hashes.

---

## Neutral Illustrations

The laws are content-agnostic. Two examples to make them concrete:

- **A product demo.** One feature per beat, cut fast. The product mark returns at the
  open and the close (callback). One accent color owns "the value"; everything else is
  quiet. The closing card holds while everything else stops.
- **A report walkthrough.** Each figure is a single idea; a stat scales in rather than
  fading. An eased scroll carries the eye between sections (velocity matched at each
  stop). A consistent grid under every section is the unifying texture. The final
  takeaway holds in stillness.
