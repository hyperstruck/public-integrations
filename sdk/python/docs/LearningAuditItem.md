# LearningAuditItem

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**applicable_goals** | **object** |  | [optional]
**applicable_tools** | **object** |  | [optional]
**category** | **object** |  | [optional]
**content** | **object** |  |
**corroboration_count** | **object** | Independent sources that corroborated this learning. |
**created_at** | **object** |  |
**evidence_availability** | [**EvidenceAvailability**](EvidenceAvailability.md) |  | [optional]
**evidence_summary** | **object** |  | [optional]
**instances** | **object** |  | [optional]
**learning_id** | **object** |  |
**legacy_learning_type** | **object** | Deprecated compatibility passthrough; null for new records. | [optional]
**privacy** | [**PrivacyClassification**](PrivacyClassification.md) |  |
**reliability** | **object** | How established, 0.0-1.0 (Wilson lower bound over corroborations, lowered by contradictions). |
**reuse_count** | **object** | UI alias of times_applied (same value, kept for the curation column heading); not an independent counter. |
**review_reasons** | **object** |  | [optional]
**review_state** | [**ReviewState**](ReviewState.md) |  |
**scope** | [**LearningScope**](LearningScope.md) |  | [optional]
**source** | **object** | How this learning was produced: &#x60;llm_extracted&#x60;, &#x60;auto_derived&#x60; or &#x60;pattern_synthesised&#x60;. This is the extraction method, not the provenance of the material: it distinguishes a synthesised pattern from an extracted rule, and it is what answers how much of a corpus synthesis actually produced. For the originating goal text, read &#x60;source_goal&#x60; on the detail endpoint. |
**summary** | **object** |  | [optional]
**tags** | **object** | Display tags (applicable tools and goals merged). | [optional]
**times_applied** | **object** |  |
**times_helpful** | **object** |  |
**trust_level** | [**TrustLevel**](TrustLevel.md) | Verification tier; UNKNOWN for an unmappable stored value. |
**updated_at** | **object** |  |
**utility** | **object** | Value when applied, 0.0-1.0 (Core&#x27;s recency-discounted application-outcome score). |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

