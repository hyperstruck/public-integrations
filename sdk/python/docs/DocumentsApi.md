# hyperstruck.DocumentsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**erase_document_endpoint_agents_agent_id_documents_doc_id_delete**](DocumentsApi.md#erase_document_endpoint_agents_agent_id_documents_doc_id_delete) | **DELETE** /agents/{agent_id}/documents/{doc_id} | Erase a document
[**get_document_endpoint_agents_agent_id_documents_doc_id_get**](DocumentsApi.md#get_document_endpoint_agents_agent_id_documents_doc_id_get) | **GET** /agents/{agent_id}/documents/{doc_id} | Fetch a document and its versions
[**read_text_window_endpoint_agents_agent_id_documents_text_window_post**](DocumentsApi.md#read_text_window_endpoint_agents_agent_id_documents_text_window_post) | **POST** /agents/{agent_id}/documents/text:window | Read a document version&#x27;s text around one unit
[**resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post**](DocumentsApi.md#resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post) | **POST** /agents/{agent_id}/documents/citations:resolve | Resolve a citation to the passage it points at
[**submit_document_endpoint_agents_agent_id_documents_doc_id_put**](DocumentsApi.md#submit_document_endpoint_agents_agent_id_documents_doc_id_put) | **PUT** /agents/{agent_id}/documents/{doc_id} | Submit a document version

# **erase_document_endpoint_agents_agent_id_documents_doc_id_delete**
> DocumentErasureResponse erase_document_endpoint_agents_agent_id_documents_doc_id_delete(agent_id, doc_id)

Erase a document

Destroys the wrapped data keys first, so from that instant every copy they protect is unreadable whether or not the deletes that follow complete, and returns a receipt naming what each scope actually reached. Any queued or running ingest for this document is cancelled: a deletion request is the one operation that must never queue behind other work.

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
> DocumentResponse get_document_endpoint_agents_agent_id_documents_doc_id_get(agent_id, doc_id)

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

try:
    # Fetch a document and its versions
    api_response = api_instance.get_document_endpoint_agents_agent_id_documents_doc_id_get(agent_id, doc_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->get_document_endpoint_agents_agent_id_documents_doc_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **doc_id** | [**object**](.md)| The caller&#x27;s own key for this document. It may contain slashes: the repository content ingest mints &#x60;{owner}/{repo}:{path}&#x60;, one file to one document. |

### Return type

[**DocumentResponse**](DocumentResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **read_text_window_endpoint_agents_agent_id_documents_text_window_post**
> TextWindowResponse read_text_window_endpoint_agents_agent_id_documents_text_window_post(body, agent_id)

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

try:
    # Read a document version's text around one unit
    api_response = api_instance.read_text_window_endpoint_agents_agent_id_documents_text_window_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->read_text_window_endpoint_agents_agent_id_documents_text_window_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**TextWindowRequest**](TextWindowRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**TextWindowResponse**](TextWindowResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post**
> CitationResolutionResponse resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post(body, agent_id)

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

try:
    # Resolve a citation to the passage it points at
    api_response = api_instance.resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->resolve_citation_endpoint_agents_agent_id_documents_citations_resolve_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ResolveCitationRequest**](ResolveCitationRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**CitationResolutionResponse**](CitationResolutionResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **submit_document_endpoint_agents_agent_id_documents_doc_id_put**
> DocumentSubmissionResponse submit_document_endpoint_agents_agent_id_documents_doc_id_put(body, agent_id, doc_id)

Submit a document version

Store one submission under the caller's own document key and queue it for ingest. Returns 202 with the new version when work was enqueued, and 200 with the existing version when identical bytes are already stored: a 202 on a duplicate would promise work that will not happen. Refuses 409 when the tenant has no document key binding, 413 above the configured size ceiling, and 404 for an unknown agent, in each case without enqueueing anything.  Send the raw bytes as the body, or `multipart/form-data` with a `content` part and a `metadata` part: JSON carrying `title`, `occurred_at` and a `record_context` in `/distill`'s schema. The metadata is what links the document to its account and dates it, and the claims read from the document carry both. Metadata sent with bytes identical to a stored version is not applied, because nothing is re-read.

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
body = NULL # object |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
doc_id = NULL # object | The caller's own key for this document. It may contain slashes: the repository content ingest mints `{owner}/{repo}:{path}`, one file to one document.

try:
    # Submit a document version
    api_response = api_instance.submit_document_endpoint_agents_agent_id_documents_doc_id_put(body, agent_id, doc_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DocumentsApi->submit_document_endpoint_agents_agent_id_documents_doc_id_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**object**](object.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **doc_id** | [**object**](.md)| The caller&#x27;s own key for this document. It may contain slashes: the repository content ingest mints &#x60;{owner}/{repo}:{path}&#x60;, one file to one document. |

### Return type

[**DocumentSubmissionResponse**](DocumentSubmissionResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/octet-stream, multipart/form-data
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

