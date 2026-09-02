# ClaimReviewContext

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** |  |
**attribute_key** | **object** |  | [optional]
**canonical_name** | **object** |  |
**channel_trust** | **object** |  |
**citation_absence** | **object** | Why the claim names no source. Null when the lookup did not run, or when every source is outside the caller&#x27;s spaces. | [optional]
**claim_id** | **object** |  |
**corroboration_count** | **object** |  |
**distinct_origins** | **object** |  |
**document_sources** | **object** | The stored documents this claim was read from, in stored order, limited to those the caller&#x27;s spaces admit. | [optional]
**entity_id** | **object** |  |
**etag** | **object** |  |
**identity_tier** | **object** |  | [optional]
**is_bindable** | **object** |  | [optional]
**is_quarantined** | **object** |  |
**is_release_lapsed** | **object** |  | [optional]
**k_required** | **object** |  |
**open_split** | **object** |  | [optional]
**passage_citations** | **object** | Passages this claim was read from that were never stored as documents. | [optional]
**peers** | **object** |  | [optional]
**provenance** | **object** |  | [optional]
**provenance_class** | **object** |  |
**quarantine_cause** | **object** |  | [optional]
**recorded_at** | **object** |  |
**statement** | [**RenderedText**](RenderedText.md) |  |
**status** | **object** |  |
**tool_family** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

