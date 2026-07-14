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

List conversation sessions associated with one agent. Results are cursor-paginated; pass `next_cursor` back unchanged to continue.

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
api_instance = hyperstruck.SessionsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
limit = 20 # object | Maximum number of items to return on this page. (optional) (default to 20)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**SessionListResponse**](SessionListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_session_messages_endpoint_sessions_session_id_messages_get**
> SessionMessageListResponse list_session_messages_endpoint_sessions_session_id_messages_get(session_id, limit=limit, cursor=cursor)

List Session Messages

Read the messages in one conversation session. Results are ordered for transcript consumption and cursor-paginated for long sessions.

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
api_instance = hyperstruck.SessionsApi(hyperstruck.ApiClient(configuration))
session_id = NULL # object | Conversation session UUID associated with an agent.
limit = 20 # object | Maximum number of items to return on this page. (optional) (default to 20)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

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
 **session_id** | [**object**](.md)| Conversation session UUID associated with an agent. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**SessionMessageListResponse**](SessionMessageListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_session_runs_endpoint_sessions_session_id_runs_get**
> RunListResponse list_session_runs_endpoint_sessions_session_id_runs_get(session_id, limit=limit, cursor=cursor)

List Session Runs

List the hosted runs associated with one conversation session, newest first. Use the returned run UUIDs to inspect individual run details.

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
api_instance = hyperstruck.SessionsApi(hyperstruck.ApiClient(configuration))
session_id = NULL # object | Conversation session UUID associated with an agent.
limit = 20 # object | Maximum number of items to return on this page. (optional) (default to 20)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

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
 **session_id** | [**object**](.md)| Conversation session UUID associated with an agent. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**RunListResponse**](RunListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

