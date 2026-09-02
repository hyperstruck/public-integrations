# hyperstruck.ReportingApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**chart_data_endpoint_reporting_charts_chart_id_data_post**](ReportingApi.md#chart_data_endpoint_reporting_charts_chart_id_data_post) | **POST** /reporting/charts/{chart_id}/data | Run Chart Data
[**create_chart_endpoint_reporting_charts_post**](ReportingApi.md#create_chart_endpoint_reporting_charts_post) | **POST** /reporting/charts | Create Chart
[**create_dashboard_endpoint_reporting_dashboards_post**](ReportingApi.md#create_dashboard_endpoint_reporting_dashboards_post) | **POST** /reporting/dashboards | Create Dashboard
[**delete_chart_endpoint_reporting_charts_chart_id_delete**](ReportingApi.md#delete_chart_endpoint_reporting_charts_chart_id_delete) | **DELETE** /reporting/charts/{chart_id} | Delete Chart
[**delete_dashboard_endpoint_reporting_dashboards_dashboard_id_delete**](ReportingApi.md#delete_dashboard_endpoint_reporting_dashboards_dashboard_id_delete) | **DELETE** /reporting/dashboards/{dashboard_id} | Delete Dashboard
[**get_chart_endpoint_reporting_charts_chart_id_get**](ReportingApi.md#get_chart_endpoint_reporting_charts_chart_id_get) | **GET** /reporting/charts/{chart_id} | Get Chart
[**get_dashboard_endpoint_reporting_dashboards_dashboard_id_get**](ReportingApi.md#get_dashboard_endpoint_reporting_dashboards_dashboard_id_get) | **GET** /reporting/dashboards/{dashboard_id} | Get Dashboard
[**get_defaults_endpoint_reporting_defaults_space_id_get**](ReportingApi.md#get_defaults_endpoint_reporting_defaults_space_id_get) | **GET** /reporting/defaults/{space_id} | Get Reporting Defaults
[**get_metric_catalog_endpoint_reporting_metric_catalog_get**](ReportingApi.md#get_metric_catalog_endpoint_reporting_metric_catalog_get) | **GET** /reporting/metric-catalog | Get Metric Catalog
[**list_charts_endpoint_reporting_charts_get**](ReportingApi.md#list_charts_endpoint_reporting_charts_get) | **GET** /reporting/charts | List Charts
[**list_dashboards_endpoint_reporting_dashboards_get**](ReportingApi.md#list_dashboards_endpoint_reporting_dashboards_get) | **GET** /reporting/dashboards | List Dashboards
[**put_dashboard_items_endpoint_reporting_dashboards_dashboard_id_items_put**](ReportingApi.md#put_dashboard_items_endpoint_reporting_dashboards_dashboard_id_items_put) | **PUT** /reporting/dashboards/{dashboard_id}/items | Replace Dashboard Items
[**put_defaults_endpoint_reporting_defaults_space_id_put**](ReportingApi.md#put_defaults_endpoint_reporting_defaults_space_id_put) | **PUT** /reporting/defaults/{space_id} | Put Reporting Defaults
[**reporting_query_endpoint_reporting_query_post**](ReportingApi.md#reporting_query_endpoint_reporting_query_post) | **POST** /reporting/query | Run Reporting Query
[**update_chart_endpoint_reporting_charts_chart_id_patch**](ReportingApi.md#update_chart_endpoint_reporting_charts_chart_id_patch) | **PATCH** /reporting/charts/{chart_id} | Update Chart
[**update_dashboard_endpoint_reporting_dashboards_dashboard_id_patch**](ReportingApi.md#update_dashboard_endpoint_reporting_dashboards_dashboard_id_patch) | **PATCH** /reporting/dashboards/{dashboard_id} | Update Dashboard

# **chart_data_endpoint_reporting_charts_chart_id_data_post**
> ReportingQueryResponse chart_data_endpoint_reporting_charts_chart_id_data_post(chart_id, body=body)

Run Chart Data

Run the stored query_binding for a visible chart (Mode B).

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
chart_id = NULL # object | Reporting chart UUID returned by the chart create or list endpoint.
body = NULL # object |  (optional)

try:
    # Run Chart Data
    api_response = api_instance.chart_data_endpoint_reporting_charts_chart_id_data_post(chart_id, body=body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->chart_data_endpoint_reporting_charts_chart_id_data_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **chart_id** | [**object**](.md)| Reporting chart UUID returned by the chart create or list endpoint. |
 **body** | [**object**](object.md)|  | [optional]

### Return type

[**ReportingQueryResponse**](ReportingQueryResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_chart_endpoint_reporting_charts_post**
> ChartResponse create_chart_endpoint_reporting_charts_post(body)

Create Chart

Create a chart in a space (portal: private to the user until published; API key: null-owner draft shared among keys in the tenant). Requires can_publish on the space.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ChartCreateRequest() # ChartCreateRequest |

try:
    # Create Chart
    api_response = api_instance.create_chart_endpoint_reporting_charts_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->create_chart_endpoint_reporting_charts_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ChartCreateRequest**](ChartCreateRequest.md)|  |

### Return type

[**ChartResponse**](ChartResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_dashboard_endpoint_reporting_dashboards_post**
> DashboardResponse create_dashboard_endpoint_reporting_dashboards_post(body)

Create Dashboard

Create an empty multi-chart dashboard in a space. Requires can_publish on the space.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.DashboardCreateRequest() # DashboardCreateRequest |

try:
    # Create Dashboard
    api_response = api_instance.create_dashboard_endpoint_reporting_dashboards_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->create_dashboard_endpoint_reporting_dashboards_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**DashboardCreateRequest**](DashboardCreateRequest.md)|  |

### Return type

[**DashboardResponse**](DashboardResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_chart_endpoint_reporting_charts_chart_id_delete**
> delete_chart_endpoint_reporting_charts_chart_id_delete(chart_id)

Delete Chart

Delete a visible chart. Charts linked on dashboards are removed from those canvases via cascade. Requires can_publish on the chart's space.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
chart_id = NULL # object | Reporting chart UUID returned by the chart create or list endpoint.

try:
    # Delete Chart
    api_instance.delete_chart_endpoint_reporting_charts_chart_id_delete(chart_id)
except ApiException as e:
    print("Exception when calling ReportingApi->delete_chart_endpoint_reporting_charts_chart_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **chart_id** | [**object**](.md)| Reporting chart UUID returned by the chart create or list endpoint. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_dashboard_endpoint_reporting_dashboards_dashboard_id_delete**
> delete_dashboard_endpoint_reporting_dashboards_dashboard_id_delete(dashboard_id)

Delete Dashboard

Delete a dashboard and its placements. Charts themselves are kept. Requires can_publish on the dashboard's space.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
dashboard_id = NULL # object | Reporting dashboard UUID returned by the dashboard create or list endpoint.

try:
    # Delete Dashboard
    api_instance.delete_dashboard_endpoint_reporting_dashboards_dashboard_id_delete(dashboard_id)
except ApiException as e:
    print("Exception when calling ReportingApi->delete_dashboard_endpoint_reporting_dashboards_dashboard_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dashboard_id** | [**object**](.md)| Reporting dashboard UUID returned by the dashboard create or list endpoint. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_chart_endpoint_reporting_charts_chart_id_get**
> ChartResponse get_chart_endpoint_reporting_charts_chart_id_get(chart_id)

Get Chart

Return a chart the caller can see: their own draft, a tenant-shared API-key draft, or a chart linked on a readable dashboard.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
chart_id = NULL # object | Reporting chart UUID returned by the chart create or list endpoint.

try:
    # Get Chart
    api_response = api_instance.get_chart_endpoint_reporting_charts_chart_id_get(chart_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->get_chart_endpoint_reporting_charts_chart_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **chart_id** | [**object**](.md)| Reporting chart UUID returned by the chart create or list endpoint. |

### Return type

[**ChartResponse**](ChartResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_dashboard_endpoint_reporting_dashboards_dashboard_id_get**
> DashboardResponse get_dashboard_endpoint_reporting_dashboards_dashboard_id_get(dashboard_id)

Get Dashboard

Return a dashboard and its chart placements when the caller can read the dashboard's space.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
dashboard_id = NULL # object | Reporting dashboard UUID returned by the dashboard create or list endpoint.

try:
    # Get Dashboard
    api_response = api_instance.get_dashboard_endpoint_reporting_dashboards_dashboard_id_get(dashboard_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->get_dashboard_endpoint_reporting_dashboards_dashboard_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dashboard_id** | [**object**](.md)| Reporting dashboard UUID returned by the dashboard create or list endpoint. |

### Return type

[**DashboardResponse**](DashboardResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_defaults_endpoint_reporting_defaults_space_id_get**
> ReportingDefaultsResponse get_defaults_endpoint_reporting_defaults_space_id_get(space_id)

Get Reporting Defaults

Return space hyperparameters used to derive dollar measures. Missing rows fall back to product defaults. Requires space viewer.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # Get Reporting Defaults
    api_response = api_instance.get_defaults_endpoint_reporting_defaults_space_id_get(space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->get_defaults_endpoint_reporting_defaults_space_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

[**ReportingDefaultsResponse**](ReportingDefaultsResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_metric_catalog_endpoint_reporting_metric_catalog_get**
> MetricCatalogResponse get_metric_catalog_endpoint_reporting_metric_catalog_get()

Get Metric Catalog

Starter dimensions and measures for Graphic Walker field pickers.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))

try:
    # Get Metric Catalog
    api_response = api_instance.get_metric_catalog_endpoint_reporting_metric_catalog_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->get_metric_catalog_endpoint_reporting_metric_catalog_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**MetricCatalogResponse**](MetricCatalogResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_charts_endpoint_reporting_charts_get**
> ChartListResponse list_charts_endpoint_reporting_charts_get(space_id=space_id)

List Charts

List charts visible to the caller: portal users see their own drafts plus charts linked on a dashboard in a readable space; API keys see tenant-shared null-owner drafts plus those published charts.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
space_id = NULL # object |  (optional)

try:
    # List Charts
    api_response = api_instance.list_charts_endpoint_reporting_charts_get(space_id=space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->list_charts_endpoint_reporting_charts_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **space_id** | [**object**](.md)|  | [optional]

### Return type

[**ChartListResponse**](ChartListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_dashboards_endpoint_reporting_dashboards_get**
> DashboardListResponse list_dashboards_endpoint_reporting_dashboards_get(space_id=space_id)

List Dashboards

List multi-chart dashboards in spaces the caller can read. Optionally filter with `space_id`.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
space_id = NULL # object |  (optional)

try:
    # List Dashboards
    api_response = api_instance.list_dashboards_endpoint_reporting_dashboards_get(space_id=space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->list_dashboards_endpoint_reporting_dashboards_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **space_id** | [**object**](.md)|  | [optional]

### Return type

[**DashboardListResponse**](DashboardListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **put_dashboard_items_endpoint_reporting_dashboards_dashboard_id_items_put**
> DashboardResponse put_dashboard_items_endpoint_reporting_dashboards_dashboard_id_items_put(body, dashboard_id)

Replace Dashboard Items

Replace all chart placements on a dashboard. Linking a chart publishes it to space viewers. Validates col_index + col_span <= columns.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.DashboardItemsPutRequest() # DashboardItemsPutRequest |
dashboard_id = NULL # object | Reporting dashboard UUID returned by the dashboard create or list endpoint.

try:
    # Replace Dashboard Items
    api_response = api_instance.put_dashboard_items_endpoint_reporting_dashboards_dashboard_id_items_put(body, dashboard_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->put_dashboard_items_endpoint_reporting_dashboards_dashboard_id_items_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**DashboardItemsPutRequest**](DashboardItemsPutRequest.md)|  |
 **dashboard_id** | [**object**](.md)| Reporting dashboard UUID returned by the dashboard create or list endpoint. |

### Return type

[**DashboardResponse**](DashboardResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **put_defaults_endpoint_reporting_defaults_space_id_put**
> ReportingDefaultsResponse put_defaults_endpoint_reporting_defaults_space_id_put(body, space_id)

Put Reporting Defaults

Replace space hyperparameters. Requires space steward (organization admins also qualify as stewards).

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ReportingDefaultsPutRequest() # ReportingDefaultsPutRequest |
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # Put Reporting Defaults
    api_response = api_instance.put_defaults_endpoint_reporting_defaults_space_id_put(body, space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->put_defaults_endpoint_reporting_defaults_space_id_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ReportingDefaultsPutRequest**](ReportingDefaultsPutRequest.md)|  |
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

[**ReportingDefaultsResponse**](ReportingDefaultsResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reporting_query_endpoint_reporting_query_post**
> ReportingQueryResponse reporting_query_endpoint_reporting_query_post(body)

Run Reporting Query

Mode B: server-side aggregate of daily reporting facts for a query binding. Dollar measures are derived at read time from space defaults.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ReportingQueryRequest() # ReportingQueryRequest |

try:
    # Run Reporting Query
    api_response = api_instance.reporting_query_endpoint_reporting_query_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->reporting_query_endpoint_reporting_query_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ReportingQueryRequest**](ReportingQueryRequest.md)|  |

### Return type

[**ReportingQueryResponse**](ReportingQueryResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_chart_endpoint_reporting_charts_chart_id_patch**
> ChartResponse update_chart_endpoint_reporting_charts_chart_id_patch(body, chart_id)

Update Chart

Update title, description, viz spec, or query binding for a visible chart. Requires can_publish on the chart's space.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ChartUpdateRequest() # ChartUpdateRequest |
chart_id = NULL # object | Reporting chart UUID returned by the chart create or list endpoint.

try:
    # Update Chart
    api_response = api_instance.update_chart_endpoint_reporting_charts_chart_id_patch(body, chart_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->update_chart_endpoint_reporting_charts_chart_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ChartUpdateRequest**](ChartUpdateRequest.md)|  |
 **chart_id** | [**object**](.md)| Reporting chart UUID returned by the chart create or list endpoint. |

### Return type

[**ChartResponse**](ChartResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_dashboard_endpoint_reporting_dashboards_dashboard_id_patch**
> DashboardResponse update_dashboard_endpoint_reporting_dashboards_dashboard_id_patch(body, dashboard_id)

Update Dashboard

Update dashboard metadata such as title, description, columns, or window preset. Requires can_publish on the dashboard's space.

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
api_instance = hyperstruck.ReportingApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.DashboardUpdateRequest() # DashboardUpdateRequest |
dashboard_id = NULL # object | Reporting dashboard UUID returned by the dashboard create or list endpoint.

try:
    # Update Dashboard
    api_response = api_instance.update_dashboard_endpoint_reporting_dashboards_dashboard_id_patch(body, dashboard_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ReportingApi->update_dashboard_endpoint_reporting_dashboards_dashboard_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**DashboardUpdateRequest**](DashboardUpdateRequest.md)|  |
 **dashboard_id** | [**object**](.md)| Reporting dashboard UUID returned by the dashboard create or list endpoint. |

### Return type

[**DashboardResponse**](DashboardResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

