# hyperstruck.AgentsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_agent_endpoint_agents_post**](AgentsApi.md#create_agent_endpoint_agents_post) | **POST** /agents | Create Agent
[**delete_agent_endpoint_agents_agent_id_delete**](AgentsApi.md#delete_agent_endpoint_agents_agent_id_delete) | **DELETE** /agents/{agent_id} | Delete Agent
[**dispatch_goal_run_endpoint_agents_agent_id_goals_post**](AgentsApi.md#dispatch_goal_run_endpoint_agents_agent_id_goals_post) | **POST** /agents/{agent_id}/goals | Create Goal Run
[**get_agent_endpoint_agents_agent_id_get**](AgentsApi.md#get_agent_endpoint_agents_agent_id_get) | **GET** /agents/{agent_id} | Get Agent
[**list_agent_sessions_endpoint_agents_agent_id_sessions_get**](AgentsApi.md#list_agent_sessions_endpoint_agents_agent_id_sessions_get) | **GET** /agents/{agent_id}/sessions | List Agent Sessions
[**list_agents_endpoint_agents_get**](AgentsApi.md#list_agents_endpoint_agents_get) | **GET** /agents | List Agents
[**update_agent_endpoint_agents_agent_id_patch**](AgentsApi.md#update_agent_endpoint_agents_agent_id_patch) | **PATCH** /agents/{agent_id} | Update Agent

# **create_agent_endpoint_agents_post**
> AgentResponse create_agent_endpoint_agents_post(body)

Create Agent

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AgentsApi()
body = hyperstruck.AgentCreateRequest() # AgentCreateRequest | 

try:
    # Create Agent
    api_response = api_instance.create_agent_endpoint_agents_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->create_agent_endpoint_agents_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AgentCreateRequest**](AgentCreateRequest.md)|  | 

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_agent_endpoint_agents_agent_id_delete**
> delete_agent_endpoint_agents_agent_id_delete(agent_id)

Delete Agent

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AgentsApi()
agent_id = NULL # object | 

try:
    # Delete Agent
    api_instance.delete_agent_endpoint_agents_agent_id_delete(agent_id)
except ApiException as e:
    print("Exception when calling AgentsApi->delete_agent_endpoint_agents_agent_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **dispatch_goal_run_endpoint_agents_agent_id_goals_post**
> GoalRunAcceptedResponse dispatch_goal_run_endpoint_agents_agent_id_goals_post(body, agent_id)

Create Goal Run

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AgentsApi()
body = hyperstruck.GoalRunRequest() # GoalRunRequest | 
agent_id = NULL # object | 

try:
    # Create Goal Run
    api_response = api_instance.dispatch_goal_run_endpoint_agents_agent_id_goals_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->dispatch_goal_run_endpoint_agents_agent_id_goals_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**GoalRunRequest**](GoalRunRequest.md)|  | 
 **agent_id** | [**object**](.md)|  | 

### Return type

[**GoalRunAcceptedResponse**](GoalRunAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_agent_endpoint_agents_agent_id_get**
> AgentResponse get_agent_endpoint_agents_agent_id_get(agent_id, include_llm_credential=include_llm_credential)

Get Agent

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AgentsApi()
agent_id = NULL # object | 
include_llm_credential = true # object | When true (default), resolve effective provider credential metadata for this agent's `model_provider` without exposing secrets. (optional) (default to true)

try:
    # Get Agent
    api_response = api_instance.get_agent_endpoint_agents_agent_id_get(agent_id, include_llm_credential=include_llm_credential)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->get_agent_endpoint_agents_agent_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **include_llm_credential** | [**object**](.md)| When true (default), resolve effective provider credential metadata for this agent&#x27;s &#x60;model_provider&#x60; without exposing secrets. | [optional] [default to true]

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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
api_instance = hyperstruck.AgentsApi()
agent_id = NULL # object | 
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Agent Sessions
    api_response = api_instance.list_agent_sessions_endpoint_agents_agent_id_sessions_get(agent_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->list_agent_sessions_endpoint_agents_agent_id_sessions_get: %s\n" % e)
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

# **list_agents_endpoint_agents_get**
> AgentListResponse list_agents_endpoint_agents_get(include_llm_credential=include_llm_credential, limit=limit, cursor=cursor)

List Agents

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AgentsApi()
include_llm_credential = false # object | When true, include `llm_credential` per agent showing whether runtime uses `tenant_default` or `agent_override` for `model_provider`. (optional) (default to false)
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

try:
    # List Agents
    api_response = api_instance.list_agents_endpoint_agents_get(include_llm_credential=include_llm_credential, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->list_agents_endpoint_agents_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **include_llm_credential** | [**object**](.md)| When true, include &#x60;llm_credential&#x60; per agent showing whether runtime uses &#x60;tenant_default&#x60; or &#x60;agent_override&#x60; for &#x60;model_provider&#x60;. | [optional] [default to false]
 **limit** | [**object**](.md)| Page size. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**AgentListResponse**](AgentListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_agent_endpoint_agents_agent_id_patch**
> AgentResponse update_agent_endpoint_agents_agent_id_patch(body, agent_id)

Update Agent

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AgentsApi()
body = hyperstruck.AgentUpdateRequest() # AgentUpdateRequest | 
agent_id = NULL # object | 

try:
    # Update Agent
    api_response = api_instance.update_agent_endpoint_agents_agent_id_patch(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->update_agent_endpoint_agents_agent_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AgentUpdateRequest**](AgentUpdateRequest.md)|  | 
 **agent_id** | [**object**](.md)|  | 

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

