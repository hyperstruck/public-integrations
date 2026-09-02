# hyperstruck.UsageApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get**](UsageApi.md#get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get) | **GET** /agents/{agent_id}/usage/summary | Get Agent Usage Summary
[**get_own_claim_assists_usage_claim_assists_get**](UsageApi.md#get_own_claim_assists_usage_claim_assists_get) | **GET** /usage/claim-assists | Get Claim Assist Counts
[**get_own_usage_summary_usage_summary_get**](UsageApi.md#get_own_usage_summary_usage_summary_get) | **GET** /usage/summary | Get Usage Summary
[**list_own_usage_runs_usage_runs_get**](UsageApi.md#list_own_usage_runs_usage_runs_get) | **GET** /usage/runs | List Usage by Run

# **get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get**
> AgentUsageSummaryResponse get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get(agent_id, window=window)

Get Agent Usage Summary

Return metered usage for one agent over a preset reporting window. Use tenant-level `/usage` endpoints when an all-agent total is required.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.UsageApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window. (optional) (default to last_30_days)

try:
    # Get Agent Usage Summary
    api_response = api_instance.get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get(agent_id, window=window)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling UsageApi->get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **window** | [**UsageTimeWindow**](.md)| Preset reporting window. | [optional] [default to last_30_days]

### Return type

[**AgentUsageSummaryResponse**](AgentUsageSummaryResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_own_claim_assists_usage_claim_assists_get**
> ClaimAssistsResponse get_own_claim_assists_usage_claim_assists_get(window_hours=window_hours)

Get Claim Assist Counts

Return recent counts of duplicate work avoided by idempotent claim handling. Use this operational usage indicator to understand retry and concurrency savings.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.UsageApi(hyperstruck.ApiClient(configuration))
window_hours = 24 # object | Recent lookback window in hours; values are capped at 90 days. (optional) (default to 24)

try:
    # Get Claim Assist Counts
    api_response = api_instance.get_own_claim_assists_usage_claim_assists_get(window_hours=window_hours)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling UsageApi->get_own_claim_assists_usage_claim_assists_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **window_hours** | [**object**](.md)| Recent lookback window in hours; values are capped at 90 days. | [optional] [default to 24]

### Return type

[**ClaimAssistsResponse**](ClaimAssistsResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_own_usage_summary_usage_summary_get**
> UsageSummaryResponse get_own_usage_summary_usage_summary_get(window=window, as_of=as_of)

Get Usage Summary

Return tenant-wide metered usage for a preset reporting window. Use the same `as_of` value with `/usage/runs` to keep totals and pages aligned.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.UsageApi(hyperstruck.ApiClient(configuration))
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window (custom date range not supported in this API version). (optional) (default to last_7_days)
as_of = NULL # object | Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. (optional)

try:
    # Get Usage Summary
    api_response = api_instance.get_own_usage_summary_usage_summary_get(window=window, as_of=as_of)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling UsageApi->get_own_usage_summary_usage_summary_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **window** | [**UsageTimeWindow**](.md)| Preset reporting window (custom date range not supported in this API version). | [optional] [default to last_7_days]
 **as_of** | [**object**](.md)| Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. | [optional]

### Return type

[**UsageSummaryResponse**](UsageSummaryResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_own_usage_runs_usage_runs_get**
> UsageRunListResponse list_own_usage_runs_usage_runs_get(window=window, as_of=as_of, limit=limit, cursor=cursor)

List Usage by Run

List hosted runs contributing to tenant usage in the selected reporting window. Results are cursor-paginated for reconciliation and audit views.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.UsageApi(hyperstruck.ApiClient(configuration))
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window (custom date range not supported in this API version). (optional) (default to last_7_days)
as_of = NULL # object | Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. (optional)
limit = 20 # object | Maximum number of items to return on this page. (optional) (default to 20)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List Usage by Run
    api_response = api_instance.list_own_usage_runs_usage_runs_get(window=window, as_of=as_of, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling UsageApi->list_own_usage_runs_usage_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **window** | [**UsageTimeWindow**](.md)| Preset reporting window (custom date range not supported in this API version). | [optional] [default to last_7_days]
 **as_of** | [**object**](.md)| Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**UsageRunListResponse**](UsageRunListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

