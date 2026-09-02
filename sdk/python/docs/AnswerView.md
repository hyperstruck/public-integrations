# AnswerView

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** |  |
**answer** | **object** |  | [optional]
**answer_id** | **object** |  |
**answer_unavailable_reason** | **object** |  | [optional]
**appended_finding_ids** | **object** |  | [optional]
**as_of** | **object** |  |
**background_finding_ids** | **object** |  | [optional]
**boundary** | **object** |  | [optional]
**change** | **object** |  | [optional]
**claims** | **object** |  | [optional]
**completeness** | **object** |  | [optional]
**detail** | [**AnswerDetail**](AnswerDetail.md) |  |
**documents** | **object** |  | [optional]
**findings** | **object** |  | [optional]
**interpretation** | **object** |  | [optional]
**is_written** | **object** | False when the writer failed and the answer is its findings laid out by code, each in its own words, rather than prose a writer composed and checked. Null when no writer ran, which &#x60;answer_unavailable_reason&#x60; says why. | [optional]
**lead** | **object** | The answer&#x27;s opening paragraph as a field, from the &#x60;findings&#x60; level up. Absent below the &#x60;findings&#x60; level, and null when the answer has no lead. Its &#x60;finding_ids&#x60; and &#x60;reference_ids&#x60; are what the writer cited, not what the check judged against. | [optional]
**more** | **object** | Where this same answer is served at each higher level: a GET path per level, never a new answer. Empty at &#x60;everything&#x60;. Null only when the answer could not be stored, which &#x60;more_unavailable_reason&#x60; says. | [optional]
**more_unavailable_reason** | **object** |  | [optional]
**multi_valued_slots** | **object** |  | [optional]
**obligations** | **object** |  | [optional]
**question** | **object** |  |
**read_documents** | **object** |  | [optional]
**references** | **object** | Null when no writer ran, and empty when one ran and cited nothing. | [optional]
**results** | **object** |  | [optional]
**sections** | **object** |  | [optional]
**selection** | **object** |  | [optional]
**silence** | **object** |  | [optional]
**sources** | **object** |  | [optional]
**stage_events** | **object** |  | [optional]
**subject** | **object** |  | [optional]
**version** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

