# ResolveResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claims** | **object** | The recalled facts as data rather than as our prose, for a host that renders them under its own design. Carries every fact this agent&#x27;s own planner would read, each with the trust axes and provenance the rendering decision needs, including the facts from attacker-reachable channels that an operator has released, which &#x60;injected_facts_text&#x60; cannot show. Null when the fact lane is unavailable or the recall bound no entity; never an empty entity list. | [optional]
**delivered_obligation_ids** | **object** | The subset of &#x60;offered_obligation_ids&#x60; the block actually carried, after the token budget. Offered and delivered are two records for this shelf and only this shelf, because it escalates on deliveries: an obligation no model was shown must not be escalated for being ignored. A host holding only the offered set cannot tell one from the other, and neither can a client library building an episode from this response. Empty when the block carried nothing, which is not the same as offering nothing. | [optional]
**fact_lane** | **object** | Why the fact lane returned what it returned. Present on every resolve. Read it before concluding from an empty &#x60;offered_claim_ids&#x60; that the agent holds no facts: only outcome &#x27;no_match&#x27; means that. | [optional]
**injected_facts_text** | **object** |  | [optional]
**injected_obligations_text** | **object** |  | [optional]
**injected_text** | **object** |  | [optional]
**learnings** | **object** | The offered learnings&#x27; evidence as data, mirroring the &#x60;Source:&#x60; line in &#x60;injected_text&#x60; without our prose. Null when no learning was offered; never an empty list. | [optional]
**offered_claim_ids** | **object** |  | [optional]
**offered_learning_ids** | **object** |  | [optional]
**offered_obligation_ids** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

