# ClaimCitation

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**grounding_digest** | **object** | A fingerprint of the passage, stable across observations of the same text. |
**grounding_ref** | **object** | The source reference the caller declared for the evidence item this value was read out of. This is the half a filename check reads, and it is populated whether or not the passage itself can be resolved.  Always present here, which is a narrower promise than the runtime&#x27;s own type makes and is deliberate. A value can be grounded in a passage the caller gave no name to; such a record cannot name a source, so it is not returned as a citation at all and drives the row&#x27;s &#x60;citation_absence&#x60; of &#x60;source_undeclared&#x60; instead. That keeps one invariant a client can rely on: every entry in &#x60;citations&#x60; names something, and &#x60;citation_absence&#x60; is set exactly when &#x60;citations&#x60; is empty. |
**observed_at** | **object** | When this passage was observed to support the claim. |
**passage** | **object** | The passage text, resolved at read time from the registered document. Null when no document is registered for the reference, and null again once such a document is erased. A null here is never a statement that the citation is wrong. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

