# RunOutputSummary

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**approvals_recorded** | **object** | For a suspension awaiting a multi-approver quorum, the number of distinct approvals recorded so far (out of the suspension&#x27;s &#x60;&#x60;required_approvals&#x60;&#x60;). Null when the suspension is not a quorum. | [optional]
**claim_attribution** | **object** | Which stored facts this run used. &#x60;&#x60;bound&#x60;&#x60; is everything that reached the planner, used or not, so &#x60;&#x60;bound&#x60;&#x60; minus &#x60;&#x60;applied&#x60;&#x60; answers why a fact was not used; each applied id carries its credit route (&#x60;&#x60;by_construction&#x60;&#x60; is certain, &#x60;&#x60;by_value_equality&#x60;&#x60; is a guarded match); &#x60;&#x60;misled&#x60;&#x60; is the subset the outcome then contradicted. When nothing was applied, &#x60;&#x60;reason&#x60;&#x60; says which of a closed set applies, so an empty result is never confused with a pass that failed or never ran. &#x60;&#x60;child_run_ids&#x60;&#x60; references delegated runs rather than absorbing their claims, which are scoped to their own agent. Null when the run predates the record or claims are not configured. | [optional]
**error** | **object** |  | [optional]
**result** | **object** |  | [optional]
**suspension** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

