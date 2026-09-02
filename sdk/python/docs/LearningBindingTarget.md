# LearningBindingTarget

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claim_id** | **object** |  | [optional]
**is_held_for_safety** | **object** | True when the learning is a safety rule and the slot now holds a different value: recall keeps rendering the value the rule was written with until a curator accepts the change, so &#x60;value&#x60; is that earlier value. | [optional]
**is_value_withheld** | **object** | True when a claim holds the slot but its value is not offered, because it is in conflict or of untrusted or unknown origin. | [optional]
**state** | **object** | The first five are the claim in force on the slot, in &#x60;GET /claims&#x60; words, or &#x60;ended&#x60; when none is. &#x60;erased&#x60;: the slot&#x27;s entity was erased. &#x60;unresolved&#x60;: the store holds nothing on the slot or did not answer. |
**value** | **object** | The value recall would render for the binding; null when the claim cannot be offered or there is none. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

