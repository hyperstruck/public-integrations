# ResolveClaimsLane

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**caveat** | **object** | The caveat every rendered line carries; render it beside any fact you present. |
**entities** | **object** |  | [optional]
**is_source_lookup_available** | **object** | Whether this deployment could look up where a fact was read at all. False means every &#x60;source_refs&#x60; below is empty for a reason that is ours rather than yours, so do not read it as &#x27;these facts have no source&#x27;. True with an empty &#x60;source_refs&#x60; on a claim does mean that claim names none.  It is here rather than left to be inferred because the inference is wrong in exactly the case that matters: a deployment pinned to a Core that predates the citation lookup, or one whose platform has not yet applied the citation migration, returns the same empty list as a corpus ingested with no &#x60;source_ref&#x60;. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

