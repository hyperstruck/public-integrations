# MCPServerConfig

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**allowed_tools** | **object** | Allowlist of tool names to register (None &#x3D; all tools) | [optional]
**args** | **object** | Command arguments (stdio only). Unsupported for hosted agents. | [optional]
**auth** | **object** | Authentication configuration. Discriminated on &#x27;auth_type&#x27; so a credential posted as a dict resolves to the concrete model that carries it. Annotating the base here silently discarded every field the base does not declare, which meant a caller supplying their own token got a 200 and a config that could never authenticate. | [optional]
**auth_token_env** | **object** | TOML shorthand: environment variable name for auth token/key. Unsupported for hosted agents. | [optional]
**auth_type** | **object** | TOML shorthand: &#x27;bearer&#x27; or &#x27;api_key&#x27; | [optional]
**category** | **object** | HITL category override for all tools from this server | [optional]
**command** | **object** | Command for stdio transport. Unsupported for hosted agents. | [optional]
**connection** | **object** | Connection resilience settings (reconnection, backoff, polling) | [optional]
**env** | **object** | Environment variables for the server process. Unsupported for hosted agents. | [optional]
**name** | **object** | Unique server identifier |
**tool_timeout_ms** | **object** | Deadline for every tool from this server, overriding the engine&#x27;s config-wide default. Per server rather than per tool because that is what an operator knows: a remote server&#x27;s latency is a property of the server, and the engine&#x27;s default was chosen for a local call. | [optional]
**url** | **object** | Server URL for HTTP/SSE transport. Required for hosted agents; use an HTTP/SSE/streamable-HTTP MCP server URL. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

