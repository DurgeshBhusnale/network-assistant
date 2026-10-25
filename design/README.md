# Design reference

- `tokens.css` — design tokens. Wire them into Tailwind in Sprint 0; components use tokens only.
- `screens/*.dc.html` — reference markup exported from the claude.ai Design canvas "Networking Assistant App Screens" (390 × 844 phone artboards). They rely on the canvas runtime (`support.js`, `<x-dc>`, `<sc-for>`), so **they don't render standalone**. Read them as a spec: copy structure, spacing, colours and copy into React components. People and numbers in them are sample data.

| File | Screen |
|---|---|
| `Main.dc.html` | Today (home) |
| `Draft.dc.html` | Draft sheet |
| `Person.dc.html` | Person |
| `Replies.dc.html` | Did they reply? |
| `Progress.dc.html` | Goal progress |
| `Goal.dc.html` | Set your goal (onboarding 1/3) |
| `Import.dc.html` | Bring in your people (onboarding 2/3) |
| `Capture.dc.html` | Voice capture + confirm cards |
| `Upgrade.dc.html` | Upgrade / paywall |
| `WhatsApp.dc.html` | WhatsApp bot conversation design (not an app screen) |

The live canvas (editable, commentable) is in the founder's claude.ai account. When the design changes there, re-export the changed files here.
