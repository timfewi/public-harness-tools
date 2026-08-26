---
name: design-system-designer
description: Create, extend, document, or migrate design systems covering tokens, typography, color, spacing, motion, accessible component contracts, variants, and governance.
---

# Design System Designer

Build a system that makes coherent product decisions easier. Start from evidence in the existing product; do not create a parallel token or component universe.

## Inventory before invention

Inspect current styles, variables, components, variants, icons, layouts, and usage patterns. Identify repeated values, near-duplicates, undocumented exceptions, accessibility gaps, and places where implementation diverges from design.

Separate deliberate brand expression from accidental inconsistency. Preserve behavior and visual contracts that users already rely on unless the brief explicitly calls for migration.

## Define the foundations

Use a layered token model:

1. primitive values such as color ramps and raw dimensions;
2. semantic roles such as background, foreground, border, accent, success, warning, and danger;
3. component tokens only where a component needs independent control.

Names should express purpose, not a single current appearance. Define modes and themes through semantic mappings rather than duplicated components.

Establish compact systems for:

- typography roles, sizes, weights, line heights, and numeric features;
- spacing based on a small unit and meaningful context steps;
- radius and border treatments;
- surface elevation using one coherent depth strategy;
- icon sizes and stroke behavior;
- motion durations, easings, and reduced-motion alternatives;
- breakpoints or container behavior appropriate to the product;
- focus, selection, disabled, and high-contrast states.

Measure rendered color pairs and record contrast requirements. Do not rely on color alone for state.

## Specify component contracts

For every component, define anatomy, purpose, semantic element or primitive, variants, sizes, states, content rules, keyboard behavior, focus behavior, accessible name and description, responsive behavior, and composition boundaries.

Prefer native controls, then established accessible primitives. A visually complete component without correct keyboard, focus, and announcement behavior is incomplete.

Keep variants orthogonal. Do not encode arbitrary page-specific combinations into the core API. Demonstrate realistic content, overflow, localization, empty/error/loading states, and composition with adjacent components.

## Plan adoption

Map old values and components to the new system. Make migration incremental where possible, with compatibility aliases only when they have a retirement plan. Identify breaking changes, owners, codemods or mechanical replacements, visual-regression coverage, and documentation updates.

Write guidance as decisions and examples, not as a catalog of values. Explain when to use a token or variant, when not to, and which escape hatch is allowed.

## Verify

Check token references for cycles and orphan values. Render component states across themes, widths, text expansion, zoom, keyboard navigation, forced colors, and reduced motion where applicable. Run available accessibility and visual-regression checks. Report coverage and unresolved exceptions explicitly.
