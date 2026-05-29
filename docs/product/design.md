# CultureGraph design note

## Interaction philosophy

CultureGraph should **not** embed ScratchJr in the MVP. Instead, it borrows **ScratchJr-inspired interaction patterns** — visual, tap-driven, and cause-and-effect clear — applied to cultural exploration rather than block coding.

The tone stays reductive and museum/archive-inspired: playful when it helps learning, never noisy or gamified.

## Patterns to borrow

| Pattern | In CultureGraph |
|--------|------------------|
| Visual storytelling | Artwork context delivered as short, scannable cards — not walls of text |
| Tap-to-reveal context | Pins and cards that open detail on tap; no hidden navigation |
| Scene-by-scene explanations | Research and context broken into ordered steps (summary → history → details) |
| Simple image annotations | Percentage-based pins on the artwork image |
| Playful but minimal guided exploration | Gentle prompts (“What did you notice here?”) without tutorials or mascots |
| Visible cause/effect | Tap pin → see note; generate research → see structured cards appear |
| Low-friction creative learning | Progressive forms, bottom sheets, one-thumb mobile flows |

## MVP implementation

What ships now maps directly to these patterns:

- **Tappable annotation pins** on artwork images (`/artworks/[id]/annotate`)
- **Guided visual story cards** for artwork context (research draft: summary, historical context, visual elements, questions, suggested annotations)
- **AI-suggested annotation points** via the research endpoint’s `suggested_annotations`
- **Mobile-first tap interactions** — 44px+ targets, bottom sheets, sticky action bars, fit-to-width image viewer

Do not add block editors, sprite runtimes, or embedded ScratchJr iframes in MVP.

## Future: Story Mode

**Story Mode** (post-MVP): an artwork becomes a simple interactive explainer — a sequence of scenes inspired by ScratchJr / OctoStudio-style scene ordering.

Concept sketch:

1. **Scene 1** — full artwork or cropped region with one annotation pin highlighted
2. **Scene 2** — tap advances to the next pin or context card
3. **Scene 3** — related question or historical beat
4. … linear or lightly branching path through the work

Implementation would reuse existing pin coordinates and research card content; new UI would add scene order, transitions, and optional auto-advance — still minimal, still mobile-first, still no embedded ScratchJr.

## Design constraints (unchanged)

- Reductive layout, conventional hierarchy, clean typography
- Off-white background, restrained motion
- No gradients, glassmorphism, neon, or dashboard clutter
- Stacked cards on mobile; multi-column only on desktop
