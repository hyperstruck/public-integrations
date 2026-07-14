# StoreLearningRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **object** | The learning content to store. |
**utility** | **object** | Starting utility prior, the curator&#x27;s initial belief in how useful this learning is when applied (0.0-1.0). Both utility and establishedness are then earned, utility from application outcomes and establishedness from corroboration, so the value read back moves off this prior over time. | [optional]
**source_goal** | **object** | Goal or context this learning originated from. | [optional]
**applicable_goals** | **object** | Keywords or patterns this learning applies to. | [optional]
**applicable_tools** | **object** | Tools this learning relates to. | [optional]
**privacy** | [**PrivacyClassification**](PrivacyClassification.md) | Privacy classification for cross-agent sharing eligibility. | [optional]
**instances** | **object** | Specific structured examples that support the learning, expressed as entity values and observed outcomes. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

