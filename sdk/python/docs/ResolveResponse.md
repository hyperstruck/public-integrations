# ResolveResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claims** | **object** | The keys &#x60;injected_facts_text&#x60; renders, as Claim items, for a host that renders them under its own design. Null when nothing was recalled; never an empty list. | [optional]
**fact_lane** | **object** | Why the claims block holds what it holds. Present on every resolve. Read it before concluding from an empty &#x60;offered_claim_ids&#x60; that the account holds nothing: only outcome &#x27;no_match&#x27; means that. | [optional]
**has_reported_outcomes** | **object** | True once this agent&#x27;s host has reported the outcome of any run through reinforce. A learning is recommended only after it has helped in two runs, and only a reported outcome can say it helped, so while this is false nothing can be recommended and the advice block ends with a sentence saying so. | [optional]
**injected_facts_text** | **object** |  | [optional]
**injected_text** | **object** |  | [optional]
**is_all_offered** | **object** | True when this resolve returned nothing because everything relevant to the goal had already been offered in the request&#x27;s session window. Distinct from a corpus with nothing relevant, which leaves it false. | [optional]
**learnings** | **object** | The offered learnings&#x27; evidence as data, mirroring the &#x60;Source:&#x60; line in &#x60;injected_text&#x60; without our prose. Null when no learning was offered; never an empty list. | [optional]
**offered_claim_ids** | **object** |  | [optional]
**offered_learning_ids** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

