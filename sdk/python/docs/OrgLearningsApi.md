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

# create an instance of the API class
api_instance = hyperstruck.OrgLearningsApi()
limit = 50 # object | Page size. (optional) (default to 50)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

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
 **limit** | [**object**](.md)| Page size. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**OrgLearningListResponse**](OrgLearningListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

