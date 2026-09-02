# ResolvedEntity

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claims** | **object** |  | [optional]
**held_for_review_count** | **object** | Open claims about this entity that are quarantined, so they were never bound and are absent above. A non-zero count is the difference between an entity nobody knows anything about and one whose facts are waiting on a curator. List them with GET /agents/{agent_id}/claims, which needs the &#x60;claims:read&#x60; scope that recall&#x27;s own &#x60;agents:read&#x60; does not imply. | [optional]
**name** | **object** |  |
**salience** | **object** |  |
**truncated_count** | **object** | Facts that cleared the trust floor and fell outside this lane&#x27;s per-entity cap. More of the same, not withheld. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

