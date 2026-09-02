# RecordContextModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**concerns** | **object** | The containers this document belongs to, filed by your own ids. | [optional]
**identifiers** | **object** | Stable ids for this document, so a reply can name it. | [optional]
**labels** | **object** | Outcomes the source attached, such as a ticket resolution. | [optional]
**occurred_at** | **object** | When the document happened, such as the meeting&#x27;s date. Answers order documents by it. Never inferred: with none declared a document is ordered by arrival and labelled undeclared. | [optional]
**participants** | **object** | Who was on the document, with addresses already split off. | [optional]
**relations** | **object** | Documents this one answers, supersedes, or shares a thread with. | [optional]
**title** | **object** | What the source calls this document, such as a meeting&#x27;s name. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

