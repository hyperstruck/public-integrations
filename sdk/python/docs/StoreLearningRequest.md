# StoreLearningRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **object** | The learning content to store. | 
**learning_type** | [**LearningType**](LearningType.md) | Category of the learning. | 
**confidence** | **object** | Initial confidence level (0.0–1.0). | [optional] 
**source_goal** | **object** | Goal or context this learning originated from. | [optional] 
**applicable_goals** | **object** | Keywords or patterns this learning applies to. | [optional] 
**applicable_tools** | **object** | Tools this learning relates to. | [optional] 
**privacy** | [**PrivacyClassification**](PrivacyClassification.md) | Privacy classification for cross-agent sharing eligibility. | [optional] 
**instances** | **object** | Specific evidence instances that support the learning. API-sourced instances are content-addressed for deduplication by entity values and outcome. | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

