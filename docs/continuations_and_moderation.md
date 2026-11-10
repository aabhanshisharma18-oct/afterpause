# D3 Continuations and moderation

A signed-in visitor submits a private proposal, first milestone, and intended materials on a visible exhibit owned by someone else. The creator sees it in Creator requests. The applicant sees it in My requests. Administrators can inspect proposals when reviewing a report.

| Record | States | Who can act |
| --- | --- | --- |
| Request | Pending, accepted, declined, closed, withdrawn | Creator decides; applicant withdraws |
| Continuation | Active, withdrawn, ended, completed | Active contributor may withdraw; creator ends or marks milestone reached |
| Update | Pending, approved, rejected | Active contributor submits; creator reviews |
| Report | Open, resolved | Signed-in member submits; administrator decides |

Acceptance locks the exhibit row before reading the current request and active slot. It creates one continuation, closes competing pending requests, updates the exhibit state and writes the timeline event in the same transaction. The database also enforces one active slot per exhibit. Duplicate form tokens are recorded inside the write transaction. SQLite uses an immediate write transaction for the local quick start; the MySQL tests exercise row locking on InnoDB.

Progress requires a screenshot and the next step. A private pending update can be seen by its author, the creator and authorised moderation. Approval creates a public event with the contributor’s credited name, date, screenshot and optional unverified external link. Rejection is private. Ending or withdrawing keeps approved work and closes pending updates without publishing them. Completing a milestone requires approved work and opens the way for another chapter.

Reports are private. A report flags an exhibit without hiding it. Moderators may resolve a report, hide the exhibit, or unhide it with an audit note. Visibility changes never delete exhibit or continuation records. Owners can appeal a moderation restriction from My exhibits.

The tests exercise concurrent acceptance, rollback after database writes, private feedback and media, moderation permissions, withdrawal, and reopening after a milestone. Use the [demo script](demo.md) for the live workflow.
