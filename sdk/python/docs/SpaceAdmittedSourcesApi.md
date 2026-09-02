# hyperstruck.SpaceAdmittedSourcesApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**admit_source_endpoint_org_org_id_spaces_space_id_admitted_sources_post**](SpaceAdmittedSourcesApi.md#admit_source_endpoint_org_org_id_spaces_space_id_admitted_sources_post) | **POST** /org/{org_id}/spaces/{space_id}/admitted-sources | Admit a declared source in this space
[**list_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_get**](SpaceAdmittedSourcesApi.md#list_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_get) | **GET** /org/{org_id}/spaces/{space_id}/admitted-sources | List the grant history for this space
[**reconcile_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_reconciliation_get**](SpaceAdmittedSourcesApi.md#reconcile_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_reconciliation_get) | **GET** /org/{org_id}/spaces/{space_id}/admitted-sources/reconciliation | Reconcile declared sources against grants
[**renew_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_renew_post**](SpaceAdmittedSourcesApi.md#renew_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_renew_post) | **POST** /org/{org_id}/spaces/{space_id}/admitted-sources/{source_id}/renew | Renew a live admission
[**revoke_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_revoke_post**](SpaceAdmittedSourcesApi.md#revoke_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_revoke_post) | **POST** /org/{org_id}/spaces/{space_id}/admitted-sources/{source_id}/revoke | Revoke a live admission

# **admit_source_endpoint_org_org_id_spaces_space_id_admitted_sources_post**
> AdmittedSourceGrant admit_source_endpoint_org_org_id_spaces_space_id_admitted_sources_post(body, org_id, space_id)

Admit a declared source in this space

Record that content bearing this source id is not attacker-reachable within this space, so facts harvested from it are no longer held for review on arrival. Requires space steward. Refused with 409 when a live admission already covers the pair, which is a renewal. The response carries how far the grant reaches, because a grant in the shared tenant space reaches every account in it. It applies to facts harvested from now on: the rank a claim was minted with is permanent, so a backlog already held for review stays held.

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
api_instance = hyperstruck.SpaceAdmittedSourcesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.AdmitSourceRequest() # AdmitSourceRequest |
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal 'commons' for the organization's shared space.

try:
    # Admit a declared source in this space
    api_response = api_instance.admit_source_endpoint_org_org_id_spaces_space_id_admitted_sources_post(body, org_id, space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpaceAdmittedSourcesApi->admit_source_endpoint_org_org_id_spaces_space_id_admitted_sources_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AdmitSourceRequest**](AdmitSourceRequest.md)|  |
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal &#x27;commons&#x27; for the organization&#x27;s shared space. |

### Return type

[**AdmittedSourceGrant**](AdmittedSourceGrant.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_get**
> AdmittedSourceListResponse list_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_get(org_id, space_id, limit=limit, cursor=cursor)

List the grant history for this space

Every grant, renewal and revocation, newest first. History rather than current state: the window a given fact was admitted under stays readable after the grant has been renewed.

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
api_instance = hyperstruck.SpaceAdmittedSourcesApi(hyperstruck.ApiClient(configuration))
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal 'commons' for the organization's shared space.
limit = 50 # object | Maximum grants to return in this page. (optional) (default to 50)
cursor = NULL # object | Opaque page cursor from a previous response. Treat it as opaque: its encoding is not part of the contract. (optional)

try:
    # List the grant history for this space
    api_response = api_instance.list_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_get(org_id, space_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpaceAdmittedSourcesApi->list_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal &#x27;commons&#x27; for the organization&#x27;s shared space. |
 **limit** | [**object**](.md)| Maximum grants to return in this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque page cursor from a previous response. Treat it as opaque: its encoding is not part of the contract. | [optional]

### Return type

[**AdmittedSourceListResponse**](AdmittedSourceListResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reconcile_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_reconciliation_get**
> ReconciliationResponse reconcile_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_reconciliation_get(org_id, space_id, cursor=cursor, limit=limit)

Reconcile declared sources against grants

The sources this space's facts actually declare, set against the grants made here, and where the two disagree: a source arriving with no grant explains why its facts are held, and a grant matching nothing is a typo or a connector not yet live. Also reports how far a grant in this space reaches, since a grant in the shared tenant space reaches every account.

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
api_instance = hyperstruck.SpaceAdmittedSourcesApi(hyperstruck.ApiClient(configuration))
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal 'commons' for the organization's shared space.
cursor = NULL # object | Opaque page cursor from a previous response. Treat it as opaque: its encoding is not part of the contract. (optional)
limit = 500 # object | Sources per page. The paged shape existed with no caller but the tests, which is how a page nobody requests goes untried until a customer requests one. (optional) (default to 500)

try:
    # Reconcile declared sources against grants
    api_response = api_instance.reconcile_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_reconciliation_get(org_id, space_id, cursor=cursor, limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpaceAdmittedSourcesApi->reconcile_admitted_sources_endpoint_org_org_id_spaces_space_id_admitted_sources_reconciliation_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal &#x27;commons&#x27; for the organization&#x27;s shared space. |
 **cursor** | [**object**](.md)| Opaque page cursor from a previous response. Treat it as opaque: its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)| Sources per page. The paged shape existed with no caller but the tests, which is how a page nobody requests goes untried until a customer requests one. | [optional] [default to 500]

### Return type

[**ReconciliationResponse**](ReconciliationResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **renew_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_renew_post**
> AdmittedSource renew_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_renew_post(body, org_id, space_id, source_id)

Renew a live admission

Supersede the live grant and record its successor, extending from now rather than from the old expiry. Any steward of the space may renew what another steward granted.

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
api_instance = hyperstruck.SpaceAdmittedSourcesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.RenewAdmissionRequest() # RenewAdmissionRequest |
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal 'commons' for the organization's shared space.
source_id = NULL # object | The source id a caller declares on corpus evidence, exactly as declared. Compared verbatim, so case matters and surrounding whitespace is stripped.

try:
    # Renew a live admission
    api_response = api_instance.renew_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_renew_post(body, org_id, space_id, source_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpaceAdmittedSourcesApi->renew_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_renew_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**RenewAdmissionRequest**](RenewAdmissionRequest.md)|  |
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal &#x27;commons&#x27; for the organization&#x27;s shared space. |
 **source_id** | [**object**](.md)| The source id a caller declares on corpus evidence, exactly as declared. Compared verbatim, so case matters and surrounding whitespace is stripped. |

### Return type

[**AdmittedSource**](AdmittedSource.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **revoke_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_revoke_post**
> AdmittedSource revoke_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_revoke_post(body, org_id, space_id, source_id)

Revoke a live admission

Withdraw the grant, naming why. Terminal and never a delete: facts already admitted keep the standing they were written with, and the record of who withdrew it survives.

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
api_instance = hyperstruck.SpaceAdmittedSourcesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.RevokeAdmissionRequest() # RevokeAdmissionRequest |
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal 'commons' for the organization's shared space.
source_id = NULL # object | The source id a caller declares on corpus evidence, exactly as declared. Compared verbatim, so case matters and surrounding whitespace is stripped.

try:
    # Revoke a live admission
    api_response = api_instance.revoke_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_revoke_post(body, org_id, space_id, source_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpaceAdmittedSourcesApi->revoke_admitted_source_endpoint_org_org_id_spaces_space_id_admitted_sources_source_id_revoke_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**RevokeAdmissionRequest**](RevokeAdmissionRequest.md)|  |
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space identifier as the authorization layer and the fact store both hold it: the space UUID, or the literal &#x27;commons&#x27; for the organization&#x27;s shared space. |
 **source_id** | [**object**](.md)| The source id a caller declares on corpus evidence, exactly as declared. Compared verbatim, so case matters and surrounding whitespace is stripped. |

### Return type

[**AdmittedSource**](AdmittedSource.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

