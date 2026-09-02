# ResolvedClaim

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**attribute_key** | **object** | The &#x60;tool_family:field&#x60; key, where the fact names a structural field. Null for an unkeyed fact. | [optional]
**channel_trust** | **object** | How attacker-reachable the channel it arrived on is. Orthogonal to who asserted it. |
**id** | **object** |  |
**is_caller_declared** | **object** | Whether a caller declared where this content came from, which is the case for anything ingested through /distill. Independent of channel trust: a declared source an operator has admitted is &#x60;unknown&#x60; rather than &#x60;untrusted&#x60;, and is still declared. An admitted declared fact does render into &#x60;injected_facts_text&#x60;; what is withheld from that block is content from an attacker-reachable channel, which reaches you here as data even after a human releases it. |
**is_operator_asserted** | **object** | Whether a human vouched for it rather than evidence corroborating it. |
**is_stale** | **object** | Whether currency decay has down-weighted it. Stale is not retracted. |
**is_tainted** | **object** | Whether the channel it arrived on is attacker-reachable. |
**last_observed_at** | **object** |  | [optional]
**provenance** | **object** | The provenance record as declared at ingest: source_id, channel, genre, author, source_time. | [optional]
**provenance_class** | **object** | Who asserted it. &#x60;user_stated&#x60; outranks &#x60;tool_observed&#x60;, which outranks &#x60;llm_inferred&#x60;. |
**recorded_at** | **object** |  |
**rendered_line** | **object** | The exact line the rendered block would carry for this fact, marker and caveat included. Render it verbatim to earn attribution: reinforce matches a receipt against this line, so a host that rewrites it in its own words is never credited for the fact, and is never reported as having dropped it either. |
**source_refs** | **object** | Where this value was read, as YOU declared it on the evidence item&#x27;s &#x60;source_ref&#x60;: a filename today, a document reference once documents are registered. This is what lets you show a reader which meeting a fact came from.  Plural, because a fact corroborated across three meetings was read out of three places.  Empty means no citation names a source for this claim, which is NOT a statement that it has none: an item ingested without a &#x60;source_ref&#x60; can never name one afterwards, because the name was never sent. It is also empty on a deployment whose platform predates the citation table, which fails to silence rather than failing a resolve.  Deliberately NOT part of &#x60;rendered_line&#x60;. That line is prompt text with our framing on it and the attribution matcher rests on that framing, while a reference is a string you supplied; render it beside the line rather than inside it. | [optional]
**statement** | **object** | The fact as one sentence, sanitised for rendering. |
**value** | **object** | The value alone, for a host that renders its own sentence. |
**value_type** | **object** | The shape of the value, so a host can render a date as a date rather than as prose. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

