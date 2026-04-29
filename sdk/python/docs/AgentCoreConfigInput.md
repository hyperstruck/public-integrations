# AgentCoreConfigInput

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**instructions** | **object** | System prompt / instructions for &#x60;AgentConfig.instructions&#x60;. Create requests must provide a non-empty value; empty strings may appear for legacy rows until backfilled. | [optional] 
**description** | **object** | Optional short description (&#x60;AgentConfig.description&#x60;). | [optional] 
**temperature** | **object** | Sampling temperature (&#x60;AgentConfig.temperature&#x60;). | [optional] 
**max_tokens** | **object** | Max tokens to generate (&#x60;AgentConfig.max_tokens&#x60;). | [optional] 
**mcp_servers** | **object** | MCP tool servers (&#x60;AgentConfig.mcp_servers&#x60;). Use &#x60;auth_type&#x60; + &#x60;auth_token_env&#x60; for hosted-safe references to secrets, or explicit &#x60;auth&#x60; objects when injecting credentials out-of-band. | [optional] 
**guardrails_config** | **object** | PII and prompt-injection guardrails (&#x60;AgentConfig.guardrails_config&#x60;). | [optional] 
**hitl_enabled** | **object** | Enable Human-in-the-Loop suspensions for this agent runtime. | [optional] 
**hitl_autonomy_level** | **object** | HITL autonomy level (1&#x3D;most supervised, 5&#x3D;least supervised). Used when &#x60;&#x60;hitl_policy_preset&#x60;&#x60; is &#x60;&#x60;autonomy&#x60;&#x60;. | [optional] 
**hitl_policy_preset** | [**HitlPolicyPreset**](HitlPolicyPreset.md) | How hosted runs build HITL policies: &#x60;&#x60;autonomy&#x60;&#x60; uses &#x60;&#x60;hitl_autonomy_level&#x60;&#x60;; &#x60;&#x60;milestone_only&#x60;&#x60; gates only at milestone boundaries (simpler resume/checkpoints). | [optional] 
**metadata** | **object** | Arbitrary extension metadata (&#x60;AgentConfig.metadata&#x60;). | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

