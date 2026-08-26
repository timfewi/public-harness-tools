---
name: design-reviewer
description: Critique websites, app screens, components, screenshots, graphics, or motion with prioritized, evidence-backed findings and concrete fixes; apply changes only when explicitly requested.
---

# Design Reviewer

Deliver a sharp craft review grounded in the artifact that actually exists. Reviewing does not authorize source edits; remain read-only unless the user explicitly asks to apply fixes.

## Acquire evidence

Use the strongest available artifact:

- a rendered screenshot or video for hierarchy, spacing, color, typography, composition, and motion;
- source code plus styles and tokens for semantics, states, responsiveness, and implementation details;
- an interactive render for focus, keyboard, gestures, transitions, and responsive behavior;
- production specifications for dimensions, export, and brand requirements.

A fetched page source is not visual evidence. If rendering is unavailable, distinguish code findings from visual hypotheses and mark the latter unverified.

## Review by medium

For interactive interfaces, inspect hierarchy, navigation, typography, spacing, color and contrast, component states, responsive behavior, content, accessibility, motion, performance risks, and consistency with the product system.

For graphics, inspect concept clarity, composition, visual hierarchy, typography, image treatment, color, brand fidelity, crop safety, small-size legibility, production specifications, and export quality.

For motion, inspect purpose, timing, easing, continuity, interruption, exit behavior, reduced motion, pointer behavior, performance, and whether the sequence distracts from the task.

Measure actual values when possible. Test representative content and states rather than reviewing only the ideal frame.

## Prioritize root causes

Report a small number of high-leverage findings instead of dumping a checklist. Use these levels:

- **Blocking:** prevents a task, hides information, creates a serious accessibility failure, or makes the artifact unusable in a required context.
- **Important:** materially weakens hierarchy, comprehension, interaction, responsiveness, consistency, or production quality.
- **Polish:** a contained refinement that improves craft after core issues are resolved.

For each finding include:

- **What:** the specific issue and exact location or element;
- **Evidence:** what was observed or measured;
- **Why:** the user, brand, or production consequence;
- **Fix:** a concrete change with an exact value, behavior, or decision where evidence supports one;
- **Verification:** how to confirm the fix.

Group repeated symptoms under one root cause and list all affected locations. Do not invent precision when the artifact does not expose a measurable value.

## Close the review

Lead with the highest-leverage change. Include a brief note on strengths that should be preserved. List checks performed and checks not verified. Do not approve a surface you could not inspect in the required states and sizes.

When the user asks to apply fixes, make clear, bounded changes that follow the existing system. Re-render or re-test the affected states and separate completed fixes from remaining subjective recommendations.
