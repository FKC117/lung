# Conservative cross-source record reconciliation

Deterministic local evidence and provider records retain independent stable identities and original quotes. No record is silently merged, deleted or assigned an invented consultation ID. Explicitly different event dates preserve repeated events.

When both sources share populated canonical fields in the same collection, identical shared values trigger a possible-overlap decision. Different findings anchored to the same explicit date trigger a conflict decision. Without a reliable shared anchor, the system does not infer a contradiction. Provider source facts become initially unresolved, and grouped exceptions link both record identities.

Reviewers may confirm that retained records describe distinct events using existing checked field decisions, or remove a confirmed duplicate and explicitly exclude its original facts with reasons. Decisions use the authenticated saved-revision API. Immutable source ledgers remain unchanged; removing issue text does not waive original unresolved fact coverage. No fuzzy deduplication or model self-confidence grants acceptance.

This conservative approach favors visible review exceptions over silently dropping repeated clinical events. Production accuracy evaluation remains separately gated.
