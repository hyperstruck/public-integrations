# AgentValueProfileUpdate

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**hourly_rate_usd** | **object** | Rate that turns minutes into dollars. Null uses the platform default ($100). | [optional]
**is_auto_estimate_enabled** | **object** | Write the platform&#x27;s estimate after each successful run that applied learnings. Estimates are reported apart from measured value. | [optional]
**is_enabled** | **object** | Turn value tracking on. While off, new value is refused; history stays readable. |
**minutes_per_applied_learning** | **object** | Minutes the platform estimate credits per applied learning. Null uses the platform default (10). | [optional]
**rate_card** | **object** | Named, priced units. Recording &#x60;unit_key&#x60; and &#x60;quantity&#x60; is the deterministic path. | [optional]
**value_description** | **object** | What counts as value for this agent, in plain language. Other agents read this before deciding whether to record value. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

