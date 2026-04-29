# hyperstruck.SessionsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_agent_sessions_endpoint_agents_agent_id_sessions_get**](SessionsApi.md#list_agent_sessions_endpoint_agents_agent_id_sessions_get) | **GET** /agents/{agent_id}/sessions | List Agent Sessions
[**list_session_messages_endpoint_sessions_session_id_messages_get**](SessionsApi.md#list_session_messages_endpoint_sessions_session_id_messages_get) | **GET** /sessions/{session_id}/messages | List Session Messages
[**list_session_runs_endpoint_sessions_session_id_runs_get**](SessionsApi.md#list_session_runs_endpoint_sessions_session_id_runs_get) | **GET** /sessions/{session_id}/runs | List Session Runs

# **list_agent_sessions_endpoint_agents_agent_id_sessions_get**
> SessionListResponse list_agent_sessions_endpoint_agents_agent_id_sessions_get(agent_id, limit=limit, cursor=cursor)

List Agent Sessions

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.SessionsApi()
agent_id = NULL # object | 
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Agent Sessions
    api_response = api_instance.list_agent_sessions_endpoint_agents_agent_id_sessions_get(agent_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SessionsApi->list_agent_sessions_endpoint_agents_agent_id_sessions_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **limit** | [**object**](.md)| Page size. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**SessionListResponse**](SessionListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_session_messages_endpoint_sessions_session_id_messages_get**
> SessionMessageListResponse list_session_messages_endpoint_sessions_session_id_messages_get(session_id, limit=limit, cursor=cursor)

List Session Messages

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.SessionsApi()
session_id = NULL # object | 
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Session Messages
    api_response = api_instance.list_session_messages_endpoint_sessions_session_id_messages_get(session_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SessionsApi->list_session_messages_endpoint_sessions_session_id_messages_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | [**object**](.md)|  | 
 **limit** | [**object**](.md)| Page size. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**SessionMessageListResponse**](SessionMessageListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_session_runs_endpoint_sessions_session_id_runs_get**
> RunListResponse list_session_runs_endpoint_sessions_session_id_runs_get(session_id, limit=limit, cursor=cursor)

List Session Runs

List runs in a session (newest first), keyset-paginated.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.SessionsApi()
session_id = NULL # object | 
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Session Runs
    api_response = api_instance.list_session_runs_endpoint_sessions_session_id_runs_get(session_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SessionsApi->list_session_runs_endpoint_sessions_session_id_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | [**object**](.md)|  | 
 **limit** | [**object**](.md)| Page size. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**RunListResponse**](RunListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

