# MCPServerConfig

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **object** | Unique server identifier |
**url** | **object** | Server URL for HTTP/SSE transport | [optional]
**command** | **object** | Command for stdio transport | [optional]
**args** | **object** | Command arguments (stdio only) | [optional]
**env** | **object** | Environment variables for the server process | [optional]
**allowed_tools** | **object** | Allowlist of tool names to register (None &#x3D; all tools) | [optional]
**category** | **object** | HITL category override for all tools from this server | [optional]
**auth** | **object** | Authentication configuration | [optional]
**connection** | **object** | Connection resilience settings (reconnection, backoff, polling) | [optional]
**auth_type** | **object** | TOML shorthand: &#x27;bearer&#x27; or &#x27;api_key&#x27; | [optional]
**auth_token_env** | **object** | TOML shorthand: environment variable name for auth token/key | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

