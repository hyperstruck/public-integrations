# ProviderCredentialUpdateRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**provider** | **object** |  | [optional]
**display_name** | **object** |  | [optional]
**secret** | **object** |  | [optional]
**is_active** | **object** |  | [optional]
**metadata** | **object** | Optional metadata replacement. Use &#x60;metadata.base_url&#x60; to override the provider endpoint. If you provide &#x60;metadata.endpoint&#x60;, it is normalized to &#x60;base_url&#x60;. If omitted, the existing metadata is preserved unless the provider changes, in which case the endpoint resets to the sane default for Anthropic, Groq, Ollama, or OpenAI. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

