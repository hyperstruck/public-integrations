# EpisodeSpanModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**origin** | **object** | Where this stretch came from: &#x60;user_prose&#x60;, &#x60;assistant_prose&#x60;, &#x60;tool_result&#x60; or &#x60;harness&#x60;. &#x60;harness&#x60; is machine text the host put in the turn (a slash-command envelope, a background-task notification, a system reminder), and it is removed before any producer reads the episode. An origin this deployment does not know is read as &#x60;user_prose&#x60; and counted, never refused. |
**source** | **object** | Who decided this span&#x27;s origin. Counted, so a client that stops tagging shows up as a number. | [optional]
**text** | **object** | The exact substring of &#x60;goal&#x60; this span covers. Matched to the goal by content, in order, so it must appear verbatim: a span that cannot be found discards the whole tagging for that episode and the goal is labelled by the closed markup set instead. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

