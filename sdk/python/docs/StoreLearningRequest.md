# StoreLearningRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**applicable_goals** | **object** | Keywords or patterns this learning applies to. | [optional]
**applicable_tools** | **object** | Tools this learning relates to. | [optional]
**condition** | **object** | The situation the rule applies in. Core stores a learning as contrast-first structured parts; sending only &#x60;content&#x60; flattens the rule to prose and the structure cannot be recovered afterwards. | [optional]
**consequent** | **object** | What to do when the condition holds. | [optional]
**content** | **object** | The learning content to store. |
**contrast** | **object** | The observed reason or outcome the rule rests on, if it states one. | [optional]
**domain_dimensions** | **object** | Names of domain dimensions this learning addresses (e.g. OWASP, reliability). Prefer names from the agent&#x27;s &#x60;&#x60;core_config.domain_dimensions&#x60;&#x60; rather than stuffing taxonomy into applicable_goals. | [optional]
**instances** | **object** | Specific structured examples that support the learning, expressed as entity values and observed outcomes. | [optional]
**privacy** | [**PrivacyClassification**](PrivacyClassification.md) | Privacy classification for cross-agent sharing eligibility. | [optional]
**source_goal** | **object** | Goal or context this learning originated from. | [optional]
**utility** | **object** | Starting utility prior, the curator&#x27;s initial belief in how useful this learning is when applied (0.0-1.0). Both utility and establishedness are then earned, utility from application outcomes and establishedness from corroboration, so the value read back moves off this prior over time. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

