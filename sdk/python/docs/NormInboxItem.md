# NormInboxItem

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **object** | The directive as the principal stated it. Typically within 8000 characters; not validated, because Core promises no length and a longer one must still be readable in order to be retired. |
**dormant_until** | **object** | Date this norm is silenced until, or empty when it is not dormant. | [optional]
**is_retired** | **object** | Archived by a curator or superseded by a later directive. |
**learning_id** | **object** |  |
**proposed_breaches** | **object** | Times the critic proposed that a run breached this norm. |
**run_digest** | **object** | Short prefix of the commitment to the run the norm was stated on, so a curator can tell two norms from one session apart. Empty when the record predates the commitment. |
**state** | **object** | Core&#x27;s lifecycle state for this norm: probation, confirmed or superseded. A norm stated before the lifecycle existed reads as confirmed, because it already had primacy and keeps it. |
**stated_at** | **object** | The date the principal stated this norm, or &#x27;unknown&#x27; for a record written before the date was captured. |
**times_applied** | **object** |  |
**times_offered** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

