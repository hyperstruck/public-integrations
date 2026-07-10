# hyperstruck.LearningsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**delete_agent_learnings_endpoint_agents_agent_id_learnings_delete**](LearningsApi.md#delete_agent_learnings_endpoint_agents_agent_id_learnings_delete) | **DELETE** /agents/{agent_id}/learnings | Delete all learnings for an agent
[**get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get**](LearningsApi.md#get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get) | **GET** /agents/{agent_id}/learnings/graph | Agent learning evidence graph
[**get_learning_endpoint_agents_agent_id_learnings_learning_id_get**](LearningsApi.md#get_learning_endpoint_agents_agent_id_learnings_learning_id_get) | **GET** /agents/{agent_id}/learnings/{learning_id} | Get a learning
[**list_agent_learnings_endpoint_agents_agent_id_learnings_get**](LearningsApi.md#list_agent_learnings_endpoint_agents_agent_id_learnings_get) | **GET** /agents/{agent_id}/learnings | List agent learnings (audit inventory)
[**reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post**](LearningsApi.md#reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post) | **POST** /agents/{agent_id}/learnings/{learning_id}/reinforce | Reinforce a learning
[**reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post**](LearningsApi.md#reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post) | **POST** /agents/{agent_id}/learnings/{learning_id}/reject | Reject (archive) a learning
[**search_learnings_endpoint_agents_agent_id_learnings_search_get**](LearningsApi.md#search_learnings_endpoint_agents_agent_id_learnings_search_get) | **GET** /agents/{agent_id}/learnings/search | Search learnings
[**store_learning_endpoint_agents_agent_id_learnings_post**](LearningsApi.md#store_learning_endpoint_agents_agent_id_learnings_post) | **POST** /agents/{agent_id}/learnings | Store a learning

# **delete_agent_learnings_endpoint_agents_agent_id_learnings_delete**
> DeleteLearningsResponse delete_agent_learnings_endpoint_agents_agent_id_learnings_delete(agent_id)

Delete all learnings for an agent

Delete every learning memory scoped to the agent. This is a destructive operation and does not affect other memory categories.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 

try:
    # Delete all learnings for an agent
    api_response = api_instance.delete_agent_learnings_endpoint_agents_agent_id_learnings_delete(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->delete_agent_learnings_endpoint_agents_agent_id_learnings_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 

### Return type

[**DeleteLearningsResponse**](DeleteLearningsResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get**
> LearningAuditGraphResponse get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get(agent_id, learning_id, depth=depth)

Agent learning evidence graph

Graph of the agent's reasoning topology around a learning: the learning plus the learnings it is connected to within `depth` lineage hops, each enriched with Qdrant detail and evidence. The Neo4j graph is the primary product — if it can't be read the request fails (503). Declared before /{learning_id} so the static path is not captured as a learning id.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 
learning_id = NULL # object | The learning to build the graph around.
depth = 1 # object | Lineage hops from the learning (1-2). (optional) (default to 1)

try:
    # Agent learning evidence graph
    api_response = api_instance.get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get(agent_id, learning_id, depth=depth)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **learning_id** | [**object**](.md)| The learning to build the graph around. | 
 **depth** | [**object**](.md)| Lineage hops from the learning (1-2). | [optional] [default to 1]

### Return type

[**LearningAuditGraphResponse**](LearningAuditGraphResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_learning_endpoint_agents_agent_id_learnings_learning_id_get**
> LearningResponse get_learning_endpoint_agents_agent_id_learnings_learning_id_get(agent_id, learning_id)

Get a learning

Retrieve a single learning by its ID.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 
learning_id = NULL # object | 

try:
    # Get a learning
    api_response = api_instance.get_learning_endpoint_agents_agent_id_learnings_learning_id_get(agent_id, learning_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->get_learning_endpoint_agents_agent_id_learnings_learning_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **learning_id** | [**object**](.md)|  | 

### Return type

[**LearningResponse**](LearningResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_agent_learnings_endpoint_agents_agent_id_learnings_get**
> LearningAuditListResponse list_agent_learnings_endpoint_agents_agent_id_learnings_get(agent_id, include_instances=include_instances, limit=limit, cursor=cursor, state=state)

List agent learnings (audit inventory)

Paginated, filterable inventory of an agent's learnings for the curation workbench. Non-semantic (unlike /search). Defaults to the active bucket (excludes archived/superseded); use `state` for other buckets. Pagination is created_at keyset via the opaque cursor.

The response's `omitted_learning_count` reports unreadable learnings omitted from
the current page. Treat this page-scoped count as the authoritative degraded
visibility signal; `partial_failures` provides diagnostic detail but may be
aggregated or truncated. A value of `0` means no learnings were omitted while
building that page.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 
include_instances = true # object | Include evidence instances on each item. (optional) (default to true)
limit = 50 # object | Page size. (optional) (default to 50)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)
state = hyperstruck.LearningStateFilter() # LearningStateFilter | Review bucket: active (default), needs_review, archived, superseded, or all. (optional) (default to active)

try:
    # List agent learnings (audit inventory)
    api_response = api_instance.list_agent_learnings_endpoint_agents_agent_id_learnings_get(agent_id, include_instances=include_instances, limit=limit, cursor=cursor, state=state)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->list_agent_learnings_endpoint_agents_agent_id_learnings_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **include_instances** | [**object**](.md)| Include evidence instances on each item. | [optional] [default to true]
 **limit** | [**object**](.md)| Page size. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 
 **state** | [**LearningStateFilter**](.md)| Review bucket: active (default), needs_review, archived, superseded, or all. | [optional] [default to active]

### Return type

[**LearningAuditListResponse**](LearningAuditListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post**
> ReinforceLearningResponse reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post(body, agent_id, learning_id)

Reinforce a learning

Provide feedback on whether a learning was helpful. Updates the learning's standing (utility and reliability) and trust level based on the feedback signal.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
body = hyperstruck.ReinforceLearningRequest() # ReinforceLearningRequest | 
agent_id = NULL # object | 
learning_id = NULL # object | 

try:
    # Reinforce a learning
    api_response = api_instance.reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post(body, agent_id, learning_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ReinforceLearningRequest**](ReinforceLearningRequest.md)|  | 
 **agent_id** | [**object**](.md)|  | 
 **learning_id** | [**object**](.md)|  | 

### Return type

[**ReinforceLearningResponse**](ReinforceLearningResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post**
> RejectLearningResponse reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post(body, agent_id, learning_id)

Reject (archive) a learning

Archive a live learning with curator provenance. Utility and trust are unchanged.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
body = hyperstruck.RejectLearningRequest() # RejectLearningRequest | 
agent_id = NULL # object | 
learning_id = NULL # object | 

try:
    # Reject (archive) a learning
    api_response = api_instance.reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post(body, agent_id, learning_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**RejectLearningRequest**](RejectLearningRequest.md)|  | 
 **agent_id** | [**object**](.md)|  | 
 **learning_id** | [**object**](.md)|  | 

### Return type

[**RejectLearningResponse**](RejectLearningResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_learnings_endpoint_agents_agent_id_learnings_search_get**
> LearningSearchResponse search_learnings_endpoint_agents_agent_id_learnings_search_get(agent_id, q, limit=limit, min_utility=min_utility, scope=scope)

Search learnings

Semantic search over the agent's learning memories. Results are ranked intelligently by relevance, considering decay of older learnings and diversity filtering to avoid redundant results.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 
q = NULL # object | Search query text.
limit = 10 # object | Maximum number of results to return. (optional) (default to 10)
min_utility = NULL # object | Minimum utility threshold for results. (optional)
scope = hyperstruck.LearningScope() # LearningScope | Search scope. 'agent' searches the agent's private learnings. 'org' searches shared learnings across agents (Enterprise only). (optional) (default to agent)

try:
    # Search learnings
    api_response = api_instance.search_learnings_endpoint_agents_agent_id_learnings_search_get(agent_id, q, limit=limit, min_utility=min_utility, scope=scope)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->search_learnings_endpoint_agents_agent_id_learnings_search_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **q** | [**object**](.md)| Search query text. | 
 **limit** | [**object**](.md)| Maximum number of results to return. | [optional] [default to 10]
 **min_utility** | [**object**](.md)| Minimum utility threshold for results. | [optional] 
 **scope** | [**LearningScope**](.md)| Search scope. &#x27;agent&#x27; searches the agent&#x27;s private learnings. &#x27;org&#x27; searches shared learnings across agents (Enterprise only). | [optional] [default to agent]

### Return type

[**LearningSearchResponse**](LearningSearchResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **store_learning_endpoint_agents_agent_id_learnings_post**
> StoreLearningAcceptedResponse store_learning_endpoint_agents_agent_id_learnings_post(body, agent_id)

Store a learning

Store a new learning for the agent. The learning is processed through the platform's deduplication and conflict prevention pipeline on a background worker so the request returns immediately.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
body = hyperstruck.StoreLearningRequest() # StoreLearningRequest | 
agent_id = NULL # object | 

try:
    # Store a learning
    api_response = api_instance.store_learning_endpoint_agents_agent_id_learnings_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->store_learning_endpoint_agents_agent_id_learnings_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**StoreLearningRequest**](StoreLearningRequest.md)|  | 
 **agent_id** | [**object**](.md)|  | 

### Return type

[**StoreLearningAcceptedResponse**](StoreLearningAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

