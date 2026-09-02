# ClaimSearchIn

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**as_of** | **object** | Search the account as it stood then, with an offset. Defaults to now. | [optional]
**cursor** | **object** | Opaque page cursor for a filtered set: pass a result&#x27;s &#x60;cursor&#x60; back verbatim. | [optional]
**detail** | **object** | &#x60;concise&#x60;: the current statement on each key, a run of readings folded; &#x60;cited&#x60; adds the other live statements and excerpts; &#x60;full&#x60; adds the statements each one replaced. | [optional]
**due_before** | **object** | Obligations due before this time, with an offset; sets the filter. | [optional]
**entity** | **object** | Search this entity&#x27;s claims alone; a question nothing on it bears on is absent. | [optional]
**kind** | **object** | The attribute&#x27;s kind; sets the filter. | [optional]
**limit** | **object** | The page size of a filtered set. | [optional]
**owner** | **object** | Obligations this entity holds (404 when the account does not hold it); sets the filter. | [optional]
**question** | **object** |  |
**since** | **object** | Search what changed since then (with an offset), about &#x60;entity&#x60;, or about the entity the question names; with neither, the point result with a hint to name one. | [optional]
**state** | **object** | With &#x60;state&#x60;, &#x60;kind&#x60;, &#x60;owner&#x60; or &#x60;due_before&#x60;, the result is the filtered set (&#x60;shape: set&#x60;), as GET /claims lists it. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

