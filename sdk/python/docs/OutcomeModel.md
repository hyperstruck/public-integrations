# OutcomeModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**completed_steps** | **object** | Number of completed steps. | [optional]
**failed_steps** | **object** | Number of failed steps. | [optional]
**final_output** | **object** | The answer this run actually gave its principal, verbatim: the composed output the person was shown, not the reasoning that produced it. Send it on POST /observe and the agent&#x27;s own commitments in it (\&quot;I&#x27;ll confirm the volumes by Friday\&quot;) are recorded on the obligation shelf, dated from the run, and held for review, where they are read with GET /agents/{agent_id}/obligations?needs_review&#x3D;true. They are NOT returned by /resolve: the agent&#x27;s own answer carries no external source vouching for it, so a curator sees it before anybody acts on it. Only /observe harvests; a value supplied on /reinforce is dropped and counted. Commitments are recorded only when own-output harvesting is enabled for the tenant; otherwise the field is accepted and nothing is recorded. Omit it and nothing else changes: the field is never required and an episode without it is accepted exactly as before. Populate it only from the composed output; a tool result put here is stored as a promise the agent made. | [optional]
**is_success** | **object** | Whether the episode achieved its goal. |
**total_steps** | **object** | Total number of attempted steps. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

