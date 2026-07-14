# hyperstruck.ProviderCredentialsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_credential_credentials_providers_post**](ProviderCredentialsApi.md#create_credential_credentials_providers_post) | **POST** /credentials/providers | Create Provider Credential
[**delete_credential_credentials_providers_credential_id_delete**](ProviderCredentialsApi.md#delete_credential_credentials_providers_credential_id_delete) | **DELETE** /credentials/providers/{credential_id} | Delete Provider Credential
[**get_credential_credentials_providers_credential_id_get**](ProviderCredentialsApi.md#get_credential_credentials_providers_credential_id_get) | **GET** /credentials/providers/{credential_id} | Get Provider Credential
[**list_credentials_credentials_providers_get**](ProviderCredentialsApi.md#list_credentials_credentials_providers_get) | **GET** /credentials/providers | List Provider Credentials
[**update_credential_credentials_providers_credential_id_patch**](ProviderCredentialsApi.md#update_credential_credentials_providers_credential_id_patch) | **PATCH** /credentials/providers/{credential_id} | Update Provider Credential

# **create_credential_credentials_providers_post**
> ProviderCredentialResponse create_credential_credentials_providers_post(body)

Create Provider Credential

Store a provider credential for tenant-wide or agent-specific use. The secret is write-only and is not returned. Use `metadata.base_url` only when the provider should use a non-default compatible endpoint.

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
api_instance = hyperstruck.ProviderCredentialsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ProviderCredentialCreateRequest() # ProviderCredentialCreateRequest |

try:
    # Create Provider Credential
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

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_credential_credentials_providers_credential_id_delete**
> delete_credential_credentials_providers_credential_id_delete(credential_id)

Delete Provider Credential

Permanently remove a provider credential. Confirm dependent agents have another usable credential before deleting it.

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
api_instance = hyperstruck.ProviderCredentialsApi(hyperstruck.ApiClient(configuration))
credential_id = NULL # object | Provider credential UUID returned by the create or list endpoint.

try:
    # Delete Provider Credential
    api_instance.delete_credential_credentials_providers_credential_id_delete(credential_id)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->delete_credential_credentials_providers_credential_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **credential_id** | [**object**](.md)| Provider credential UUID returned by the create or list endpoint. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_credential_credentials_providers_credential_id_get**
> ProviderCredentialResponse get_credential_credentials_providers_credential_id_get(credential_id)

Get Provider Credential

Retrieve one provider credential's provider, binding, metadata, and active state. Secret material is never included.

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
api_instance = hyperstruck.ProviderCredentialsApi(hyperstruck.ApiClient(configuration))
credential_id = NULL # object | Provider credential UUID returned by the create or list endpoint.

try:
    # Get Provider Credential
    api_response = api_instance.get_credential_credentials_providers_credential_id_get(credential_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->get_credential_credentials_providers_credential_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **credential_id** | [**object**](.md)| Provider credential UUID returned by the create or list endpoint. |

### Return type

[**ProviderCredentialResponse**](ProviderCredentialResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_credentials_credentials_providers_get**
> ProviderCredentialListResponse list_credentials_credentials_providers_get(provider=provider, binding_type=binding_type, agent_id=agent_id, include_inactive=include_inactive)

List Provider Credentials

List configured model-provider credentials without secret values. Filter by provider, binding type, agent, or active state when selecting a credential for an agent.

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
api_instance = hyperstruck.ProviderCredentialsApi(hyperstruck.ApiClient(configuration))
provider = NULL # object |  (optional)
binding_type = NULL # object |  (optional)
agent_id = NULL # object |  (optional)
include_inactive = false # object |  (optional) (default to false)

try:
    # List Provider Credentials
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

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_credential_credentials_providers_credential_id_patch**
> ProviderCredentialResponse update_credential_credentials_providers_credential_id_patch(body, credential_id)

Update Provider Credential

Update selected fields on a provider credential. Omit the secret to keep the current value. Omitted metadata is preserved; provider changes use that provider's default endpoint unless a base URL is supplied.

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
api_instance = hyperstruck.ProviderCredentialsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ProviderCredentialUpdateRequest() # ProviderCredentialUpdateRequest |
credential_id = NULL # object | Provider credential UUID returned by the create or list endpoint.

try:
    # Update Provider Credential
    api_response = api_instance.update_credential_credentials_providers_credential_id_patch(body, credential_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ProviderCredentialsApi->update_credential_credentials_providers_credential_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ProviderCredentialUpdateRequest**](ProviderCredentialUpdateRequest.md)|  |
 **credential_id** | [**object**](.md)| Provider credential UUID returned by the create or list endpoint. |

### Return type

[**ProviderCredentialResponse**](ProviderCredentialResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

