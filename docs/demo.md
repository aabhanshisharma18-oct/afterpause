# Afterpause classroom demonstration

Run `bash scripts/demo.sh` against a separate demo database and then `APP_ENV=demo bash scripts/dev.sh`. Use two browser profiles for the creator and contributor and a private window for an anonymous visitor. All seeded exhibits and accounts are fictional. The password is the one chosen when running the seed.

1. Visit the entrance, enter the museum, and filter Unfinished Interfaces by CSS. Open Campus Guide, point out the original work, permissions, and concrete next step.
2. As `creator@example.test`, use Exhibit a project to create a private draft. Enter its intention and story, reopen it from My exhibits, upload a screenshot, declare permissions, and publish after preview. The visitor can now open its public URL.
3. As `contributor@example.test`, open the exhibit and choose Continue this idea. Propose a keyboard-friendly mobile menu and a testable milestone. In the creator dashboard, accept the proposal.
4. As contributor, submit an update with a prepared screenshot and the next action. Refresh the public exhibit to show the update is still private. As creator, approve it. Refresh again to show the original and new credits, then compare the two screenshots.
5. Report an attribution concern. In the `admin@example.test` session, hide the exhibit with a private audit note. Check the anonymous URL and search, then unhide it. Show that the approved chapter remains.
6. Restart the application. Reopen the public exhibit and check its screenshot and timeline. For the transaction and backup evidence, see [verification](verification.md).

## Seeded exhibits

| Exhibit | Room | Demonstration state | Media |
| --- | --- | --- | --- |
| Campus Guide | Unfinished Interfaces | Open | Existing generated map concept |
| Reading Room | Unfinished Interfaces | Milestone reached and approved chapter | Existing generated bookshelf concept and labelled search mockup |
| One More Level | Playable Someday | Active continuation | Existing generated game concept |
| Pocket Forecast | Unfinished Interfaces | Private pending request | Generated geometric demo mockup |
| Lantern Relay | Playable Someday | Private declined request | Generated geometric demo mockup |
| Recipe Drawer | Useful Little Tools | Withdrawn continuation | Generated geometric demo mockup |
| Focus Trace | Useful Little Tools | Open report | Generated geometric demo mockup |
| Studio Index | Useful Little Tools | Open | Existing generated workspace illustration |
| Pattern Press | First Experiments | Open | Generated geometric demo mockup |
| Sidewalk Sounds | First Experiments | Open; no image fallback | No image |
| Private demo draft | Not public | Draft | No image |

The existing assets are from the repository’s static concept. Newly seeded images are rendered by the demo script. They illustrate ideas; they are not screenshots of functioning applications or evidence of real activity.
