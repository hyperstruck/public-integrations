# hyperstruck.LearningsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**confirm_norm_endpoint_agents_agent_id_learnings_norms_learning_id_confirm_post**](LearningsApi.md#confirm_norm_endpoint_agents_agent_id_learnings_norms_learning_id_confirm_post) | **POST** /agents/{agent_id}/learnings/norms/{learning_id}/confirm | Confirm a stated norm
[**delete_agent_learnings_endpoint_agents_agent_id_learnings_delete**](LearningsApi.md#delete_agent_learnings_endpoint_agents_agent_id_learnings_delete) | **DELETE** /agents/{agent_id}/learnings | Delete all learnings for an agent
[**get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get**](LearningsApi.md#get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get) | **GET** /agents/{agent_id}/learnings/graph | Agent learning evidence graph
[**get_learning_endpoint_agents_agent_id_learnings_learning_id_get**](LearningsApi.md#get_learning_endpoint_agents_agent_id_learnings_learning_id_get) | **GET** /agents/{agent_id}/learnings/{learning_id} | Get a learning
[**get_norm_review_context_endpoint_agents_agent_id_learnings_norms_learning_id_review_context_get**](LearningsApi.md#get_norm_review_context_endpoint_agents_agent_id_learnings_norms_learning_id_review_context_get) | **GET** /agents/{agent_id}/learnings/norms/{learning_id}/review-context | Get a norm&#x27;s review context and consent token
[**list_agent_learnings_endpoint_agents_agent_id_learnings_get**](LearningsApi.md#list_agent_learnings_endpoint_agents_agent_id_learnings_get) | **GET** /agents/{agent_id}/learnings | List agent learnings (audit inventory)
[**list_learning_claims_endpoint_agents_agent_id_learnings_learning_id_claims_get**](LearningsApi.md#list_learning_claims_endpoint_agents_agent_id_learnings_learning_id_claims_get) | **GET** /agents/{agent_id}/learnings/{learning_id}/claims | List claims linked to a learning
[**list_norm_inbox_endpoint_agents_agent_id_learnings_norms_get**](LearningsApi.md#list_norm_inbox_endpoint_agents_agent_id_learnings_norms_get) | **GET** /agents/{agent_id}/learnings/norms | List the agent&#x27;s stated norms for review
[**reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post**](LearningsApi.md#reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post) | **POST** /agents/{agent_id}/learnings/{learning_id}/reinforce | Reinforce a learning
[**reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post**](LearningsApi.md#reject_learning_endpoint_agents_agent_id_learnings_learning_id_reject_post) | **POST** /agents/{agent_id}/learnings/{learning_id}/reject | Reject (archive) a learning
[**retire_norm_endpoint_agents_agent_id_learnings_norms_learning_id_retire_post**](LearningsApi.md#retire_norm_endpoint_agents_agent_id_learnings_norms_learning_id_retire_post) | **POST** /agents/{agent_id}/learnings/norms/{learning_id}/retire | Retire a stated norm
[**search_learnings_endpoint_agents_agent_id_learnings_search_get**](LearningsApi.md#search_learnings_endpoint_agents_agent_id_learnings_search_get) | **GET** /agents/{agent_id}/learnings/search | Search learnings
[**store_learning_endpoint_agents_agent_id_learnings_post**](LearningsApi.md#store_learning_endpoint_agents_agent_id_learnings_post) | **POST** /agents/{agent_id}/learnings | Store a learning

# **confirm_norm_endpoint_agents_agent_id_learnings_norms_learning_id_confirm_post**
> NormVerdictResponse confirm_norm_endpoint_agents_agent_id_learnings_norms_learning_id_confirm_post(agent_id, learning_id, if_match=if_match)

Confirm a stated norm

Lift a norm out of probation, which is what renders it at primacy on every turn. A curator is the only path: the norm's own applications never confirm it, because a probation norm renders as followable and crediting the agent for following it would be self-confirmation. Idempotent on an already confirmed norm; refused on a retired one. Requires the If-Match consent token.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier returned by a learning list or search endpoint.
if_match = NULL # object | The consent ETag returned by GET .../norms/{learning_id}/review-context. Required for confirm and retire: it proves the curator read this norm's state, and a stale token is refused. (optional)

try:
    # Confirm a stated norm
    api_response = api_instance.confirm_norm_endpoint_agents_agent_id_learnings_norms_learning_id_confirm_post(agent_id, learning_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->confirm_norm_endpoint_agents_agent_id_learnings_norms_learning_id_confirm_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier returned by a learning list or search endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../norms/{learning_id}/review-context. Required for confirm and retire: it proves the curator read this norm&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**NormVerdictResponse**](NormVerdictResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_agent_learnings_endpoint_agents_agent_id_learnings_delete**
> DeleteLearningsResponse delete_agent_learnings_endpoint_agents_agent_id_learnings_delete(agent_id)

Delete all learnings for an agent

Delete every learning memory scoped to the agent. Requires the agents:write scope and can_write on the agent. This is a destructive operation and does not affect other memory categories or the org-shared learning library.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**DeleteLearningsResponse**](DeleteLearningsResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get**
> LearningAuditGraphResponse get_agent_learnings_graph_endpoint_agents_agent_id_learnings_graph_get(agent_id, learning_id, depth=depth)

Agent learning evidence graph

Return a learning and related learnings within the requested lineage depth, including available evidence. Use this endpoint to explain relationships during audit or curation; a temporarily unavailable relationship service returns 503.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier to place at the centre of the graph.
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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier to place at the centre of the graph. |
 **depth** | [**object**](.md)| Lineage hops from the learning (1-2). | [optional] [default to 1]

### Return type

[**LearningAuditGraphResponse**](LearningAuditGraphResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

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

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier returned by a learning list or search endpoint.

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier returned by a learning list or search endpoint. |

### Return type

[**LearningResponse**](LearningResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_norm_review_context_endpoint_agents_agent_id_learnings_norms_learning_id_review_context_get**
> NormReviewContext get_norm_review_context_endpoint_agents_agent_id_learnings_norms_learning_id_review_context_get(agent_id, learning_id)

Get a norm's review context and consent token

One stated norm with an ETag consent token over everything shown. Pass the ETag back as If-Match on confirm or retire; any change to the directive, its lifecycle state, its dormancy or its counts invalidates it, so a curator cannot retire on 'never applied' a norm that was applied since they read it. Retired norms are readable here.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier returned by a learning list or search endpoint.

try:
    # Get a norm's review context and consent token
    api_response = api_instance.get_norm_review_context_endpoint_agents_agent_id_learnings_norms_learning_id_review_context_get(agent_id, learning_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->get_norm_review_context_endpoint_agents_agent_id_learnings_norms_learning_id_review_context_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier returned by a learning list or search endpoint. |

### Return type

[**NormReviewContext**](NormReviewContext.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_agent_learnings_endpoint_agents_agent_id_learnings_get**
> LearningAuditListResponse list_agent_learnings_endpoint_agents_agent_id_learnings_get(agent_id, include_instances=include_instances, limit=limit, cursor=cursor, state=state, q=q)

List agent learnings (audit inventory)

Paginated, filterable inventory of an agent's learnings for the curation workbench. Non-semantic (unlike /search). Defaults to the active bucket (excludes archived/superseded); use `state` for other buckets. Optional `q` ANDs free-text / learning-id match with the selected facet (requires a full-text index on learning content). Pagination is created_at keyset via the opaque cursor.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
include_instances = true # object | Include evidence instances on each item. (optional) (default to true)
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)
state = hyperstruck.LearningStateFilter() # LearningStateFilter | Review bucket: active (default), needs_review, archived, superseded, or all. (optional) (default to active)
q = NULL # object | Optional inventory text filter (content MatchText or exact learning id). ANDed with `state`. Omit or blank to disable. (optional)

try:
    # List agent learnings (audit inventory)
    api_response = api_instance.list_agent_learnings_endpoint_agents_agent_id_learnings_get(agent_id, include_instances=include_instances, limit=limit, cursor=cursor, state=state, q=q)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->list_agent_learnings_endpoint_agents_agent_id_learnings_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **include_instances** | [**object**](.md)| Include evidence instances on each item. | [optional] [default to true]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **state** | [**LearningStateFilter**](.md)| Review bucket: active (default), needs_review, archived, superseded, or all. | [optional] [default to active]
 **q** | [**object**](.md)| Optional inventory text filter (content MatchText or exact learning id). ANDed with &#x60;state&#x60;. Omit or blank to disable. | [optional]

### Return type

[**LearningAuditListResponse**](LearningAuditListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_learning_claims_endpoint_agents_agent_id_learnings_learning_id_claims_get**
> LearningClaimsListResponse list_learning_claims_endpoint_agents_agent_id_learnings_learning_id_claims_get(agent_id, learning_id, status=status, limit=limit, cursor=cursor)

List claims linked to a learning

Claims connected to this learning via composition provenance edges, for the claim curation panel. Filter by review status (or list open split proposals on entities the learning touched). latest_edge_at keyset pagination; an empty edge set is a 200 with no items, not a 404.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier returned by a learning list or search endpoint.
status = all # object | Review status filter. `all` is everything: every claim status plus open split proposals on entities this learning touched. `split_proposed` is open splits only; other values filter claims only. (optional) (default to all)
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List claims linked to a learning
    api_response = api_instance.list_learning_claims_endpoint_agents_agent_id_learnings_learning_id_claims_get(agent_id, learning_id, status=status, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->list_learning_claims_endpoint_agents_agent_id_learnings_learning_id_claims_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier returned by a learning list or search endpoint. |
 **status** | [**object**](.md)| Review status filter. &#x60;all&#x60; is everything: every claim status plus open split proposals on entities this learning touched. &#x60;split_proposed&#x60; is open splits only; other values filter claims only. | [optional] [default to all]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**LearningClaimsListResponse**](LearningClaimsListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_norm_inbox_endpoint_agents_agent_id_learnings_norms_get**
> NormInboxResponse list_norm_inbox_endpoint_agents_agent_id_learnings_norms_get(agent_id, include_retired=include_retired)

List the agent's stated norms for review

Every directive the principal stated, with its lifecycle state, when it was stated, the run it came from, and how often it has been offered, applied and proposed as breached. Ordered most-applied first. A norm sits in probation until a curator confirms it, and its own applications never confirm it, so this listing is the only route to primacy. Dormant norms are included and say what they are dormant until, so a zero application count can be read correctly. The listing is bounded by the reasoning memory, which counts the overflow rather than paging. Reachable from a portal session whose role carries `norms:curate`; an API key cannot hold it beside the dispatch scope that reaches the agent relation these routes require, which is the same shape `claims:curate` has.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
include_retired = false # object | Include norms already archived by a curator or superseded by a later directive. (optional) (default to false)

try:
    # List the agent's stated norms for review
    api_response = api_instance.list_norm_inbox_endpoint_agents_agent_id_learnings_norms_get(agent_id, include_retired=include_retired)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->list_norm_inbox_endpoint_agents_agent_id_learnings_norms_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **include_retired** | [**object**](.md)| Include norms already archived by a curator or superseded by a later directive. | [optional] [default to false]

### Return type

[**NormInboxResponse**](NormInboxResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

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

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ReinforceLearningRequest() # ReinforceLearningRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier returned by a learning list or search endpoint.

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier returned by a learning list or search endpoint. |

### Return type

[**ReinforceLearningResponse**](ReinforceLearningResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

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

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.RejectLearningRequest() # RejectLearningRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier returned by a learning list or search endpoint.

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier returned by a learning list or search endpoint. |

### Return type

[**RejectLearningResponse**](RejectLearningResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **retire_norm_endpoint_agents_agent_id_learnings_norms_learning_id_retire_post**
> NormVerdictResponse retire_norm_endpoint_agents_agent_id_learnings_norms_learning_id_retire_post(body, agent_id, learning_id, if_match=if_match)

Retire a stated norm

Archive a norm with curator provenance, so it leaves recall and keeps its history. This is the verdict for a directive that should not have been taken as a standing rule. A norm the principal has REPLACED is not retired here: state the replacement and the reasoning memory supersedes the original itself. Requires the If-Match consent token.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.RetireNormRequest() # RetireNormRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
learning_id = NULL # object | Learning identifier returned by a learning list or search endpoint.
if_match = NULL # object | The consent ETag returned by GET .../norms/{learning_id}/review-context. Required for confirm and retire: it proves the curator read this norm's state, and a stale token is refused. (optional)

try:
    # Retire a stated norm
    api_response = api_instance.retire_norm_endpoint_agents_agent_id_learnings_norms_learning_id_retire_post(body, agent_id, learning_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->retire_norm_endpoint_agents_agent_id_learnings_norms_learning_id_retire_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**RetireNormRequest**](RetireNormRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **learning_id** | [**object**](.md)| Learning identifier returned by a learning list or search endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../norms/{learning_id}/review-context. Required for confirm and retire: it proves the curator read this norm&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**NormVerdictResponse**](NormVerdictResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_learnings_endpoint_agents_agent_id_learnings_search_get**
> LearningSearchResponse search_learnings_endpoint_agents_agent_id_learnings_search_get(agent_id, q, limit=limit, min_utility=min_utility, scope=scope)

Search learnings

Semantic search over the agent's learning memories. Results are ranked intelligently by relevance, considering decay of older learnings and diversity filtering to avoid redundant results. Recorded contradictions involving the returned learnings come back on `conflicts`; an entry is kept when either side is in `items`, so the other side may need fetching by id.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **q** | [**object**](.md)| Search query text. |
 **limit** | [**object**](.md)| Maximum number of results to return. | [optional] [default to 10]
 **min_utility** | [**object**](.md)| Minimum utility threshold for results. | [optional]
 **scope** | [**LearningScope**](.md)| Search scope. &#x27;agent&#x27; searches the agent&#x27;s private learnings. &#x27;org&#x27; searches shared learnings across agents (Enterprise only). | [optional] [default to agent]

### Return type

[**LearningSearchResponse**](LearningSearchResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **store_learning_endpoint_agents_agent_id_learnings_post**
> StoreLearningAcceptedResponse store_learning_endpoint_agents_agent_id_learnings_post(body, agent_id)

Store a learning

Submit a caller-authored learning for one hosted agent. Processing is asynchronous, so a 202 response confirms acceptance rather than completion. Use `/distill` instead when the caller has evidence but not final learning text.

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
api_instance = hyperstruck.LearningsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.StoreLearningRequest() # StoreLearningRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

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
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**StoreLearningAcceptedResponse**](StoreLearningAcceptedResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

