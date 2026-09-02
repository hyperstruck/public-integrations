# hyperstruck.OrgLearningsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_org_learnings_endpoint_org_learnings_get**](OrgLearningsApi.md#list_org_learnings_endpoint_org_learnings_get) | **GET** /org/learnings | List org-shared learnings

# **list_org_learnings_endpoint_org_learnings_get**
> OrgLearningListResponse list_org_learnings_endpoint_org_learnings_get(limit=limit, cursor=cursor)

List org-shared learnings

Tenant-wide library of org-promoted (shared) learnings. Enterprise only. Evidence is stripped at promotion time, so items report org_stripped and summarise cross-agent corroboration. promotion_timestamp keyset pagination.

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
api_instance = hyperstruck.OrgLearningsApi(hyperstruck.ApiClient(configuration))
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List org-shared learnings
    api_response = api_instance.list_org_learnings_endpoint_org_learnings_get(limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrgLearningsApi->list_org_learnings_endpoint_org_learnings_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**OrgLearningListResponse**](OrgLearningListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

