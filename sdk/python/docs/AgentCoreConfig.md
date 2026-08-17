# AgentCoreConfig

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **object** | Optional short description (&#x60;AgentConfig.description&#x60;). | [optional]
**domain_dimensions** | **object** | Domain dimensions this agent focuses on when extracting and keeping learnings. Each entry has a name, description, and optional example values. Learnings store the matching names in &#x60;&#x60;domain_dimensions&#x60;&#x60; (list of strings). Omit or null when unguided; on PATCH, pass null or [] to clear. | [optional]
**guardrails_config** | **object** | PII and prompt-injection guardrails (&#x60;AgentConfig.guardrails_config&#x60;). | [optional]
**hitl_autonomy_level** | **object** | HITL autonomy level (1&#x3D;most supervised, 5&#x3D;least supervised). Used when &#x60;&#x60;hitl_policy_preset&#x60;&#x60; is &#x60;&#x60;autonomy&#x60;&#x60;. | [optional]
**hitl_enabled** | **object** | Enable Human-in-the-Loop suspensions for this agent runtime. | [optional]
**hitl_policy_preset** | [**HitlPolicyPreset**](HitlPolicyPreset.md) | How hosted runs build HITL policies: &#x60;&#x60;autonomy&#x60;&#x60; uses &#x60;&#x60;hitl_autonomy_level&#x60;&#x60;; &#x60;&#x60;milestone_only&#x60;&#x60; gates only at milestone boundaries (simpler resume/checkpoints). | [optional]
**hitl_required_approvals** | **object** | Distinct approvals required before a milestone gate lets the run proceed (a four-eyes / maker-checker quorum). Only supported with &#x60;&#x60;hitl_policy_preset&#x3D;milestone_only&#x60;&#x60;. Each approval must come from a distinct authenticated principal (a distinct API key or portal login, not necessarily a distinct human), the run&#x27;s dispatcher is excluded, and any single rejection vetoes. One caller resuming twice replays rather than counting twice. | [optional]
**instructions** | **object** | System prompt / instructions for &#x60;AgentConfig.instructions&#x60;. Create requests must provide a non-empty value; empty strings may appear for legacy rows until backfilled. | [optional]
**mcp_servers** | **object** | MCP tool servers (&#x60;AgentConfig.mcp_servers&#x60;). Use &#x60;auth_type&#x60; + &#x60;auth_token_env&#x60; for hosted-safe references to secrets, or explicit &#x60;auth&#x60; objects when injecting credentials out-of-band. | [optional]
**metadata** | **object** | Arbitrary extension metadata (&#x60;AgentConfig.metadata&#x60;). | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

