# Silence

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**arm** | **object** | &#x60;arm_unavailable&#x60;: which arm. | [optional]
**count** | **object** | &#x60;held_back&#x60;: how many rows are held for human review. &#x60;outside_as_of&#x60;: how many rows exist now that did not exist at the instant you asked about. Null where the reason carries no count, never a zero standing in for a number nobody measured. | [optional]
**detail** | **object** | The underlying reason in the runtime&#x27;s own words, where it has one. | [optional]
**entity_ids** | **object** | &#x60;entity_bound_no_claims&#x60; and &#x60;outside_as_of&#x60;: which of the entities your question reached the reason applies to. | [optional]
**entity_names** | **object** | The names of those entities, in the same order. Print these rather than the ids: an entity id is a UUID, and a sentence naming one is not something a reader can act on. Empty, never partial, when a name could not be resolved. | [optional]
**reason** | [**SilenceReason**](SilenceReason.md) |  |
**shelf** | **object** | &#x60;shelf_unavailable&#x60;: which composed half did not run. | [optional]
**terms** | **object** | &#x60;term_did_not_participate&#x60; and &#x60;no_surface_matched&#x60;: the words of your question that reached no recorded entity, so they selected nothing. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

