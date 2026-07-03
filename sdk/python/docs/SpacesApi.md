# hyperstruck.SpacesApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_spaces_endpoint_spaces_get**](SpacesApi.md#list_spaces_endpoint_spaces_get) | **GET** /spaces | List Spaces

# **list_spaces_endpoint_spaces_get**
> SpaceListResponse list_spaces_endpoint_spaces_get(limit=limit, cursor=cursor)

List Spaces

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.SpacesApi()
limit = 50 # object | Page size. (optional) (default to 50)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Spaces
    api_response = api_instance.list_spaces_endpoint_spaces_get(limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpacesApi->list_spaces_endpoint_spaces_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Page size. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**SpaceListResponse**](SpaceListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

