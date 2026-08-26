---
name: website-designer
description: Design and implement distinctive marketing, editorial, portfolio, documentation, and landing-page websites; do not use for dense product-app screens or design-only critique.
---

# Website Designer

Create a production-ready website whose visual identity grows from the subject, audience, and page goal. Treat copy, layout, typography, imagery, and motion as one system.

## Form the direction

Before building, pin down the audience, the page's single job, and the subject's real-world materials, language, imagery, and cultural references. Use those inputs to define:

- one visual thesis for the page;
- one memorable signature element that belongs to this subject;
- three likely template defaults to avoid;
- a compact palette of named colors with exact values;
- distinct display, body, and optional utility type roles;
- the layout logic and responsive behavior;
- one purposeful motion moment, or an explicit decision to keep the page still.

If the same direction could fit an unrelated company after swapping the logo, revise it. Take one justified aesthetic risk and spend the rest of the page on restraint and precision.

## Design the narrative

Make the hero a thesis rather than a generic headline-plus-gradient container. Start with the most characteristic content, image, demonstration, or interaction available.

Build a reading sequence with clear pacing. Structural devices such as numbering, dividers, labels, and grids must encode a real relationship in the content. Vary density intentionally: keep related items close and separate major ideas with meaningful space.

Write concrete copy from the visitor's perspective. Prefer plain verbs, specific claims, and consistent action names. Include real empty, error, loading, and confirmation language when the page contains interactive flows.

## Implement in the existing stack

Inspect the project's components, tokens, fonts, assets, and styling conventions before adding new ones. Reuse them when they support the direction; extend them coherently when they do not. Avoid parallel button, spacing, or color systems.

Use semantic HTML and resilient layout primitives. Ensure:

- a logical heading outline and landmarks;
- visible keyboard focus and complete keyboard paths;
- sufficient contrast and non-color status cues;
- responsive composition without clipped content or horizontal scrolling;
- touch targets appropriate to the target device;
- preserved aspect ratios to prevent layout shift;
- useful metadata and social previews when the page will ship publicly;
- graceful operation without decorative animation.

Typography should carry personality without sacrificing reading. Keep body measure comfortable, use deliberate wrapping for headings, use tabular numerals for changing data, and load only the font faces actually required.

## Use motion sparingly

Choose one orchestrated moment over scattered effects. Use motion only for orientation, feedback, continuity, explanation, or a rare moment of delight. Respect reduced-motion preferences and avoid moving text or data the visitor is trying to read.

## Verify

Render the website when tools permit. Inspect at representative mobile and desktop widths, with realistic long and short content, keyboard navigation, focus states, loading/error/empty states, and reduced motion. Check for overflow, layout shift, unreadable type, weak hierarchy, and inconsistent tokens. Report anything not verified.
