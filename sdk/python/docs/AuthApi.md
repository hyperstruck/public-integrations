# hyperstruck.AuthApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**logout_auth_logout_post**](AuthApi.md#logout_auth_logout_post) | **POST** /auth/logout | Logout
[**me_me_get**](AuthApi.md#me_me_get) | **GET** /me | Me
[**workos_callback_auth_sso_callback_get**](AuthApi.md#workos_callback_auth_sso_callback_get) | **GET** /auth/sso/callback | Workos Callback
[**workos_login_auth_sso_login_get**](AuthApi.md#workos_login_auth_sso_login_get) | **GET** /auth/sso/login | Workos Login

# **logout_auth_logout_post**
> object logout_auth_logout_post()

Logout

Clear the session cookie and return the WorkOS logout URL to revoke the session.  Clearing only the cookie leaves the WorkOS session valid until expiry, so a stolen sealed session would still work. We compute the WorkOS logout URL from the current session and return it; the frontend redirects there to actually end the WorkOS session. Safe to call when already signed out (logout_url null).

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AuthApi()

try:
    # Logout
    api_response = api_instance.logout_auth_logout_post()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AuthApi->logout_auth_logout_post: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **me_me_get**
> MeResponse me_me_get()

Me

Return the current portal session: user, active tenant, memberships, scopes.  Portal-session only. API-key callers have no portal identity and are rejected with 403 — they should use the resource APIs directly, not `/me`. A valid session without an active membership surfaces as 403 from the middleware.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AuthApi()

try:
    # Me
    api_response = api_instance.me_me_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AuthApi->me_me_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**MeResponse**](MeResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **workos_callback_auth_sso_callback_get**
> object workos_callback_auth_sso_callback_get(code=code, state=state)

Workos Callback

Complete login: exchange the WorkOS code and issue the session cookie.  The backend owns the code exchange (the WorkOS secret never reaches the browser). The `state` is HMAC-signed and carries a CSRF nonce + landing path; the signature must verify AND the nonce must match the host-only pre-login cookie (double-submit) or the callback is rejected. On authorized or pending-admin-assignment it sets the HTTP-only sealed-session cookie and 303-redirects to the frontend; the frontend's `/me` call then decides app vs. pending UI. Every response clears the one-shot state cookie.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AuthApi()
code = NULL # object |  (optional)
state = NULL # object |  (optional)

try:
    # Workos Callback
    api_response = api_instance.workos_callback_auth_sso_callback_get(code=code, state=state)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AuthApi->workos_callback_auth_sso_callback_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **code** | [**object**](.md)|  | [optional] 
 **state** | [**object**](.md)|  | [optional] 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **workos_login_auth_sso_login_get**
> object workos_login_auth_sso_login_get(email=email, tenant_hint=tenant_hint, return_to=return_to)

Workos Login

Start the WorkOS AuthKit login hand-off.  Resolves the target WorkOS organization from `tenant_hint` when present and 303-redirects to the AuthKit authorization URL; without a hint, WorkOS resolves the org from the user's identity (no local domain->org map). An unmapped user comes back org-less and is rejected at the callback (no session), so the hand-off is unconditional. `email` is forwarded only as a WorkOS `login_hint`. `return_to` is carried through WorkOS in `state` (open-redirect-validated).

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AuthApi()
email = NULL # object |  (optional)
tenant_hint = NULL # object |  (optional)
return_to = NULL # object |  (optional)

try:
    # Workos Login
    api_response = api_instance.workos_login_auth_sso_login_get(email=email, tenant_hint=tenant_hint, return_to=return_to)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AuthApi->workos_login_auth_sso_login_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **email** | [**object**](.md)|  | [optional] 
 **tenant_hint** | [**object**](.md)|  | [optional] 
 **return_to** | [**object**](.md)|  | [optional] 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

