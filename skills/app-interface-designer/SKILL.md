---
name: app-interface-designer
description: Design and implement task-focused product interfaces for web, mobile, and desktop apps, including dashboards, SaaS tools, admin panels, settings, and data-heavy workflows.
---

# App Interface Designer

Design software around the user's task, not around a dashboard template. Navigation, data presentation, controls, states, and visual hierarchy are all product decisions.

## Start with the work

Name the actual person, their context, and the verb they came to perform: approve a payment, find a failed deployment, schedule a visit, compare records, or complete another concrete task. Decide how the interface should feel using specific qualities such as workbench-dense, calm and clinical, or warm and guided.

Explore the product domain before drawing screens:

- list its characteristic concepts, objects, and vocabulary;
- identify colors and materials that belong naturally to that world;
- define one structural or interaction signature unique to the product;
- name the obvious structural and visual defaults to avoid.

The focal action or information should be unmistakable. If every card, number, or control has equal visual weight, redesign the hierarchy.

## Shape the flow

Map the happy path and the consequential branches before styling. Include loading, empty, partial, validation, error, offline, permission, destructive-action, and success states where relevant. Preserve user work and make recovery explicit.

Navigation must communicate location, available destinations, and the relationship between areas. Data displays must explain meaning, comparison, trend, or required action rather than merely placing a large number in a box.

Choose density deliberately and repeat it. Use tighter spacing for frequent expert workflows and more guidance for occasional or high-risk tasks. Group by proximity, reveal complexity progressively, and keep primary actions stable across the flow.

## Build from the product system

Inspect existing primitives, components, tokens, icons, and platform conventions first. Prefer, in order:

1. native platform controls when they express the behavior;
2. the project's accessible primitives and components;
3. a trusted headless primitive already in the stack;
4. a custom behavior only when the complete keyboard, focus, and state contract can be delivered.

Use semantic tokens rather than isolated values. Establish clear text tiers, a consistent spacing unit, a small radius scale, and one coherent depth strategy. Use tabular numerals for tables and changing values. Align numeric columns by meaning, not decoration.

## Interaction and accessibility

Every pointer action needs a keyboard path. Use native names, roles, states, labels, and error associations. Keep focus visible, restore it after overlays, avoid positive `tabindex`, and ensure touch targets do not overlap.

Motion should confirm actions, preserve spatial continuity, or clarify state. Frequent and keyboard-driven operations should be instant or nearly so. Reduced motion must remove spatial movement while retaining necessary feedback.

Adapt the information architecture to narrow screens instead of merely shrinking it. Test zoom, text growth, localization expansion, long identifiers, and both sparse and dense datasets when relevant.

## Deliver and verify

Implement the requested screens or components in the existing stack. Verify the complete primary flow, representative edge states, keyboard order, accessible names, focus return, responsive behavior, and visual consistency. Render on target device sizes when possible and report any unverified behavior.
