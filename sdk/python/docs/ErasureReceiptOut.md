# ErasureReceiptOut

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**aliases_erased** | **object** |  |
**claims_erased** | **object** |  |
**claims_reended** | **object** |  |
**claims_reopened** | **object** | Claims on other entities the erased claims had ended, current again. |
**dossiers_rebuilt** | **object** |  |
**entities_erased** | **object** | Document erasure only: entities nothing else held, deleted. | [optional]
**entities_renamed** | **object** | Document erasure only. | [optional]
**entities_unmerged** | **object** |  |
**folds_undone** | **object** | Document erasure only. | [optional]
**id** | **object** |  |
**identifiers_erased** | **object** | Document erasure only: identifiers removed from entities. | [optional]
**insight_findings_deleted** | **object** | Insights findings removed because they named the entity or cited an erased claim. | [optional]
**insight_run_events_blanked** | **object** | Insight run events whose label or payload named the entity and were blanked. | [optional]
**insight_runs_blanked** | **object** | Insight run summaries or errors that named the entity and were blanked. | [optional]
**legacy_entities_erased** | **object** | Entity erasure only: entities of the agent&#x27;s earlier claim records that carried one of this entity&#x27;s names, erased in the same request. | [optional]
**natures_reset** | **object** | Document erasure only. | [optional]
**obligations_erased** | **object** | Entity erasure only: the obligations erased. |
**references_cleared** | **object** |  |
**relations_erased** | **object** | Entity erasure only: the relations erased. |
**residue** | **object** | Entity erasure only: what the erasure could not finish and may still hold a value or name of the erased entity (&#x60;learning_literals&#x60;, &#x60;run_state_offers&#x60;). Empty when nothing remains; repeating the erasure finishes what it names. | [optional]
**statements_erased** | **object** | Entity erasure only: the claims erased that are neither obligations nor relations. |
**subject_id** | **object** |  |
**subject_kind** | **object** |  |
**verdicts_erased** | **object** |  |
**verdicts_written** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

