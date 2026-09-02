# QuestionClaimRow

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**arms** | **object** | Which arms returned this row. A row carrying only &#x60;recall&#x60; is a suggestion, not part of any completeness statement. | [optional]
**attribute_key** | **object** | The slot this value was filed under, or null when it was recorded without one. A null is not a defect: a value nothing could be filed under is still held, and is still returned here, because withholding it would be the omission this read exists to remove. | [optional]
**channel_trust** | **object** | How much authority the channel the value arrived on earns on its own. |
**citation_absence** | **object** | Why &#x60;citations&#x60; is empty, present only when it is AND only when the citation lookup actually ran. Read the response-level &#x60;citations.guarantee&#x60; first: when that is &#x60;unavailable&#x60; this field is deliberately null on every row, because there is nothing to explain about a claim we did not look up.  Two of the four values name work you can do (&#x60;source_undeclared&#x60;, &#x60;ambiguous_match&#x60;) and two name work nobody can do (&#x60;no_passage_lane&#x60;, &#x60;predates_citations&#x60;). Branch on that split rather than on emptiness, which cannot tell them apart. | [optional]
**citations** | **object** | Where this value was read from, zero or more. Plural because a value corroborated across three meetings has three passages, and &#x27;which meetings does this come from&#x27; is a question a single source field cannot answer. | [optional]
**claim_id** | **object** |  |
**contradicts** | **object** | The claims this row contradicts, empty where none. BOTH sides of an unresolved contradiction are always returned and each names the other; returning one side is a silently resolved conflict, and that is a defect rather than a mode a caller may choose. This is not a flag: there is no request field that turns it off. | [optional]
**document_occurred_at** | **object** | That document&#x27;s declared date. Null when it declared none; an ingest time is never shown as a meeting date. | [optional]
**document_ref** | **object** | The document this claim was read from, or null when it names none. | [optional]
**entity_id** | **object** |  |
**entity_name** | **object** | The entity this claim is about, so a row can be read without a second lookup. |
**is_caller_declared** | **object** | True when the provenance on this row is what the caller said it was rather than something the platform observed. Published because a caller weighing its own facts should know which of them it vouched for itself. |
**is_contradiction_partner** | **object** | True when this row was pulled onto this page to complete a contradiction pair rather than reached by the page&#x27;s own ordering. Such a row may appear again on the page its own position belongs to; that duplication is deliberate, and the alternative is not returning it at all. | [optional]
**is_document_date_declared** | **object** | Whether the document declared its date. Null when there is no document or its record could not be read. | [optional]
**is_operator_asserted** | **object** | True when a human operator asserted this value rather than it being extracted. |
**is_stale** | **object** | True when the value has decayed on the currency axis: nothing has replaced it, so it IS the current value, and it is merely old. This is a different fact from being superseded, and conflating the two causes the failure that withholding both looks like it prevents: a decayed value withheld is an omission, a superseded value returned as current is a lie. Decayed values are returned, marked; superseded ones are not. |
**is_tainted** | **object** | True when the value reached us through content that could have been authored to influence us. |
**last_observed_at** | **object** | The most recent time a source restated this value. Read it beside recorded_at: a value recorded once in March and restated last week is a different thing from one nobody has mentioned since. | [optional]
**matched_source_ids** | **object** | Present only with an &#x60;ambiguous_match&#x60; absence: the evidence items the value was found in. &#x27;Found in these, cannot attribute to one&#x27; is strictly more than silence. | [optional]
**matched_via** | **object** | Every route that reached this row&#x27;s entity. Empty when the row arrived through the recall arm alone, which is itself the useful signal: nothing in the question named this entity, an approximate search found it. | [optional]
**passage** | **object** | The passage of the stored document this claim was read from, resolved at read time. | [optional]
**passage_absence** | **object** | Why &#x60;passage&#x60; is null, typed rather than bare. | [optional]
**provenance** | **object** | Where this value came from, as declared and as resolved: the channel, the genre, the source identifier and the author the caller stated, beside the closed vocabularies those resolved to. Both halves, because a caller weighing its own facts needs to see that a source called itself a policy AND whether that word was recognised; a resolved value alone hides an unrecognised declaration behind &#x27;unknown&#x27;, and a declared value alone cannot say whether anything ranks on it. The same record every other claim surface publishes, off the same column. | [optional]
**provenance_class** | **object** | How far the source was from the agent: its own output, a tool, or a third party. |
**recorded_at** | **object** | When this version of the value was written. Half of the paging key. |
**statement** | **object** | The claim as a standalone sentence, whole and uncut. |
**status** | **object** | Where this row sits in its own history: open, or disputed by an alternative that has not been settled. Superseded rows are excluded unless include_superseded was set. |
**superseded_by_claim_id** | **object** | On a superseded row, the claim that replaced it. | [optional]
**supersedes_id** | **object** | The claim this one replaced, or the incumbent it is disputing. It is the link the supersession chain is walked along, and with include_superseded it is how a history question is answered. | [optional]
**valid_from** | **object** | When the value started being true in the world, which is not when it was recorded. |
**valid_until** | **object** | When the value stopped being true, where that is known. Null means still in force. | [optional]
**value_num** | **object** | The value as a number, when it is one. | [optional]
**value_text** | **object** | The value itself, separated from the sentence around it so it can be compared. |
**value_time** | **object** | The value as a time, when it is one. | [optional]
**value_type** | **object** | How to read the value: text, a number, a time, and so on. |
**withheld_contradiction_count** | **object** | How many of this row&#x27;s contradiction partners exist but are held rather than returned. Zero on almost every row, and load-bearing where it is not.  The both-sides promise on &#x60;contradicts&#x60; has exactly one lawful exception: a hold keeps back content no human has released, so a held partner is not returned. Without this number an incumbent whose every dissenter is held comes back with an empty &#x60;contradicts&#x60; and is indistinguishable from a claim nothing disputes, which is the silently resolved conflict the promise exists to refuse, arriving through the one door the completion pass does not watch.  So read it as: this answer has a disputed side you are not being shown. Non-zero here with an empty &#x60;contradicts&#x60; means the only dissent on this value is held, and the value should not be quoted as uncontested. The agent-wide &#x60;held_count&#x60; cannot do this job, because it cannot be attributed to a row and so cannot tell you WHICH of your answers is missing a half. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

