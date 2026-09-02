# HostLoopClosure

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**avg_seconds_to_close** | **object** |  | [optional]
**half_open** | **object** |  |
**half_open_rate** | **object** |  |
**host** | **object** |  |
**in_flight** | **object** |  | [optional]
**loop_closure_rate** | **object** |  |
**observed** | **object** |  |
**offered** | **object** |  |
**parked** | **object** | Mature runs whose reinforce is held until their observe lands, waiting on a holder that exists. Disjoint from half_open and from parked_stalled: a parked run has not stopped writing back, so it is subtracted from half_open rather than counted in it, and reinforced + parked + half_open accounts for every mature run. | [optional]
**parked_stalled** | **object** | Mature runs parked longer than an observe can legitimately run, so the holder is gone and nothing will spawn them. Counted inside half_open rather than parked, because by then the run is genuinely abandoned. Normally zero; it rises when an observe container dies without running any Python. | [optional]
**reinforced** | **object** |  |
**resolved** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

