# LearningAuditItem

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**learning_id** | **object** |  |
**content** | **object** |  |
**summary** | **object** |  | [optional]
**scope** | [**LearningScope**](LearningScope.md) |  | [optional]
**category** | **object** |  | [optional]
**legacy_learning_type** | **object** | Deprecated compatibility passthrough; null for new records. | [optional]
**utility** | **object** | Value when applied, 0.0-1.0 (Core&#x27;s recency-discounted application-outcome score). |
**reliability** | **object** | How established, 0.0-1.0 (Wilson lower bound over corroborations, lowered by contradictions). |
**corroboration_count** | **object** | Independent sources that corroborated this learning. |
**trust_level** | [**TrustLevel**](TrustLevel.md) | Verification tier; UNKNOWN for an unmappable stored value. |
**privacy** | [**PrivacyClassification**](PrivacyClassification.md) |  |
**review_state** | [**ReviewState**](ReviewState.md) |  |
**review_reasons** | **object** |  | [optional]
**times_applied** | **object** |  |
**times_helpful** | **object** |  |
**reuse_count** | **object** | UI alias of times_applied (same value, kept for the curation column heading); not an independent counter. |
**tags** | **object** | Display tags (applicable tools and goals merged). | [optional]
**applicable_goals** | **object** |  | [optional]
**applicable_tools** | **object** |  | [optional]
**instances** | **object** |  | [optional]
**evidence_summary** | **object** |  | [optional]
**evidence_availability** | [**EvidenceAvailability**](EvidenceAvailability.md) |  | [optional]
**created_at** | **object** |  |
**updated_at** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

