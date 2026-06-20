# hyperstruck.AdminIdentityApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_identity_provider_admin_tenants_tenant_id_identity_provider_post**](AdminIdentityApi.md#create_identity_provider_admin_tenants_tenant_id_identity_provider_post) | **POST** /admin/tenants/{tenant_id}/identity-provider | Create Identity Provider
[**create_member_admin_tenants_tenant_id_members_post**](AdminIdentityApi.md#create_member_admin_tenants_tenant_id_members_post) | **POST** /admin/tenants/{tenant_id}/members | Create Member
[**create_portal_link_admin_tenants_tenant_id_identity_provider_portal_links_post**](AdminIdentityApi.md#create_portal_link_admin_tenants_tenant_id_identity_provider_portal_links_post) | **POST** /admin/tenants/{tenant_id}/identity-provider/portal-links | Create Portal Link
[**workos_webhook_webhooks_workos_post**](AdminIdentityApi.md#workos_webhook_webhooks_workos_post) | **POST** /webhooks/workos | Workos Webhook

# **create_identity_provider_admin_tenants_tenant_id_identity_provider_post**
> WorkOSOrganizationLinkResponse create_identity_provider_admin_tenants_tenant_id_identity_provider_post(body, tenant_id)

Create Identity Provider

Create a WorkOS Organization for the tenant and map it.  Requires the `identity:admin:write` scope. Creates a WorkOS Organization with `external_id = tenant_id`, then stores the mapping (status `pending_setup`) through admin impersonation. Creates real WorkOS state.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AdminIdentityApi()
body = hyperstruck.WorkOSOrganizationLinkRequest() # WorkOSOrganizationLinkRequest | 
tenant_id = NULL # object | 

try:
    # Create Identity Provider
    api_response = api_instance.create_identity_provider_admin_tenants_tenant_id_identity_provider_post(body, tenant_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AdminIdentityApi->create_identity_provider_admin_tenants_tenant_id_identity_provider_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**WorkOSOrganizationLinkRequest**](WorkOSOrganizationLinkRequest.md)|  | 
 **tenant_id** | [**object**](.md)|  | 

### Return type

[**WorkOSOrganizationLinkResponse**](WorkOSOrganizationLinkResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_member_admin_tenants_tenant_id_members_post**
> AdminMembershipResponse create_member_admin_tenants_tenant_id_members_post(body, tenant_id)

Create Member

Manually assign a tenant membership (admin-provisioned).  Requires the `identity:admin:write` scope. Creates the identity user by email if needed and upserts the membership (`provisioning_source = 'hyperstruck_admin'`) through admin impersonation. Used to seed the first owner before SSO, or whenever JIT is disabled.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AdminIdentityApi()
body = hyperstruck.AdminMembershipRequest() # AdminMembershipRequest | 
tenant_id = NULL # object | 

try:
    # Create Member
    api_response = api_instance.create_member_admin_tenants_tenant_id_members_post(body, tenant_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AdminIdentityApi->create_member_admin_tenants_tenant_id_members_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AdminMembershipRequest**](AdminMembershipRequest.md)|  | 
 **tenant_id** | [**object**](.md)|  | 

### Return type

[**AdminMembershipResponse**](AdminMembershipResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_portal_link_admin_tenants_tenant_id_identity_provider_portal_links_post**
> WorkOSPortalLinkResponse create_portal_link_admin_tenants_tenant_id_identity_provider_portal_links_post(body, tenant_id)

Create Portal Link

Generate a WorkOS Admin Portal link for the tenant's organization.  Requires the `identity:admin:write` scope. Returns a link to hand customer IT for domain verification / SSO setup (`intent` = `sso` or `domain_verification`). Responds 404 if the tenant has no WorkOS organization mapping yet.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AdminIdentityApi()
body = hyperstruck.WorkOSPortalLinkRequest() # WorkOSPortalLinkRequest | 
tenant_id = NULL # object | 

try:
    # Create Portal Link
    api_response = api_instance.create_portal_link_admin_tenants_tenant_id_identity_provider_portal_links_post(body, tenant_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AdminIdentityApi->create_portal_link_admin_tenants_tenant_id_identity_provider_portal_links_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**WorkOSPortalLinkRequest**](WorkOSPortalLinkRequest.md)|  | 
 **tenant_id** | [**object**](.md)|  | 

### Return type

[**WorkOSPortalLinkResponse**](WorkOSPortalLinkResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **workos_webhook_webhooks_workos_post**
> object workos_webhook_webhooks_workos_post(work_os_signature=work_os_signature)

Workos Webhook

Receive and verify WorkOS webhook events.  Public but signature-verified via the `WorkOS-Signature` header against `HYPER_WORKOS__WEBHOOK_SECRET`. Reconciles provider connection status for an already-mapped organization only; never grants tenant access on its own.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AdminIdentityApi()
work_os_signature = NULL # object |  (optional)

try:
    # Workos Webhook
    api_response = api_instance.workos_webhook_webhooks_workos_post(work_os_signature=work_os_signature)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AdminIdentityApi->workos_webhook_webhooks_workos_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **work_os_signature** | [**object**](.md)|  | [optional] 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

