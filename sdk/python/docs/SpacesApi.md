# hyperstruck.SpacesApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**clear_space_external_registration_endpoint_spaces_space_id_external_registration_delete**](SpacesApi.md#clear_space_external_registration_endpoint_spaces_space_id_external_registration_delete) | **DELETE** /spaces/{space_id}/external-registration | Clear Space External Registration
[**create_space_endpoint_spaces_post**](SpacesApi.md#create_space_endpoint_spaces_post) | **POST** /spaces | Create Space
[**delete_space_endpoint_spaces_space_id_delete**](SpacesApi.md#delete_space_endpoint_spaces_space_id_delete) | **DELETE** /spaces/{space_id} | Delete Space
[**list_spaces_endpoint_spaces_get**](SpacesApi.md#list_spaces_endpoint_spaces_get) | **GET** /spaces | List Spaces
[**set_space_external_registration_endpoint_spaces_space_id_external_registration_put**](SpacesApi.md#set_space_external_registration_endpoint_spaces_space_id_external_registration_put) | **PUT** /spaces/{space_id}/external-registration | Set Space External Registration

# **clear_space_external_registration_endpoint_spaces_space_id_external_registration_delete**
> SpaceResponse clear_space_external_registration_endpoint_spaces_space_id_external_registration_delete(space_id)

Clear Space External Registration

Unregister a domain space, so the external container it mirrored resolves to nothing and its identifier is free for another space to take. Requires an API key with the `agents:write` scope and publish rights on the space. Returns the space as it now stands rather than 204, so a connector that unregisters and re-registers needs one round trip rather than two. Clearing a space that carries no registration succeeds and writes no audit row, so a retry is safe. Rejected with 400 for any space that is not `kind='domain'`.

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
api_instance = hyperstruck.SpacesApi(hyperstruck.ApiClient(configuration))
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # Clear Space External Registration
    api_response = api_instance.clear_space_external_registration_endpoint_spaces_space_id_external_registration_delete(space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpacesApi->clear_space_external_registration_endpoint_spaces_space_id_external_registration_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

[**SpaceResponse**](SpaceResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_space_endpoint_spaces_post**
> SpaceResponse create_space_endpoint_spaces_post(body)

Create Space

Create a domain space programmatically, so a connector or a test harness can provision its own container rather than waiting on someone to click. Requires an API key with the `spaces:write` scope and all-spaces reach; a key confined to selected spaces cannot create new ones. The creating key becomes the space's provisioner, which is what lets it delete the space again later. People use `POST /org/{org_id}/spaces` instead, which makes the creator a steward; a space created here is stewarded by the organization's admins.

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
api_instance = hyperstruck.SpacesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.CreateSpaceRequest() # CreateSpaceRequest |

try:
    # Create Space
    api_response = api_instance.create_space_endpoint_spaces_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpacesApi->create_space_endpoint_spaces_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CreateSpaceRequest**](CreateSpaceRequest.md)|  |

### Return type

[**SpaceResponse**](SpaceResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_space_endpoint_spaces_space_id_delete**
> delete_space_endpoint_spaces_space_id_delete(space_id)

Delete Space

Permanently delete a domain space this key created. Requires the `spaces:write` scope and provisioner rights, which a key holds only on spaces it provisioned itself: a key cannot delete a space a person made, or one another key made. Rejected with 409 while the space still homes agents, so a caller tears its agents down first; only `kind='domain'` spaces are deletable, as on the portal route. People delete spaces through `DELETE /org/{org_id}/spaces/{space_id}`, which asks for steward instead.

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
api_instance = hyperstruck.SpacesApi(hyperstruck.ApiClient(configuration))
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # Delete Space
    api_instance.delete_space_endpoint_spaces_space_id_delete(space_id)
except ApiException as e:
    print("Exception when calling SpacesApi->delete_space_endpoint_spaces_space_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_spaces_endpoint_spaces_get**
> SpaceListResponse list_spaces_endpoint_spaces_get(limit=limit, cursor=cursor, _for=_for, external_system=external_system, external_id=external_id)

List Spaces

List spaces in the active tenant. Default (`for=read`) returns spaces the caller can read. Pass `for=publish` for spaces the caller may publish to (agent home-space picker). When `for=publish`, personal spaces owned by other users are excluded.  Supply `external_system` and `external_id` together to resolve a registered external container to the space that mirrors it. An id that is registered nowhere, registered in another organization, or registered on a space you cannot read all return an empty list.

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
api_instance = hyperstruck.SpacesApi(hyperstruck.ApiClient(configuration))
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)
_for = read # object | `read` (default): readable spaces. `publish`: spaces the caller may publish to (home-space picker). (optional) (default to read)
external_system = NULL # object | With `external_id`, resolve a registered external container to its space. Matched lower-cased; both parameters are required together. (optional)
external_id = NULL # object | With `external_system`, the registered identifier to resolve. Matched verbatim, so case matters. (optional)

try:
    # List Spaces
    api_response = api_instance.list_spaces_endpoint_spaces_get(limit=limit, cursor=cursor, _for=_for, external_system=external_system, external_id=external_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpacesApi->list_spaces_endpoint_spaces_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **_for** | [**object**](.md)| &#x60;read&#x60; (default): readable spaces. &#x60;publish&#x60;: spaces the caller may publish to (home-space picker). | [optional] [default to read]
 **external_system** | [**object**](.md)| With &#x60;external_id&#x60;, resolve a registered external container to its space. Matched lower-cased; both parameters are required together. | [optional]
 **external_id** | [**object**](.md)| With &#x60;external_system&#x60;, the registered identifier to resolve. Matched verbatim, so case matters. | [optional]

### Return type

[**SpaceListResponse**](SpaceListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **set_space_external_registration_endpoint_spaces_space_id_external_registration_put**
> SpaceResponse set_space_external_registration_endpoint_spaces_space_id_external_registration_put(body, space_id)

Set Space External Registration

Register or re-point the external container a domain space mirrors, so a connector can keep the mapping current itself. Requires an API key with the `agents:write` scope and publish rights on the space; portal sessions use `PATCH /org/{org_id}/spaces/{space_id}` instead. The registration moves as one value: send `registration` carrying both members. To unregister, send `DELETE` to this same path. Rejected with 409 when another space in the organization already holds that registration, and with 400 for any space that is not `kind='domain'`. Re-asserting the registration the space already carries succeeds and writes no audit row.

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
api_instance = hyperstruck.SpacesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.UpdateSpaceRegistrationRequest() # UpdateSpaceRegistrationRequest |
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # Set Space External Registration
    api_response = api_instance.set_space_external_registration_endpoint_spaces_space_id_external_registration_put(body, space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpacesApi->set_space_external_registration_endpoint_spaces_space_id_external_registration_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**UpdateSpaceRegistrationRequest**](UpdateSpaceRegistrationRequest.md)|  |
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

[**SpaceResponse**](SpaceResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

