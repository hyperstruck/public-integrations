# hyperstruck.ProviderCredentialsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_credential_credentials_providers_post**](ProviderCredentialsApi.md#create_credential_credentials_providers_post) | **POST** /credentials/providers | Create Credential
[**delete_credential_credentials_providers_credential_id_delete**](ProviderCredentialsApi.md#delete_credential_credentials_providers_credential_id_delete) | **DELETE** /credentials/providers/{credential_id} | Delete Credential
[**get_credential_credentials_providers_credential_id_get**](ProviderCredentialsApi.md#get_credential_credentials_providers_credential_id_get) | **GET** /credentials/providers/{credential_id} | Get Credential
[**list_credentials_credentials_providers_get**](ProviderCredentialsApi.md#list_credentials_credentials_providers_get) | **GET** /credentials/providers | List Credentials
[**update_credential_credentials_providers_credential_id_patch**](ProviderCredentialsApi.md#update_credential_credentials_providers_credential_id_patch) | **PATCH** /credentials/providers/{credential_id} | Update Credential

# **create_credential_credentials_providers_post**
> ProviderCredentialResponse create_credential_credentials_providers_post(body)

Create Credential

Create an encrypted provider credential. Use `metadata.base_url` to override the provider endpoint. If omitted, the API stores a sane provider default for Anthropic, Groq, Ollama, and OpenAI.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ProviderCredentialsApi()
body = hyperstruck.ProviderCredentialCreateRequest() # ProviderCredentialCreateRequest | 

try:
    # Create Credential
    api_response = api_instance.create_credential_credentials_providers_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->create_credential_credentials_providers_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ProviderCredentialCreateRequest**](ProviderCredentialCreateRequest.md)|  | 

### Return type

[**ProviderCredentialResponse**](ProviderCredentialResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_credential_credentials_providers_credential_id_delete**
> delete_credential_credentials_providers_credential_id_delete(credential_id)

Delete Credential

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ProviderCredentialsApi()
credential_id = NULL # object | 

try:
    # Delete Credential
    api_instance.delete_credential_credentials_providers_credential_id_delete(credential_id)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->delete_credential_credentials_providers_credential_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **credential_id** | [**object**](.md)|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_credential_credentials_providers_credential_id_get**
> ProviderCredentialResponse get_credential_credentials_providers_credential_id_get(credential_id)

Get Credential

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ProviderCredentialsApi()
credential_id = NULL # object | 

try:
    # Get Credential
    api_response = api_instance.get_credential_credentials_providers_credential_id_get(credential_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->get_credential_credentials_providers_credential_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **credential_id** | [**object**](.md)|  | 

### Return type

[**ProviderCredentialResponse**](ProviderCredentialResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_credentials_credentials_providers_get**
> ProviderCredentialListResponse list_credentials_credentials_providers_get(provider=provider, binding_type=binding_type, agent_id=agent_id, include_inactive=include_inactive)

List Credentials

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ProviderCredentialsApi()
provider = NULL # object |  (optional)
binding_type = NULL # object |  (optional)
agent_id = NULL # object |  (optional)
include_inactive = false # object |  (optional) (default to false)

try:
    # List Credentials
    api_response = api_instance.list_credentials_credentials_providers_get(provider=provider, binding_type=binding_type, agent_id=agent_id, include_inactive=include_inactive)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->list_credentials_credentials_providers_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider** | [**object**](.md)|  | [optional] 
 **binding_type** | [**object**](.md)|  | [optional] 
 **agent_id** | [**object**](.md)|  | [optional] 
 **include_inactive** | [**object**](.md)|  | [optional] [default to false]

### Return type

[**ProviderCredentialListResponse**](ProviderCredentialListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_credential_credentials_providers_credential_id_patch**
> ProviderCredentialResponse update_credential_credentials_providers_credential_id_patch(body, credential_id)

Update Credential

Update an encrypted provider credential. If `metadata` is omitted, the existing endpoint is preserved; if the provider changes without explicit metadata, or metadata is provided without a base URL, the endpoint resets to a sane provider default.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.ProviderCredentialsApi()
body = hyperstruck.ProviderCredentialUpdateRequest() # ProviderCredentialUpdateRequest | 
credential_id = NULL # object | 

try:
    # Update Credential
    api_response = api_instance.update_credential_credentials_providers_credential_id_patch(body, credential_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->update_credential_credentials_providers_credential_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ProviderCredentialUpdateRequest**](ProviderCredentialUpdateRequest.md)|  | 
 **credential_id** | [**object**](.md)|  | 

### Return type

[**ProviderCredentialResponse**](ProviderCredentialResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

