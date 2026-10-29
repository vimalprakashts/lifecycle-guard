---
type: llm
weight: 1
---

Control case: none of the seven gaps planted in the other cases exists in this fixture. Fail only if the
review asserts that one of these EXISTING things is missing or wrong:
1. customers cannot see their refunds or the rejection reason;
2. the existing "Refunds waiting for review" tile goes to a generic or unfiltered page;
3. the order number in the refunds table is not a link to the order;
4. the spec's failure cases or acceptance criteria are vague or generic;
5. the admin has no way to reject a refund at all;
6. the refund presets/max can exceed the amount paid on that order;
7. a new or duplicate top-level refund settings page or tab was added.
These do NOT count as failures: suggestions for additional tiles or links (e.g. one for failed refunds);
showing actions on rows where they'd be refused; rounding of presets; and any other finding outside the
seven above (missing helpers, races, validation, test coverage, or an overall "not done" verdict for
those reasons). This is a deliberately small fixture, so such findings are expected. Pass otherwise.
