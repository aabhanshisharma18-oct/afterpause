# Afterpause classroom demonstration

Run `bash scripts/demo.sh` against a separate demo database and then `APP_ENV=demo bash scripts/dev.sh`. Use two browser profiles for the creator and contributor and a private window for an anonymous visitor. All seeded exhibits and accounts are fictional. The password is the one chosen when running the seed.

1. Sign in as `creator@example.test`. In **My exhibits**, open **BorrowBox — Campus Equipment Library** and choose **Preview and publish**, then **Publish exhibit**.
2. Open a second session as `contributor@example.test`. In **Explore**, choose **Useful Little Tools** and search for `BorrowBox`. Open the exhibit and select **Continue this idea**. Propose a search box and availability filters. Use “Show only presentation gear that is available now” as the first milestone and “The original BorrowBox mockup and its fictional inventory” as the materials.
3. After submitting, open **My requests** and show the pending status. Select **Edit proposal**, add a keyboard check to the milestone, and save. Back in the creator session, open **Creator requests** and accept the current proposal.
4. As contributor, return to BorrowBox and select **Submit progress**. Use “Added search and availability filters” as the title. Describe how the revised mockup shows two available presentation items. Enter “Test the empty results screen” as the next step. Upload the [revised mockup](../app/demo_assets/borrowbox-after.png) and enter “Search and availability filters showing two presentation items” as its image description. The form previews the screenshot before you submit.
5. Refresh the public exhibit as a visitor to show that the update stays private while it awaits review. As creator, open **Updates awaiting review** and approve it. Refresh the exhibit and show both credits, the new chapter, and the original and revised images in **Compare the original and the latest contribution**.
6. To demonstrate moderation, report an attribution concern. In the `admin@example.test` session, hide the exhibit with a private audit note. Check the anonymous URL and search, then unhide it. Show that the approved chapter remains.
7. Restart the application. Reopen the public exhibit and check its screenshot and timeline. For the transaction and backup evidence, see [verification](verification.md).

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
| BorrowBox | Useful Little Tools | Ready to publish (private draft) | Original equipment catalogue mockup, with a separate revised image for the contributor |
| Private demo draft | Not public | Draft | No image |

The existing assets are from the repository’s static concept. Newly seeded images are rendered by the demo script. They illustrate ideas; they are not screenshots of functioning applications or evidence of real activity.
