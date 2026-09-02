# AgentUpdateRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**core_config** | **object** |  | [optional]
**description** | **object** |  | [optional]
**home_space_id** | **object** | Move the agent&#x27;s home space; null leaves it unchanged. | [optional]
**name** | **object** |  | [optional]
**reasoning_profile** | **object** |  | [optional]
**status** | **object** |  | [optional]
**timezone** | **object** | The agent&#x27;s own IANA zone (for example &#x60;Australia/Sydney&#x60;), used to render its obligations when a resolve does not name one. Without it every such block falls back to UTC and says so, and the zone decides which obligations read as overdue, not merely how they read. Null leaves it unchanged. Write-only for now: the agent read path does not return it, because the schema fixture the agent suites build cannot create the column (see docs/spec-followups.md). | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

