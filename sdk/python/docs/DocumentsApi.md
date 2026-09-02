# hyperstruck.DocumentsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**count_documents_endpoint_agents_agent_id_documents_count_get**](DocumentsApi.md#count_documents_endpoint_agents_agent_id_documents_count_get) | **GET** /agents/{agent_id}/documents:count | Count an agent&#x27;s documents by state
[**document_neighbours_endpoint_agents_agent_id_documents_neighbours_search_post**](DocumentsApi.md#document_neighbours_endpoint_agents_agent_id_documents_neighbours_search_post) | **POST** /agents/{agent_id}/documents/neighbours:search | The documents filed beside one in the same container
[**erase_document_endpoint_agents_agent_id_documents_doc_id_delete**](DocumentsApi.md#erase_document_endpoint_agents_agent_id_documents_doc_id_delete) | **DELETE** /agents/{agent_id}/documents/{doc_id} | Erase a document
[**get_document_endpoint_agents_agent_id_documents_doc_id_get**](DocumentsApi.md#get_document_endpoint_agents_agent_id_documents_doc_id_get) | **GET** /agents/{agent_id}/documents/{doc_id} | Fetch a document and its versions
[**list_documents_endpoint_agents_agent_id_documents_get**](DocumentsApi.md#list_documents_endpoint_agents_agent_id_documents_get) | **GET** /agents/{agent_id}/documents | List an agent&#x27;s documents
[**read_text_window_endpoint_agents_agent_id_documents_text_window_post**](DocumentsApi.md#read_text_window_endpoint_agents_agent_id_documents_text_window_post) | **POST** /agents/{agent_id}/documents/text:window | Read a document version&#x27;s text around one unit
[**resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post**](DocumentsApi.md#resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post) | **POST** /agents/{agent_id}/documents/citations:resolve | Resolve a citation to the passage it points at
[**search_documents_endpoint_agents_agent_id_documents_ids_search_post**](DocumentsApi.md#search_documents_endpoint_agents_agent_id_documents_ids_search_post) | **POST** /agents/{agent_id}/documents/ids:search | Find an agent&#x27;s documents by the start of their id
[**submit_document_endpoint_agents_agent_id_documents_doc_id_put**](DocumentsApi.md#submit_document_endpoint_agents_agent_id_documents_doc_id_put) | **PUT** /agents/{agent_id}/documents/{doc_id} | Submit a document version

# **count_documents_endpoint_agents_agent_id_documents_count_get**
> DocumentCountsResponse count_documents_endpoint_agents_agent_id_documents_count_get(agent_id)

Count an agent's documents by state

How many documents the agent holds in each state. The five states sum to `total`. `completed_last_10_minutes` is the number of uploads that finished ingesting in that window, which is the rate a sync is being read at.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Count an agent's documents by state
    api_response = api_instance.count_documents_endpoint_agents_agent_id_documents_count_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->count_documents_endpoint_agents_agent_id_documents_count_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**DocumentCountsResponse**](DocumentCountsResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **document_neighbours_endpoint_agents_agent_id_documents_neighbours_search_post**
> DocumentNeighboursResponse document_neighbours_endpoint_agents_agent_id_documents_neighbours_search_post(body, agent_id, reveal=reveal)

The documents filed beside one in the same container

The documents filed in the same container as `doc_id` (a chat channel, for one) just before and just after it, by the time each declared, each with its opening words. Only documents whose text is kept are named, so an erased or unprocessed one is left out. A document that declares only a thread is filed under that thread.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.DocumentNeighboursRequest() # DocumentNeighboursRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # The documents filed beside one in the same container
    api_response = api_instance.document_neighbours_endpoint_agents_agent_id_documents_neighbours_search_post(body, agent_id, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->document_neighbours_endpoint_agents_agent_id_documents_neighbours_search_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**DocumentNeighboursRequest**](DocumentNeighboursRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**DocumentNeighboursResponse**](DocumentNeighboursResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **erase_document_endpoint_agents_agent_id_documents_doc_id_delete**
> DocumentErasureResponse erase_document_endpoint_agents_agent_id_documents_doc_id_delete(agent_id, doc_id)

Erase a document

Destroys the wrapped data keys first, so from that instant every copy they protect is unreadable whether or not the deletes that follow complete, and returns a receipt naming what each scope actually reached. Any queued or running ingest for this document is cancelled: a deletion request is the one operation that must never queue behind other work. The learnings distilled from the document are reported in two scopes: `learnings` counts those deleted because only this document supported them, and `learning_citations` counts those kept on their other sources with this document removed. Either scope reads `not_tracked` when the document was only distilled before learnings recorded their source, and `deleted_incomplete` when only some of its distillations were, so a zero is never reported for learnings the erasure could not have found.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
doc_id = NULL # object | The caller's own key for this document. It may contain slashes: the repository content ingest mints `{owner}/{repo}:{path}`, one file to one document.

try:
    # Erase a document
    api_response = api_instance.erase_document_endpoint_agents_agent_id_documents_doc_id_delete(agent_id, doc_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->erase_document_endpoint_agents_agent_id_documents_doc_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **doc_id** | [**object**](.md)| The caller&#x27;s own key for this document. It may contain slashes: the repository content ingest mints &#x60;{owner}/{repo}:{path}&#x60;, one file to one document. |

### Return type

[**DocumentErasureResponse**](DocumentErasureResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_document_endpoint_agents_agent_id_documents_doc_id_get**
> DocumentResponse get_document_endpoint_agents_agent_id_documents_doc_id_get(agent_id, doc_id, job_id=job_id, reveal=reveal)

Fetch a document and its versions

Returns the document, its raw versions, and TWO separate state fields. `ingest` is the queue's view (`queued`, `ingesting`, `ingested`, `failed`); `version_state` is Core's own, present once a version exists. They are never conflated, because `superseded` is citable by design and is not a failure. A `doc_id` with neither a job nor a version is 404, so a typo is distinguishable from a queue.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
doc_id = NULL # object | The caller's own key for this document. It may contain slashes: the repository content ingest mints `{owner}/{repo}:{path}`, one file to one document.
job_id = NULL # object | The `job_id` a PUT returned. When given, `ingest` and `ingest_error` describe that upload's own job, so an upload that a newer one cancelled shows why. (optional)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Fetch a document and its versions
    api_response = api_instance.get_document_endpoint_agents_agent_id_documents_doc_id_get(agent_id, doc_id, job_id=job_id, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->get_document_endpoint_agents_agent_id_documents_doc_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **doc_id** | [**object**](.md)| The caller&#x27;s own key for this document. It may contain slashes: the repository content ingest mints &#x60;{owner}/{repo}:{path}&#x60;, one file to one document. |
 **job_id** | [**object**](.md)| The &#x60;job_id&#x60; a PUT returned. When given, &#x60;ingest&#x60; and &#x60;ingest_error&#x60; describe that upload&#x27;s own job, so an upload that a newer one cancelled shows why. | [optional]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**DocumentResponse**](DocumentResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_documents_endpoint_agents_agent_id_documents_get**
> DocumentListResponse list_documents_endpoint_agents_agent_id_documents_get(agent_id, state=state, limit=limit, cursor=cursor, reveal=reveal)

List an agent's documents

The agent's documents, newest arrival first, each with its one `state`. A document that was sent again is listed once, at its newest upload. A deleted document is not listed. Page with `cursor` until `next_cursor` is absent.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
state = NULL # object | Only documents in this state. Repeat it to admit several. (optional)
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # List an agent's documents
    api_response = api_instance.list_documents_endpoint_agents_agent_id_documents_get(agent_id, state=state, limit=limit, cursor=cursor, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->list_documents_endpoint_agents_agent_id_documents_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **state** | [**object**](.md)| Only documents in this state. Repeat it to admit several. | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**DocumentListResponse**](DocumentListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **read_text_window_endpoint_agents_agent_id_documents_text_window_post**
> TextWindowResponse read_text_window_endpoint_agents_agent_id_documents_text_window_post(body, agent_id, reveal=reveal)

Read a document version's text around one unit

Any document of this agent the caller's spaces admit, not only cited ones: resolve's reach.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.TextWindowRequest() # TextWindowRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Read a document version's text around one unit
    api_response = api_instance.read_text_window_endpoint_agents_agent_id_documents_text_window_post(body, agent_id, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->read_text_window_endpoint_agents_agent_id_documents_text_window_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**TextWindowRequest**](TextWindowRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**TextWindowResponse**](TextWindowResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post**
> CitationResolutionResponse resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post(body, agent_id, reveal=reveal)

Resolve a citation to the passage it points at

Turns a shelf record's six-member citation back into the text it points at, or a defined refusal. The four outcomes are kept distinct: `resolved`, `truncated` (the stored excerpt is bounded and the span reaches past it), `erased`, and `missing`.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ResolveCitationRequest() # ResolveCitationRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Resolve a citation to the passage it points at
    api_response = api_instance.resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post(body, agent_id, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ResolveCitationRequest**](ResolveCitationRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**CitationResolutionResponse**](CitationResolutionResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_documents_endpoint_agents_agent_id_documents_ids_search_post**
> DocumentSearchResponse search_documents_endpoint_agents_agent_id_documents_ids_search_post(body, agent_id, reveal=reveal)

Find an agent's documents by the start of their id

Documents whose id starts with `doc_id_prefix`, in id order. The match is exact and case-sensitive, so a Slack timestamp or an email Message-ID is sent as it is.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.DocumentSearchRequest() # DocumentSearchRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Find an agent's documents by the start of their id
    api_response = api_instance.search_documents_endpoint_agents_agent_id_documents_ids_search_post(body, agent_id, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->search_documents_endpoint_agents_agent_id_documents_ids_search_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**DocumentSearchRequest**](DocumentSearchRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**DocumentSearchResponse**](DocumentSearchResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **submit_document_endpoint_agents_agent_id_documents_doc_id_put**
> DocumentSubmissionResponse submit_document_endpoint_agents_agent_id_documents_doc_id_put(content, metadata, agent_id, doc_id, x_document_type=x_document_type, x_document_filename=x_document_filename)

Submit a document version

Store one submission under the caller's own document key and queue it for ingest. Returns 202 with the new version when work was enqueued, and 200 with the existing version when identical bytes are already stored: a 202 on a duplicate would promise work that will not happen. Refuses 409 when the tenant has no document key binding, 413 above the configured size ceiling, and 404 for an unknown agent, in each case without enqueueing anything.  Send `multipart/form-data` with a `content` part and a `metadata` part: JSON carrying the compulsory `channel` (`unknown` when you do not know how the document reached you), and optionally `title`, `occurred_at` and a `record_context` in `/distill`'s schema. The metadata is what links the document to its account and dates it, and the claims read from the document carry both. A `source_url` is the link an answer citing the document shows. Bytes identical to a stored version are not read again: their metadata fills a `title`, `source_url`, `occurred_at` or `channel` the stored version lacks (a stored `unknown` channel counts as lacking), and never replaces one it has, except that a held `occurred_at` without a real offset (`+00:00`) takes the same instant stated with one; a stated `occurred_at` later than the arrival of the earliest stored version of the same text is not filled, and a time that is filled lands on that version. A title declared this way does replace one derived from the document's own pages, in the answers that cite it.

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
api_instance = hyperstruck.DocumentsApi(hyperstruck.ApiClient(configuration))
content = NULL # object |
metadata = hyperstruck.DocumentMetadataModel() # DocumentMetadataModel |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
doc_id = NULL # object | The caller's own key for this document. It may contain slashes: the repository content ingest mints `{owner}/{repo}:{path}`, one file to one document.
x_document_type = markdown # object | How to read the bytes: `markdown` (the default), `text`, `html`, `pdf` or `docx`. (optional) (default to markdown)
x_document_filename = NULL # object | The name the document is shown under. A multipart `content` part's own filename is used when this is absent. (optional)

try:
    # Submit a document version
    api_response = api_instance.submit_document_endpoint_agents_agent_id_documents_doc_id_put(content, metadata, agent_id, doc_id, x_document_type=x_document_type, x_document_filename=x_document_filename)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->submit_document_endpoint_agents_agent_id_documents_doc_id_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **content** | [**object**](.md)|  |
 **metadata** | [**DocumentMetadataModel**](.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **doc_id** | [**object**](.md)| The caller&#x27;s own key for this document. It may contain slashes: the repository content ingest mints &#x60;{owner}/{repo}:{path}&#x60;, one file to one document. |
 **x_document_type** | [**object**](.md)| How to read the bytes: &#x60;markdown&#x60; (the default), &#x60;text&#x60;, &#x60;html&#x60;, &#x60;pdf&#x60; or &#x60;docx&#x60;. | [optional] [default to markdown]
 **x_document_filename** | [**object**](.md)| The name the document is shown under. A multipart &#x60;content&#x60; part&#x27;s own filename is used when this is absent. | [optional]

### Return type

[**DocumentSubmissionResponse**](DocumentSubmissionResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

