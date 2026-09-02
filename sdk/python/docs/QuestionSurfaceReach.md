# QuestionSurfaceReach

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**entities_reached** | **object** | How many distinct entities this surface reached, exactly. Never truncated, whatever &#x60;entity_ids&#x60; holds: this is the number to read when judging whether a question matched too broadly. |
**entity_ids** | **object** | Which entities, up to 500 per surface, in the order the agent&#x27;s own registry returns them, so the sample is deterministic rather than arbitrary. When &#x60;len(entity_ids) &lt; entities_reached&#x60; the list is the head of a longer set: there is no separate flag to read, because a flag beside the two numbers is a third thing that can disagree with them.  Two things this deliberately does not give you, rather than leave you to find out. Entity NAMES do not travel here, so naming an entity that has no row on the page you are holding takes a follow-up read; every returned row still carries its own entity name and its own &#x60;matched_via&#x60;. And past 500 entities on one surface this is a sample while &#x60;entities_reached&#x60; stays exact, so you always have the full magnitude and not always the full inventory. | [optional]
**matched_as** | [**EntityMatchKind**](EntityMatchKind.md) | Whether this surface matched entities by their own name or by an alias recorded for them. A surface that did both appears twice, once per kind, because the two say different things about why the match was as wide as it was. |
**surface** | **object** | The text from the question that matched something the agent has recorded. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

