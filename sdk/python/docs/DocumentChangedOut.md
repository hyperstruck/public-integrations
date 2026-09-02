# DocumentChangedOut

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**channel** | **object** | How the document travelled: the route its sender stated, or &#x60;web&#x60; for a page a crawl or URL watch fetched. | [optional]
**container** | **object** |  | [optional]
**container_name** | **object** | What a person calls the thread, such as a Slack channel&#x27;s name, as its sender named it. | [optional]
**doc_id** | **object** | The Documents tab&#x27;s id for a note. | [optional]
**document** | [**DocumentRefOut**](DocumentRefOut.md) |  |
**ended** | [**DocumentKeysOut**](DocumentKeysOut.md) |  |
**established** | [**DocumentKeysOut**](DocumentKeysOut.md) |  |
**received_at** | **object** | When the document reached the agent. | [optional]
**since_ended** | [**DocumentKeysOut**](DocumentKeysOut.md) | Values this document wrote that have since ended with nothing in their place. |
**since_followed** | [**DocumentKeysOut**](DocumentKeysOut.md) | Values this document wrote that a later one has since followed without announcing a change. |
**since_replaced** | [**DocumentKeysOut**](DocumentKeysOut.md) | Values this document wrote that a later one has since replaced. |
**title** | **object** | A note&#x27;s name. | [optional]
**undecided** | [**DocumentKeysOut**](DocumentKeysOut.md) |  |
**zone** | **object** | The zone the document&#x27;s own times were read in. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

