# hyperstruck.AgentsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_agent_endpoint_agents_post**](AgentsApi.md#create_agent_endpoint_agents_post) | **POST** /agents | Create Agent
[**delete_agent_endpoint_agents_agent_id_delete**](AgentsApi.md#delete_agent_endpoint_agents_agent_id_delete) | **DELETE** /agents/{agent_id} | Delete Agent
[**dispatch_goal_run_endpoint_agents_agent_id_goals_post**](AgentsApi.md#dispatch_goal_run_endpoint_agents_agent_id_goals_post) | **POST** /agents/{agent_id}/goals | Create Goal Run
[**get_agent_endpoint_agents_agent_id_get**](AgentsApi.md#get_agent_endpoint_agents_agent_id_get) | **GET** /agents/{agent_id} | Get Agent
[**get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get**](AgentsApi.md#get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get) | **GET** /agents/{agent_id}/usage/summary | Get Agent Usage Summary
[**list_agent_runs_endpoint_agents_agent_id_runs_get**](AgentsApi.md#list_agent_runs_endpoint_agents_agent_id_runs_get) | **GET** /agents/{agent_id}/runs | List Agent Runs
[**list_agent_sessions_endpoint_agents_agent_id_sessions_get**](AgentsApi.md#list_agent_sessions_endpoint_agents_agent_id_sessions_get) | **GET** /agents/{agent_id}/sessions | List Agent Sessions
[**list_agents_endpoint_agents_get**](AgentsApi.md#list_agents_endpoint_agents_get) | **GET** /agents | List Agents
[**list_definition_suggestions_endpoint_agents_definition_suggestions_get**](AgentsApi.md#list_definition_suggestions_endpoint_agents_definition_suggestions_get) | **GET** /agents/definition-suggestions | List Definition Suggestions
[**update_agent_endpoint_agents_agent_id_patch**](AgentsApi.md#update_agent_endpoint_agents_agent_id_patch) | **PATCH** /agents/{agent_id} | Update Agent

# **create_agent_endpoint_agents_post**
> AgentResponse create_agent_endpoint_agents_post(body)

Create Agent

Create a hosted agent from its name, model configuration, instructions, and optional home space. Use the returned agent UUID for agent-scoped resource paths.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
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

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_agent_endpoint_agents_agent_id_delete**
> delete_agent_endpoint_agents_agent_id_delete(agent_id)

Delete Agent

Permanently delete a hosted agent and purge its learning corpus after the row commits. Use only when the agent and its configuration are no longer needed; the operation cannot be undone.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Delete Agent
    api_instance.delete_agent_endpoint_agents_agent_id_delete(agent_id)
except ApiException as e:
    print("Exception when calling AgentsApi->delete_agent_endpoint_agents_agent_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **dispatch_goal_run_endpoint_agents_agent_id_goals_post**
> GoalRunAcceptedResponse dispatch_goal_run_endpoint_agents_agent_id_goals_post(body, agent_id)

Create Goal Run

Start asynchronous work for a hosted agent. A 202 response contains the server-issued run UUID; use `GET /runs/{run_id}` to follow its status and resume it if human input is requested.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.GoalRunRequest() # GoalRunRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**GoalRunAcceptedResponse**](GoalRunAcceptedResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_agent_endpoint_agents_agent_id_get**
> AgentDetailResponse get_agent_endpoint_agents_agent_id_get(agent_id, include_summary=include_summary, include_access=include_access, window=window)

Get Agent

Retrieve one hosted agent and its effective configuration. An optional query flag can include a per-agent usage summary.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
include_summary = false # object | When true, include a per-agent usage summary. (optional) (default to false)
include_access = false # object | When true, include what the caller may do with the agent. (optional) (default to false)
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Window applied when `include_summary` is true. (optional) (default to last_30_days)

try:
    # Get Agent
    api_response = api_instance.get_agent_endpoint_agents_agent_id_get(agent_id, include_summary=include_summary, include_access=include_access, window=window)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->get_agent_endpoint_agents_agent_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **include_summary** | [**object**](.md)| When true, include a per-agent usage summary. | [optional] [default to false]
 **include_access** | [**object**](.md)| When true, include what the caller may do with the agent. | [optional] [default to false]
 **window** | [**UsageTimeWindow**](.md)| Window applied when &#x60;include_summary&#x60; is true. | [optional] [default to last_30_days]

### Return type

[**AgentDetailResponse**](AgentDetailResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get**
> AgentUsageSummaryResponse get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get(agent_id, window=window)

Get Agent Usage Summary

Return metered usage for one agent over a preset reporting window. Use tenant-level `/usage` endpoints when an all-agent total is required.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Preset reporting window. (optional) (default to last_30_days)

try:
    # Get Agent Usage Summary
    api_response = api_instance.get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get(agent_id, window=window)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->get_agent_usage_summary_endpoint_agents_agent_id_usage_summary_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **window** | [**UsageTimeWindow**](.md)| Preset reporting window. | [optional] [default to last_30_days]

### Return type

[**AgentUsageSummaryResponse**](AgentUsageSummaryResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_agent_runs_endpoint_agents_agent_id_runs_get**
> AgentRunListResponse list_agent_runs_endpoint_agents_agent_id_runs_get(agent_id, status=status, run_type=run_type, session_id=session_id, window=window, limit=limit, cursor=cursor)

List Agent Runs

List hosted runs for one agent, optionally filtered by status, type, session, or reporting window. Use the returned run UUIDs with `/runs`.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
status = [] # object | Filter by one or more run statuses. (optional) (default to [])
run_type = [] # object | Filter by one or more run types (goal|resume). (optional) (default to [])
session_id = NULL # object | Filter to a single session. (optional)
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Window bounding which runs are returned. (optional) (default to last_30_days)
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List Agent Runs
    api_response = api_instance.list_agent_runs_endpoint_agents_agent_id_runs_get(agent_id, status=status, run_type=run_type, session_id=session_id, window=window, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->list_agent_runs_endpoint_agents_agent_id_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **status** | [**object**](.md)| Filter by one or more run statuses. | [optional] [default to []]
 **run_type** | [**object**](.md)| Filter by one or more run types (goal|resume). | [optional] [default to []]
 **session_id** | [**object**](.md)| Filter to a single session. | [optional]
 **window** | [**UsageTimeWindow**](.md)| Window bounding which runs are returned. | [optional] [default to last_30_days]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**AgentRunListResponse**](AgentRunListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
limit = 20 # object | Maximum number of items to return on this page. (optional) (default to 20)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

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

# **list_agents_endpoint_agents_get**
> AgentInventoryResponse list_agents_endpoint_agents_get(q=q, status=status, space_id=space_id, reasoning_profile=reasoning_profile, sort=sort, window=window, documents=documents, include_summary=include_summary, limit=limit, cursor=cursor, include_value=include_value, test=test)

List Agents

Find agents available to the caller. Use filters and cursor pagination for inventory screens or agent selection; request summaries only when usage metrics are needed. Request `include_value` (or sort by value) to see what each agent is worth and how to record value for it.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
q = NULL # object | Case-insensitive search over name and description. (optional)
status = [] # object | Filter by one or more agent statuses. (optional) (default to [])
space_id = NULL # object | Filter to agents homed in this space. (optional)
reasoning_profile = [] # object | Filter by one or more reasoning profiles. (optional) (default to [])
sort = created_desc # object | Sort mode: created_desc|created_asc|name_asc|name_desc|last_run_desc|run_count_desc|spend_desc|value_desc|value_asc|estimated_value_desc. Value sorts rank by lifetime measured (or, for estimated_value_desc, estimated) value; agents without value tracking come last. value_asc lists tracked agents earning the least first, for pruning. (optional) (default to created_desc)
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Window for metric sorts and per-agent summaries. (optional) (default to last_30_days)
documents = NULL # object | Keep only agents whose documents have this status, the first that applies: `reading` (some queued or being read), `paused` (some stopped at the spend limit), `failed`, `up_to_date`, or `empty` (no documents). (optional)
include_summary = false # object | When true, include a per-agent usage summary. (optional) (default to false)
limit = 20 # object | Maximum number of items to return on this page. (optional) (default to 20)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)
include_value = false # object | When true, include each agent's lifetime `value`: measured and estimated dollars, what counts as value, its rate-card units, and `guidance` on how to record value for it. Implied by any value sort. (optional) (default to false)
test = hyperstruck.AgentTestFilter() # AgentTestFilter | Whether test agents are listed: `exclude` (default) leaves them out, `include` lists every agent, `only` lists test agents alone. (optional) (default to exclude)

try:
    # List Agents
    api_response = api_instance.list_agents_endpoint_agents_get(q=q, status=status, space_id=space_id, reasoning_profile=reasoning_profile, sort=sort, window=window, documents=documents, include_summary=include_summary, limit=limit, cursor=cursor, include_value=include_value, test=test)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->list_agents_endpoint_agents_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **q** | [**object**](.md)| Case-insensitive search over name and description. | [optional]
 **status** | [**object**](.md)| Filter by one or more agent statuses. | [optional] [default to []]
 **space_id** | [**object**](.md)| Filter to agents homed in this space. | [optional]
 **reasoning_profile** | [**object**](.md)| Filter by one or more reasoning profiles. | [optional] [default to []]
 **sort** | [**object**](.md)| Sort mode: created_desc|created_asc|name_asc|name_desc|last_run_desc|run_count_desc|spend_desc|value_desc|value_asc|estimated_value_desc. Value sorts rank by lifetime measured (or, for estimated_value_desc, estimated) value; agents without value tracking come last. value_asc lists tracked agents earning the least first, for pruning. | [optional] [default to created_desc]
 **window** | [**UsageTimeWindow**](.md)| Window for metric sorts and per-agent summaries. | [optional] [default to last_30_days]
 **documents** | [**object**](.md)| Keep only agents whose documents have this status, the first that applies: &#x60;reading&#x60; (some queued or being read), &#x60;paused&#x60; (some stopped at the spend limit), &#x60;failed&#x60;, &#x60;up_to_date&#x60;, or &#x60;empty&#x60; (no documents). | [optional]
 **include_summary** | [**object**](.md)| When true, include a per-agent usage summary. | [optional] [default to false]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **include_value** | [**object**](.md)| When true, include each agent&#x27;s lifetime &#x60;value&#x60;: measured and estimated dollars, what counts as value, its rate-card units, and &#x60;guidance&#x60; on how to record value for it. Implied by any value sort. | [optional] [default to false]
 **test** | [**AgentTestFilter**](.md)| Whether test agents are listed: &#x60;exclude&#x60; (default) leaves them out, &#x60;include&#x60; lists every agent, &#x60;only&#x60; lists test agents alone. | [optional] [default to exclude]

### Return type

[**AgentInventoryResponse**](AgentInventoryResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_definition_suggestions_endpoint_agents_definition_suggestions_get**
> AgentDefinitionSuggestionListResponse list_definition_suggestions_endpoint_agents_definition_suggestions_get(kind=kind, q=q)

List Definition Suggestions

Return curated templates or traits that can help construct an agent definition. Use this before creating or editing an agent when the caller needs discoverable starting values.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
kind = hyperstruck.AgentDefinitionSuggestionKind() # AgentDefinitionSuggestionKind | Suggestion catalog to return. (optional) (default to template)
q = NULL # object | Optional case-insensitive filter over label/description. (optional)

try:
    # List Definition Suggestions
    api_response = api_instance.list_definition_suggestions_endpoint_agents_definition_suggestions_get(kind=kind, q=q)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentsApi->list_definition_suggestions_endpoint_agents_definition_suggestions_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **kind** | [**AgentDefinitionSuggestionKind**](.md)| Suggestion catalog to return. | [optional] [default to template]
 **q** | [**object**](.md)| Optional case-insensitive filter over label/description. | [optional]

### Return type

[**AgentDefinitionSuggestionListResponse**](AgentDefinitionSuggestionListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_agent_endpoint_agents_agent_id_patch**
> AgentResponse update_agent_endpoint_agents_agent_id_patch(body, agent_id)

Update Agent

Update the supplied fields on an existing hosted agent. Omitted fields retain their current values.

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
api_instance = hyperstruck.AgentsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.AgentUpdateRequest() # AgentUpdateRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

