# ToolSpecModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**category** | **object** | The tool&#x27;s declared category. Restraint and admissibility both classify on this, and only the values Core knows are read: &#x60;read_only&#x60;, &#x60;write&#x60;, &#x60;destructive&#x60;, &#x60;external&#x60;, &#x60;delegation&#x60;. Of those, &#x60;write&#x60;, &#x60;destructive&#x60; and &#x60;external&#x60; are the side-effectful ones. Anything else, including a near-miss like &#x60;read&#x60;, is treated as declaring nothing, and a roster where nothing declares a side-effectful category cannot express that a run held off at all. | [optional]
**description** | **object** | Short explanation of what the tool can do. | [optional]
**name** | **object** | Caller-visible tool name. |
**parameters** | **object** | The tool&#x27;s declared parameter schema, used to fingerprint its shape. Pre-redact secrets and personal data: this is stored on the learning. | [optional]
**returns** | **object** | The tool&#x27;s declared return schema, used to fingerprint its shape. Pre-redact secrets and personal data: this is stored on the learning. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

