# CloseObligationRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**dropped_reason** | **object** | Required when outcome is &#x27;dropped&#x27;. Only &#x27;not_an_obligation&#x27; counts against the source that produced it; the other three are judgements about the commitment, not the source. | [optional]
**expected_version** | **object** | The version the caller last read. Omitted, the open-status guard still applies and a row that has already closed is refused. Present and stale, the request is a 409 naming the current version. | [optional]
**kept_basis** | **object** | Who said it was done. Required when outcome is &#x27;kept&#x27;. | [optional]
**note** | **object** |  | [optional]
**outcome** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

