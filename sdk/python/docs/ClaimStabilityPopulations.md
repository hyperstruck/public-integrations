# ClaimStabilityPopulations

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**admitted_slots** | **object** | What the axis would admit right now. An upper bound on read elimination, not a count of it: the bind gate independently refuses a currency-decayed claim and a high-stakes attribute key, neither of which this axis judges. |
**bindable_slots** | **object** | Keyed, open, non-quarantined slots: the population the axis judges at all. |
**confidence** | **object** | The deployment&#x27;s stability confidence this count was evaluated at. |
**lapsed_slots** | **object** | Slots with demonstrated survival whose licence no longer covers the gap since. |
**mean_survived_days** | **object** | total_survived_days divided by re_observed_slots, not by bindable_slots, so the numerator and denominator cover the same population. Zero when nothing was re-observed. |
**never_re_observed_slots** | **object** | Slots never seen to hold for any elapsed time. A cold corpus is nearly all of these. |
**prior_changes** | **object** | The deployment&#x27;s stability prior-changes this count was evaluated at. |
**re_observed_slots** | **object** | Slots with any demonstrated survival, which is the population that can qualify. |
**slots_with_a_recorded_change** | **object** | Slots observed to have moved to a different value at least once. |
**total_survived_days** | **object** | Demonstrated survival summed over the re-observed slots only. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

