# hyperstruck.ApiKeysApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_api_key_endpoint_api_keys_post**](ApiKeysApi.md#create_api_key_endpoint_api_keys_post) | **POST** /api-keys | Create API Key
[**list_api_keys_endpoint_api_keys_get**](ApiKeysApi.md#list_api_keys_endpoint_api_keys_get) | **GET** /api-keys | List API Keys
[**revoke_api_key_endpoint_api_keys_api_key_id_revoke_post**](ApiKeysApi.md#revoke_api_key_endpoint_api_keys_api_key_id_revoke_post) | **POST** /api-keys/{api_key_id}/revoke | Revoke API Key

# **create_api_key_endpoint_api_keys_post**
> ApiKeyCreateResponse create_api_key_endpoint_api_keys_post(body)

Create API Key

Create a tenant API key with explicit scopes. The complete Bearer token is returned only once, so store it securely before leaving the response.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.ApiKeysApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ApiKeyCreateRequest() # ApiKeyCreateRequest |

try:
    # Create API Key
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

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_api_keys_endpoint_api_keys_get**
> ApiKeyListResponse list_api_keys_endpoint_api_keys_get()

List API Keys

List API keys for the active tenant without revealing their secret values. Use this portal-session endpoint to review key names, prefixes, scopes, and revocation state.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.ApiKeysApi(hyperstruck.ApiClient(configuration))

try:
    # List API Keys
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

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **revoke_api_key_endpoint_api_keys_api_key_id_revoke_post**
> ApiKeyRevokeResponse revoke_api_key_endpoint_api_keys_api_key_id_revoke_post(api_key_id)

Revoke API Key

Permanently revoke an API key so it can no longer authenticate requests. Use the key UUID returned by the list or create endpoint.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.ApiKeysApi(hyperstruck.ApiClient(configuration))
api_key_id = NULL # object | API key UUID returned by the create or list endpoint.

try:
    # Revoke API Key
    api_response = api_instance.revoke_api_key_endpoint_api_keys_api_key_id_revoke_post(api_key_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ApiKeysApi->revoke_api_key_endpoint_api_keys_api_key_id_revoke_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **api_key_id** | [**object**](.md)| API key UUID returned by the create or list endpoint. |

### Return type

[**ApiKeyRevokeResponse**](ApiKeyRevokeResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

