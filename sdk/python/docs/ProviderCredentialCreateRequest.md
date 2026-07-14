# ProviderCredentialCreateRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**provider** | [**ModelProvider**](ModelProvider.md) |  |
**display_name** | **object** |  |
**binding_type** | [**ProviderCredentialBindingType**](ProviderCredentialBindingType.md) |  |
**agent_id** | **object** |  | [optional]
**secret** | **object** | Provider secret. This value is write-only and never returned. |
**is_active** | **object** |  | [optional]
**metadata** | **object** | Optional credential metadata. Use &#x60;metadata.base_url&#x60; to override the provider endpoint. If omitted, the API stores a sane provider default: Anthropic&#x3D;&#x60;https://api.anthropic.com&#x60;, Groq&#x3D;&#x60;https://api.groq.com&#x60;, Ollama&#x3D;&#x60;http://localhost:11434/v1&#x60;, OpenAI&#x3D;&#x60;https://api.openai.com/v1&#x60;. Legacy &#x60;metadata.endpoint&#x60; is accepted as an alias and normalized to &#x60;base_url&#x60;. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

