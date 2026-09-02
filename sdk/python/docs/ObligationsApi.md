# hyperstruck.ObligationsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**cancel_obligation_endpoint_agents_agent_id_obligations_obligation_id_cancel_post**](ObligationsApi.md#cancel_obligation_endpoint_agents_agent_id_obligations_obligation_id_cancel_post) | **POST** /agents/{agent_id}/obligations/{obligation_id}/cancel | Withdraw an obligation record
[**close_obligation_endpoint_agents_agent_id_obligations_obligation_id_close_post**](ObligationsApi.md#close_obligation_endpoint_agents_agent_id_obligations_obligation_id_close_post) | **POST** /agents/{agent_id}/obligations/{obligation_id}/close | Close an obligation as kept or dropped
[**get_agent_obligation_open_count_endpoint_agents_agent_id_obligations_open_count_get**](ObligationsApi.md#get_agent_obligation_open_count_endpoint_agents_agent_id_obligations_open_count_get) | **GET** /agents/{agent_id}/obligations/open-count | Count an agent&#x27;s open obligations
[**get_obligation_endpoint_agents_agent_id_obligations_obligation_id_get**](ObligationsApi.md#get_obligation_endpoint_agents_agent_id_obligations_obligation_id_get) | **GET** /agents/{agent_id}/obligations/{obligation_id} | Get an obligation
[**get_org_obligation_open_count_endpoint_org_obligations_open_count_get**](ObligationsApi.md#get_org_obligation_open_count_endpoint_org_obligations_open_count_get) | **GET** /org/obligations/open-count | Read the metered open-obligation stock beside the live one
[**list_obligation_source_credit_endpoint_agents_agent_id_obligation_credit_get**](ObligationsApi.md#list_obligation_source_credit_endpoint_agents_agent_id_obligation_credit_get) | **GET** /agents/{agent_id}/obligation-credit | Read how reliable each harvesting source has proved
[**list_obligations_endpoint_agents_agent_id_obligations_get**](ObligationsApi.md#list_obligations_endpoint_agents_agent_id_obligations_get) | **GET** /agents/{agent_id}/obligations | List an agent&#x27;s obligations
[**list_org_obligations_endpoint_org_obligations_get**](ObligationsApi.md#list_org_obligations_endpoint_org_obligations_get) | **GET** /org/obligations | List obligations across the tenant&#x27;s agents
[**reschedule_obligation_endpoint_agents_agent_id_obligations_obligation_id_reschedule_post**](ObligationsApi.md#reschedule_obligation_endpoint_agents_agent_id_obligations_obligation_id_reschedule_post) | **POST** /agents/{agent_id}/obligations/{obligation_id}/reschedule | Move an obligation&#x27;s due date
[**store_obligation_endpoint_agents_agent_id_obligations_post**](ObligationsApi.md#store_obligation_endpoint_agents_agent_id_obligations_post) | **POST** /agents/{agent_id}/obligations | Record an obligation
[**supersede_obligation_endpoint_agents_agent_id_obligations_obligation_id_supersede_post**](ObligationsApi.md#supersede_obligation_endpoint_agents_agent_id_obligations_obligation_id_supersede_post) | **POST** /agents/{agent_id}/obligations/{obligation_id}/supersede | Replace an obligation with its successor

# **cancel_obligation_endpoint_agents_agent_id_obligations_obligation_id_cancel_post**
> ObligationResponse cancel_obligation_endpoint_agents_agent_id_obligations_obligation_id_cancel_post(body, agent_id, obligation_id, timezone=timezone)

Withdraw an obligation record

Withdraws the RECORD rather than deciding the commitment: a test write, a malformed body, a bad import. Takes no reason, writes no suppression key, and moves no source's credit, so the same commitment can be recorded again immediately and an operator tidying up cannot penalise a source. Use close with 'not_an_obligation' when the source was wrong.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.CancelObligationRequest() # CancelObligationRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
obligation_id = NULL # object | Obligation UUID returned by the obligations store or list endpoint.
timezone = NULL # object | IANA zone to render due_local in on the answer. (optional)

try:
    # Withdraw an obligation record
    api_response = api_instance.cancel_obligation_endpoint_agents_agent_id_obligations_obligation_id_cancel_post(body, agent_id, obligation_id, timezone=timezone)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->cancel_obligation_endpoint_agents_agent_id_obligations_obligation_id_cancel_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CancelObligationRequest**](CancelObligationRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **obligation_id** | [**object**](.md)| Obligation UUID returned by the obligations store or list endpoint. |
 **timezone** | [**object**](.md)| IANA zone to render due_local in on the answer. | [optional]

### Return type

[**ObligationResponse**](ObligationResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **close_obligation_endpoint_agents_agent_id_obligations_obligation_id_close_post**
> ObligationResponse close_obligation_endpoint_agents_agent_id_obligations_obligation_id_close_post(body, agent_id, obligation_id, timezone=timezone)

Close an obligation as kept or dropped

Ends an obligation, recording who says so. 'kept' needs a kept_basis (reported, evidenced or declared); 'dropped' needs a dropped_reason, of which only 'not_an_obligation' counts against the source that produced it. Repeating the identical close returns 200 with the row and emits nothing further, so a client that retried a timed-out request is not told its own successful action failed; a close contradicting the state already held is a 409, as is a stale expected_version.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.CloseObligationRequest() # CloseObligationRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
obligation_id = NULL # object | Obligation UUID returned by the obligations store or list endpoint.
timezone = NULL # object | IANA zone to render due_local in on the answer. (optional)

try:
    # Close an obligation as kept or dropped
    api_response = api_instance.close_obligation_endpoint_agents_agent_id_obligations_obligation_id_close_post(body, agent_id, obligation_id, timezone=timezone)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->close_obligation_endpoint_agents_agent_id_obligations_obligation_id_close_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CloseObligationRequest**](CloseObligationRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **obligation_id** | [**object**](.md)| Obligation UUID returned by the obligations store or list endpoint. |
 **timezone** | [**object**](.md)| IANA zone to render due_local in on the answer. | [optional]

### Return type

[**ObligationResponse**](ObligationResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_agent_obligation_open_count_endpoint_agents_agent_id_obligations_open_count_get**
> AgentObligationOpenCountResponse get_agent_obligation_open_count_endpoint_agents_agent_id_obligations_open_count_get(agent_id)

Count an agent's open obligations

How many open, unexpired obligations this agent holds right now. Only this agent's rows are counted; the tenant-wide figure beside its metered value is GET /org/obligations/open-count.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Count an agent's open obligations
    api_response = api_instance.get_agent_obligation_open_count_endpoint_agents_agent_id_obligations_open_count_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->get_agent_obligation_open_count_endpoint_agents_agent_id_obligations_open_count_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**AgentObligationOpenCountResponse**](AgentObligationOpenCountResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_obligation_endpoint_agents_agent_id_obligations_obligation_id_get**
> ObligationResponse get_obligation_endpoint_agents_agent_id_obligations_obligation_id_get(agent_id, obligation_id, timezone=timezone)

Get an obligation

Retrieve a single obligation by its id.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
obligation_id = NULL # object | Obligation UUID returned by the obligations store or list endpoint.
timezone = NULL # object | IANA zone to render due_local in. (optional)

try:
    # Get an obligation
    api_response = api_instance.get_obligation_endpoint_agents_agent_id_obligations_obligation_id_get(agent_id, obligation_id, timezone=timezone)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->get_obligation_endpoint_agents_agent_id_obligations_obligation_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **obligation_id** | [**object**](.md)| Obligation UUID returned by the obligations store or list endpoint. |
 **timezone** | [**object**](.md)| IANA zone to render due_local in. | [optional]

### Return type

[**ObligationResponse**](ObligationResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_org_obligation_open_count_endpoint_org_obligations_open_count_get**
> ObligationOpenCountResponse get_org_obligation_open_count_endpoint_org_obligations_open_count_get(usage_date=usage_date)

Read the metered open-obligation stock beside the live one

usage_daily.obligation_open_count for a day, and the number of open obligations the tenant actually holds right now, so the two are visibly the same or visibly not. obligation_open_count is the shelf's only stock counter; the other six are flow, drained from events. A flow counter that stops being written is obviously wrong. A stock counter that stops being written goes on reading as whatever it last said, which is what a healthy counter looks like on a quiet day, so it is only meaningful next to the live figure. A null metered_open_count means the reconcile has not written for that day yet, which is a different fact from a zero.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
usage_date = NULL # object | The metered day, in UTC. Defaults to today. (optional)

try:
    # Read the metered open-obligation stock beside the live one
    api_response = api_instance.get_org_obligation_open_count_endpoint_org_obligations_open_count_get(usage_date=usage_date)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->get_org_obligation_open_count_endpoint_org_obligations_open_count_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **usage_date** | [**object**](.md)| The metered day, in UTC. Defaults to today. | [optional]

### Return type

[**ObligationOpenCountResponse**](ObligationOpenCountResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_obligation_source_credit_endpoint_agents_agent_id_obligation_credit_get**
> ObligationSourceCreditListResponse list_obligation_source_credit_endpoint_agents_agent_id_obligation_credit_get(agent_id, limit=limit)

Read how reliable each harvesting source has proved

How often obligations harvested from each source turned out to have been real, worst score first. Kept counts for, on any basis; only a drop for 'not_an_obligation' and an expiry for neglect count against, because the other drop reasons judge the commitment rather than the source, capacity expiry is eviction, and a passed due says the rep did not act. Each source is scored against this agent's pooled rate as a prior, so a source with a handful of outcomes is not judged on a handful of outcomes. Advisory: nothing in the harvest lane reads this back to gate anything.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
limit = 200 # object | Maximum number of items to return on this page. (optional) (default to 200)

try:
    # Read how reliable each harvesting source has proved
    api_response = api_instance.list_obligation_source_credit_endpoint_agents_agent_id_obligation_credit_get(agent_id, limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->list_obligation_source_credit_endpoint_agents_agent_id_obligation_credit_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 200]

### Return type

[**ObligationSourceCreditListResponse**](ObligationSourceCreditListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_obligations_endpoint_agents_agent_id_obligations_get**
> ObligationListResponse list_obligations_endpoint_agents_agent_id_obligations_get(agent_id, status=status, entity_id=entity_id, due_before=due_before, limit=limit, after=after, needs_review=needs_review, q=q, provenance_class=provenance_class, review_reason=review_reason, timezone=timezone)

List an agent's obligations

Paginated inventory of an agent's obligations. Filters by status, entity_id (either party or the subject), due_before, q (free text over the statement) and provenance_class, and every filter composes with needs_review. due_at is additionally rendered in ?timezone= (default: the agent's own zone, else UTC). Pagination is by opaque cursor: pass the response's next_cursor back verbatim as ?after= for the next page, and never parse or construct one yourself.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
status = NULL # object | Filter by status (open, kept, dropped, expired, superseded, cancelled). (optional)
entity_id = NULL # object | Filter to obligations naming this registry entity. (optional)
due_before = NULL # object | Filter to obligations due before this instant. (optional)
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
after = NULL # object | Opaque cursor from a previous page's next_cursor, passed back verbatim. Its shape is internal and may change; a malformed value is refused with a 422. (optional)
needs_review = false # object | Narrow to the OPEN obligations waiting on a person rather than on a due date: an untrusted source, a premise since retracted or erased, a later note reporting the work done or taken back, or repeated surfacing with no decision. Each row comes back with review_reasons naming which apply. A page may be short or empty while next_cursor is set, so page until next_cursor is null. (optional) (default to false)
q = NULL # object | Free-text contains match over the statement, case-insensitive. The caller's own wildcards are taken literally: searching for '50%' finds statements containing '50%', not everything starting '50'. Combines with every other filter, needs_review included. (optional)
provenance_class = NULL # object | Filter by whose word the obligation is held on: user_directed (the typed write), source_observed (harvested from a corpus), agent_committed, or rule_implied. (optional)
review_reason = NULL # object | Narrow the review queue to one bucket: untrusted_provenance, premise_retracted, later_standing or neglected. Only meaningful with needs_review=true, and it can only shrink that queue, never widen it. (optional)
timezone = NULL # object | IANA zone to render due_local in. (optional)

try:
    # List an agent's obligations
    api_response = api_instance.list_obligations_endpoint_agents_agent_id_obligations_get(agent_id, status=status, entity_id=entity_id, due_before=due_before, limit=limit, after=after, needs_review=needs_review, q=q, provenance_class=provenance_class, review_reason=review_reason, timezone=timezone)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->list_obligations_endpoint_agents_agent_id_obligations_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **status** | [**object**](.md)| Filter by status (open, kept, dropped, expired, superseded, cancelled). | [optional]
 **entity_id** | [**object**](.md)| Filter to obligations naming this registry entity. | [optional]
 **due_before** | [**object**](.md)| Filter to obligations due before this instant. | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **after** | [**object**](.md)| Opaque cursor from a previous page&#x27;s next_cursor, passed back verbatim. Its shape is internal and may change; a malformed value is refused with a 422. | [optional]
 **needs_review** | [**object**](.md)| Narrow to the OPEN obligations waiting on a person rather than on a due date: an untrusted source, a premise since retracted or erased, a later note reporting the work done or taken back, or repeated surfacing with no decision. Each row comes back with review_reasons naming which apply. A page may be short or empty while next_cursor is set, so page until next_cursor is null. | [optional] [default to false]
 **q** | [**object**](.md)| Free-text contains match over the statement, case-insensitive. The caller&#x27;s own wildcards are taken literally: searching for &#x27;50%&#x27; finds statements containing &#x27;50%&#x27;, not everything starting &#x27;50&#x27;. Combines with every other filter, needs_review included. | [optional]
 **provenance_class** | [**object**](.md)| Filter by whose word the obligation is held on: user_directed (the typed write), source_observed (harvested from a corpus), agent_committed, or rule_implied. | [optional]
 **review_reason** | [**object**](.md)| Narrow the review queue to one bucket: untrusted_provenance, premise_retracted, later_standing or neglected. Only meaningful with needs_review&#x3D;true, and it can only shrink that queue, never widen it. | [optional]
 **timezone** | [**object**](.md)| IANA zone to render due_local in. | [optional]

### Return type

[**ObligationListResponse**](ObligationListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_org_obligations_endpoint_org_obligations_get**
> ObligationOrgListResponse list_org_obligations_endpoint_org_obligations_get(status=status, entity_id=entity_id, due_before=due_before, needs_review=needs_review, q=q, provenance_class=provenance_class, review_reason=review_reason, limit=limit, after=after, timezone=timezone)

List obligations across the tenant's agents

The tenant's obligations, fanned across its agents and each labelled with its owning agent. Carries the same filters as the agent-scoped list, so ?needs_review=true is the review queue across every agent an operator holds. is_space_filtered says the caller's readable-space set narrowed the page, so a short page can be told from the end of the list. Pagination is by opaque cursor: pass next_cursor back verbatim as ?after=.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
status = NULL # object | Filter by status (open, kept, dropped, expired, superseded, cancelled). (optional)
entity_id = NULL # object | Filter to obligations naming this registry entity. (optional)
due_before = NULL # object | Filter to obligations due before this instant. (optional)
needs_review = false # object | Narrow to the OPEN obligations waiting on a person rather than on a due date. Each row comes back with review_reasons naming which of the four buckets apply. This is the parameter that makes this route the tenant's review queue. (optional) (default to false)
q = NULL # object | Free-text contains match over the statement, case-insensitive. The caller's own wildcards are taken literally: searching for '50%' finds statements containing '50%', not everything starting '50'. Combines with every other filter, needs_review included. (optional)
provenance_class = NULL # object | Filter by whose word the obligation is held on: user_directed (the typed write), source_observed (harvested from a corpus), agent_committed, or rule_implied. (optional)
review_reason = NULL # object | Narrow the review queue to one bucket: untrusted_provenance, premise_retracted, later_standing or neglected. Only meaningful with needs_review=true, and it can only shrink that queue, never widen it. (optional)
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
after = NULL # object | Opaque cursor from a previous page's next_cursor, passed back verbatim. Its shape is internal and may change; a malformed value is refused with a 422. (optional)
timezone = NULL # object | IANA zone to render due_local in. Defaults to UTC rather than to an agent's own default, because a page here spans agents and no one agent's default is the right one for it. A date-precision due still renders in its own zone. (optional)

try:
    # List obligations across the tenant's agents
    api_response = api_instance.list_org_obligations_endpoint_org_obligations_get(status=status, entity_id=entity_id, due_before=due_before, needs_review=needs_review, q=q, provenance_class=provenance_class, review_reason=review_reason, limit=limit, after=after, timezone=timezone)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->list_org_obligations_endpoint_org_obligations_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **status** | [**object**](.md)| Filter by status (open, kept, dropped, expired, superseded, cancelled). | [optional]
 **entity_id** | [**object**](.md)| Filter to obligations naming this registry entity. | [optional]
 **due_before** | [**object**](.md)| Filter to obligations due before this instant. | [optional]
 **needs_review** | [**object**](.md)| Narrow to the OPEN obligations waiting on a person rather than on a due date. Each row comes back with review_reasons naming which of the four buckets apply. This is the parameter that makes this route the tenant&#x27;s review queue. | [optional] [default to false]
 **q** | [**object**](.md)| Free-text contains match over the statement, case-insensitive. The caller&#x27;s own wildcards are taken literally: searching for &#x27;50%&#x27; finds statements containing &#x27;50%&#x27;, not everything starting &#x27;50&#x27;. Combines with every other filter, needs_review included. | [optional]
 **provenance_class** | [**object**](.md)| Filter by whose word the obligation is held on: user_directed (the typed write), source_observed (harvested from a corpus), agent_committed, or rule_implied. | [optional]
 **review_reason** | [**object**](.md)| Narrow the review queue to one bucket: untrusted_provenance, premise_retracted, later_standing or neglected. Only meaningful with needs_review&#x3D;true, and it can only shrink that queue, never widen it. | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **after** | [**object**](.md)| Opaque cursor from a previous page&#x27;s next_cursor, passed back verbatim. Its shape is internal and may change; a malformed value is refused with a 422. | [optional]
 **timezone** | [**object**](.md)| IANA zone to render due_local in. Defaults to UTC rather than to an agent&#x27;s own default, because a page here spans agents and no one agent&#x27;s default is the right one for it. A date-precision due still renders in its own zone. | [optional]

### Return type

[**ObligationOrgListResponse**](ObligationOrgListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reschedule_obligation_endpoint_agents_agent_id_obligations_obligation_id_reschedule_post**
> ObligationResponse reschedule_obligation_endpoint_agents_agent_id_obligations_obligation_id_reschedule_post(body, agent_id, obligation_id, timezone=timezone)

Move an obligation's due date

Moves the due, keeping the obligation's identity: moving a date is not making a new promise. An open obligation already sitting on the new day under the same key is a 409, and the caller resolves it by closing one of the two.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.RescheduleObligationRequest() # RescheduleObligationRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
obligation_id = NULL # object | Obligation UUID returned by the obligations store or list endpoint.
timezone = NULL # object | IANA zone to render due_local in on the answer. (optional)

try:
    # Move an obligation's due date
    api_response = api_instance.reschedule_obligation_endpoint_agents_agent_id_obligations_obligation_id_reschedule_post(body, agent_id, obligation_id, timezone=timezone)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->reschedule_obligation_endpoint_agents_agent_id_obligations_obligation_id_reschedule_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**RescheduleObligationRequest**](RescheduleObligationRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **obligation_id** | [**object**](.md)| Obligation UUID returned by the obligations store or list endpoint. |
 **timezone** | [**object**](.md)| IANA zone to render due_local in on the answer. | [optional]

### Return type

[**ObligationResponse**](ObligationResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **store_obligation_endpoint_agents_agent_id_obligations_post**
> StoreObligationAcceptedResponse store_obligation_endpoint_agents_agent_id_obligations_post(body, agent_id)

Record an obligation

Write an obligation the host has, is owed, or is holding a party to. Always written as user_directed provenance. A capacity or dedupe refusal is reported as a 202 with an outcome, never a 4xx; only a malformed body, a naive datetime, or an unknown timezone is a 422.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.StoreObligationRequest() # StoreObligationRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Record an obligation
    api_response = api_instance.store_obligation_endpoint_agents_agent_id_obligations_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->store_obligation_endpoint_agents_agent_id_obligations_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**StoreObligationRequest**](StoreObligationRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**StoreObligationAcceptedResponse**](StoreObligationAcceptedResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **supersede_obligation_endpoint_agents_agent_id_obligations_obligation_id_supersede_post**
> ObligationResponse supersede_obligation_endpoint_agents_agent_id_obligations_obligation_id_supersede_post(body, agent_id, obligation_id, timezone=timezone)

Replace an obligation with its successor

Closes this obligation as superseded and writes its successor, linked, in one step. Nothing commits unless the successor lands: a successor that collides with another open obligation on the same key is a 409 and changes nothing. The 200 body is the SUCCESSOR, which is the live row the caller now cares about.

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
api_instance = hyperstruck.ObligationsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.SupersedeObligationRequest() # SupersedeObligationRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
obligation_id = NULL # object | Obligation UUID returned by the obligations store or list endpoint.
timezone = NULL # object | IANA zone to render due_local in on the answer. (optional)

try:
    # Replace an obligation with its successor
    api_response = api_instance.supersede_obligation_endpoint_agents_agent_id_obligations_obligation_id_supersede_post(body, agent_id, obligation_id, timezone=timezone)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ObligationsApi->supersede_obligation_endpoint_agents_agent_id_obligations_obligation_id_supersede_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**SupersedeObligationRequest**](SupersedeObligationRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **obligation_id** | [**object**](.md)| Obligation UUID returned by the obligations store or list endpoint. |
 **timezone** | [**object**](.md)| IANA zone to render due_local in on the answer. | [optional]

### Return type

[**ObligationResponse**](ObligationResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

