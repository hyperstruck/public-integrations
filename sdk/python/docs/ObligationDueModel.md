# ObligationDueModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**at** | **object** | The due instant. Naive datetimes are refused, not assumed UTC. |
**precision** | **object** | &#x27;date&#x27;: overdue at end of day in the zone. &#x27;datetime&#x27;: overdue at the exact instant. | [optional]
**tz** | **object** | IANA zone name the due was stated in. Defaults to the request timezone, then the agent&#x27;s, then UTC. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

