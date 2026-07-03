# hyperstruck.ApiKeysApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_api_key_endpoint_api_keys_post**](ApiKeysApi.md#create_api_key_endpoint_api_keys_post) | **POST** /api-keys | Create Api Key Endpoint
[**list_api_keys_endpoint_api_keys_get**](ApiKeysApi.md#list_api_keys_endpoint_api_keys_get) | **GET** /api-keys | List Api Keys Endpoint
[**revoke_api_key_endpoint_api_keys_api_key_id_revoke_post**](ApiKeysApi.md#revoke_api_key_endpoint_api_keys_api_key_id_revoke_post) | **POST** /api-keys/{api_key_id}/revoke | Revoke Api Key Endpoint

# **create_api_key_endpoint_api_keys_post**
> ApiKeyCreateResponse create_api_key_endpoint_api_keys_post(body)

Create Api Key Endpoint

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ApiKeysApi()
body = hyperstruck.ApiKeyCreateRequest() # ApiKeyCreateRequest | 

try:
    # Create Api Key Endpoint
    api_response = api_instance.create_api_key_endpoint_api_keys_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ApiKeysApi->create_api_key_endpoint_api_keys_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ApiKeyCreateRequest**](ApiKeyCreateRequest.md)|  | 

### Return type

[**ApiKeyCreateResponse**](ApiKeyCreateResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_api_keys_endpoint_api_keys_get**
> ApiKeyListResponse list_api_keys_endpoint_api_keys_get()

List Api Keys Endpoint

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ApiKeysApi()

try:
    # List Api Keys Endpoint
    api_response = api_instance.list_api_keys_endpoint_api_keys_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ApiKeysApi->list_api_keys_endpoint_api_keys_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**ApiKeyListResponse**](ApiKeyListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **revoke_api_key_endpoint_api_keys_api_key_id_revoke_post**
> ApiKeyRevokeResponse revoke_api_key_endpoint_api_keys_api_key_id_revoke_post(api_key_id)

Revoke Api Key Endpoint

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ApiKeysApi()
api_key_id = NULL # object | 

try:
    # Revoke Api Key Endpoint
    api_response = api_instance.revoke_api_key_endpoint_api_keys_api_key_id_revoke_post(api_key_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ApiKeysApi->revoke_api_key_endpoint_api_keys_api_key_id_revoke_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **api_key_id** | [**object**](.md)|  | 

### Return type

[**ApiKeyRevokeResponse**](ApiKeyRevokeResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

