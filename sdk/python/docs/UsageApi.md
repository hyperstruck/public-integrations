# hyperstruck.UsageApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_own_usage_summary_usage_summary_get**](UsageApi.md#get_own_usage_summary_usage_summary_get) | **GET** /usage/summary | Get Own Usage Summary
[**get_tenant_usage_summary_admin_usage_tenants_tenant_id_summary_get**](UsageApi.md#get_tenant_usage_summary_admin_usage_tenants_tenant_id_summary_get) | **GET** /usage/tenants/{tenant_id}/summary | Get Tenant Usage Summary Admin
[**list_own_usage_runs_usage_runs_get**](UsageApi.md#list_own_usage_runs_usage_runs_get) | **GET** /usage/runs | List Own Usage Runs
[**list_tenant_usage_runs_admin_usage_tenants_tenant_id_runs_get**](UsageApi.md#list_tenant_usage_runs_admin_usage_tenants_tenant_id_runs_get) | **GET** /usage/tenants/{tenant_id}/runs | List Tenant Usage Runs Admin

# **get_own_usage_summary_usage_summary_get**
> UsageSummaryResponse get_own_usage_summary_usage_summary_get(window=window, as_of=as_of)

Get Own Usage Summary

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.UsageApi()
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window (custom date range not supported in this API version). (optional) (default to last_7_days)
as_of = NULL # object | Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. (optional)

try:
    # Get Own Usage Summary
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

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_tenant_usage_summary_admin_usage_tenants_tenant_id_summary_get**
> UsageSummaryResponse get_tenant_usage_summary_admin_usage_tenants_tenant_id_summary_get(tenant_id, window=window, as_of=as_of)

Get Tenant Usage Summary Admin

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.UsageApi()
tenant_id = NULL # object | 
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window (custom date range not supported in this API version). (optional) (default to last_7_days)
as_of = NULL # object | Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. (optional)

try:
    # Get Tenant Usage Summary Admin
    api_response = api_instance.get_tenant_usage_summary_admin_usage_tenants_tenant_id_summary_get(tenant_id, window=window, as_of=as_of)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling UsageApi->get_tenant_usage_summary_admin_usage_tenants_tenant_id_summary_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **tenant_id** | [**object**](.md)|  | 
 **window** | [**UsageTimeWindow**](.md)| Preset reporting window (custom date range not supported in this API version). | [optional] [default to last_7_days]
 **as_of** | [**object**](.md)| Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. | [optional] 

### Return type

[**UsageSummaryResponse**](UsageSummaryResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_own_usage_runs_usage_runs_get**
> UsageRunListResponse list_own_usage_runs_usage_runs_get(window=window, as_of=as_of, limit=limit, cursor=cursor)

List Own Usage Runs

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.UsageApi()
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window (custom date range not supported in this API version). (optional) (default to last_7_days)
as_of = NULL # object | Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. (optional)
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Own Usage Runs
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
 **limit** | [**object**](.md)| Page size. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**UsageRunListResponse**](UsageRunListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_tenant_usage_runs_admin_usage_tenants_tenant_id_runs_get**
> UsageRunListResponse list_tenant_usage_runs_admin_usage_tenants_tenant_id_runs_get(tenant_id, window=window, as_of=as_of, limit=limit, cursor=cursor)

List Tenant Usage Runs Admin

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.UsageApi()
tenant_id = NULL # object | 
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window (custom date range not supported in this API version). (optional) (default to last_7_days)
as_of = NULL # object | Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. (optional)
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Tenant Usage Runs Admin
    api_response = api_instance.list_tenant_usage_runs_admin_usage_tenants_tenant_id_runs_get(tenant_id, window=window, as_of=as_of, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling UsageApi->list_tenant_usage_runs_admin_usage_tenants_tenant_id_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **tenant_id** | [**object**](.md)|  | 
 **window** | [**UsageTimeWindow**](.md)| Preset reporting window (custom date range not supported in this API version). | [optional] [default to last_7_days]
 **as_of** | [**object**](.md)| Optional UTC timestamp used to anchor the reporting window so summary and paginated run pages stay aligned across requests. | [optional] 
 **limit** | [**object**](.md)| Page size. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**UsageRunListResponse**](UsageRunListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

