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
**summary** | **object** |  | [optional]
**tags** | **object** | Display tags (applicable tools and goals merged). | [optional]
**times_applied** | **object** |  |
**times_helpful** | **object** |  |
**trust_level** | [**TrustLevel**](TrustLevel.md) | Verification tier; UNKNOWN for an unmappable stored value. |
**updated_at** | **object** |  |
**utility** | **object** | Value when applied, 0.0-1.0 (Core&#x27;s recency-discounted application-outcome score). |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

