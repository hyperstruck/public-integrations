# ConcernModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**kind** | **object** | What sort of thing the container is. **A person is refused rather than accepted**: filing every document somebody touched under that person would hand one individual everything their colleagues touched too. | [optional]
**name** | **object** | What the container is called, so the declaration can bind an entity the corpus already knows by name. Without it the declaration is still recorded and binds later, once something else names the same id. | [optional]
**scheme** | **object** | The namespace this id lives in, e.g. &#x60;crm:account&#x60;. Yours to choose, and stable across sends. |
**value** | **object** | The container&#x27;s id in that namespace. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

