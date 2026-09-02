# ObligationClosureResult

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**disposition** | **object** | applied: the row moved to the requested terminal state. already_closed: it was already in exactly that state, so nothing moved and nothing is wrong. conflicting_close: a different terminal state holds, and the report was dropped rather than allowed to overwrite it. not_offered: this run was never shown that id, which is the disposition a stale id carried across turns gets. not_found: the id was offered and the row is no longer on the shelf. refused: the shelf rejected the write, from a version race or a note it would not take; terminal, do not resend. busy: this was not attempted; transient, and the same outcome may be sent again. Not produced by reinforce, whose closes take no run lock. |
**id** | **object** | The obligation id the reported outcome named. |
**status** | **object** | The row&#x27;s status after the call, when the row exists. Null for not_offered, not_found and busy, where there is no row this call read. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

