---
name: motion-designer
description: Design and implement purposeful UI motion, microinteractions, transitions, animated graphics, SVG/Lottie work, scroll sequences, and coherent motion systems across web and apps.
---

# Motion Designer

Use motion to communicate feedback, spatial continuity, state, causality, explanation, or rare delight. A good outcome may be a decision not to animate.

## Gate the animation

First assess frequency and purpose. Operations used constantly, especially keyboard-driven ones, should be instant. Frequently repeated interactions deserve only near-imperceptible feedback. Save expressive motion for occasional, explanatory, or celebratory moments.

Name one purpose before continuing:

- confirm input;
- preserve spatial context;
- reveal a state change;
- bridge a discontinuity;
- explain a relationship;
- add delight where it will remain rare.

If none applies, use a static affordance or instant state change.

## Choose the motion language

Define the relationship between mass, distance, timing, and hierarchy. Large surfaces should not move like tiny controls. Entrances decelerate, exits remain decisive, and on-screen rearrangements preserve continuity. Repeated elements may stagger only enough to expose order without delaying use.

For character animation or animated graphics, apply anticipation, follow-through, arcs, overlap, staging, and exaggeration selectively. Preserve legibility and brand tone; do not apply every animation principle to every element.

## Choose the cheapest capable tool

Follow the project's existing stack and tokens. Prefer:

- CSS transitions for hover, press, color, and simple state changes;
- CSS entry animation or the Web Animations API for deterministic sequences;
- the existing motion library for layout transitions, gestures, springs, exits, and interruptible values;
- SVG or Lottie for scalable authored graphics;
- a timeline or video tool for frame-accurate narrative work.

Do not add a library for a simple fade. Do not hand-roll an accessible component merely to animate it.

## Implement for feel and performance

For UI motion, favor compositor-friendly transforms and opacity. Avoid animating layout properties unless the interaction genuinely requires it and measurement shows it is safe. Never use `transition: all`; name the properties.

Use a shared duration and easing scale. As a starting range, press feedback is roughly 100–160 ms, small overlays 125–200 ms, menus 150–250 ms, and larger modal or drawer transitions 200–500 ms. Most routine UI motion should finish within 300 ms. Choose springs for gesture-driven, reversible, or velocity-carrying motion, and keep bounce restrained unless playfulness is intentional.

Animations triggered in quick succession must retarget from their current state. Preserve velocity for gestures. Exit toward the origin implied by the entrance or dismissal gesture. Never block input while decorative motion finishes.

## Accessibility and device behavior

Ship a reduced-motion treatment with every implementation. Keep opacity or color feedback when useful, but remove parallax, large spatial travel, and autoplay under reduced motion. Gate hover-only motion to devices that truly support hover and a fine pointer.

Provide pause or stop controls for persistent autoplay. Avoid flashes, rapid oscillation, and moving data a person is reading or manipulating.

## Verify

Test interruption, reversal, rapid repetition, cancellation, route changes, background/foreground transitions, and cleanup on unmount. Inspect on representative low- and high-performance devices when possible. Verify reduced motion and touch behavior. Slow the sequence down to inspect spacing and continuity, then judge it again at real speed. Report the purpose, tool, timing, easing or spring, and anything not verified.
