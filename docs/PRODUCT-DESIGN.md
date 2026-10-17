# Product and design handoff

TradeOff has a responsive public homepage, a mission cockpit, and a usage guide. One set of source assets supports both the protected runtime and the public showcase.

## Visual direction

The supplied Figma canvas was inspected visually. The implemented interface takes its dark operational direction: navy surfaces, mint completion signals, compact monospace measurements and visible negotiation phases. It is an original implementation with measured product claims. The supplied Figma file was not modified because no callable Figma tools were available in this session.

Import `docs/assets/tradeoff-design-board.svg` into Figma by dragging the file onto the canvas. It contains editable vector shapes and text for the color system, landing-page composition and cockpit composition. It is a design handoff, not a Code Connect mapping or native auto-layout component library. The website source remains the authoritative responsive implementation.

| Token | Value | Use |
| --- | --- | --- |
| Background | `#0b1119` | Page canvas |
| Surface | `#111b27` | Panels |
| Raised surface | `#15212e` | Metrics and controls |
| Border | `#263443` | Separators |
| Primary text | `#edf2f5` | Headings and values |
| Secondary text | `#a0afbf` | Context and labels |
| Mint | `#8be4be` | Primary action and acceptance |
| Blue | `#a5c6f3` | Oracle and secondary data |
| Amber | `#efc58b` | Alternate supply and unresolved states |

Typography: system Segoe UI / Arial for prose; Consolas / Cascadia Code for measured data. Cards use 8–14px radii. Desktop page width is 1240px; mobile breakpoint is 760px. Workspace sidebar collapses into horizontal navigation. Forms keep visible labels; status is announced through a live region. Reduced motion and keyboard focus states are included.

## Product behavior

- Homepage: explanation, baseline allocation illustration, measured evidence, workspace and source links.
- Public workspace: five labeled recorded LinuxONE scenarios, real client inference, export, recorded verification, session history and reset.
- Protected workspace: token sign-in, new VM/local jobs, fresh server inference, real denied-access and audit checks, persisted history and reset.
- Guide: outcomes, local startup, SSH access, and interpretation limits.

No account signup, payment, manufactured privacy percentage, fake deployment telemetry, or unsupported hardware acceleration claim appears in the flow.
