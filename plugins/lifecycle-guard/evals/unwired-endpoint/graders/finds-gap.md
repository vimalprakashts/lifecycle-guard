---
type: llm
weight: 1
---

The review identifies that the admin cannot reject a refund from the UI: the reject endpoint
exists in the API but the refunds page has no reject button/action, although the spec gives the admin
"reject with reason". Passing requires naming this missing reject action specifically.
