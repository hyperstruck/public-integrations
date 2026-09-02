# ReconciliationResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_truncated** | **object** | True when the scan did not complete within its time budget, so the items are not a measurement of anything. Surfaced rather than silent, because a short list would read identically to a source that was never observed, which is the single inference this view exists to make safe. A further page is next_cursor, not this. | [optional]
**items** | **object** |  |
**next_cursor** | **object** | Present when another page follows. Ordinary paging, and deliberately not the same thing as the truncation flag below. | [optional]
**reach** | [**SpaceReach**](SpaceReach.md) |  |
**unlistable_source_count** | **object** | Declared sources this view refuses to list because their id is longer than a grant may ever be. They are reported as a count rather than dropped in silence: such an id is a source arriving with no grant and no way to make one, and the caller supplying the corpus chooses it. | [optional]
**unreachable_grant_count** | **object** | Live grants in this tenant stored under a space id no lookup can produce, so they match nothing, cannot be revoked through the API (revocation resolves the same projection and addresses a different row) and are absent from the items above. A commons space is addressed by the slug and never by its row uuid; a grant written the other way is inert, as are a grant on a uuid naming no space and a grant on a misspelt slug, and all three are counted. Counted rather than listed because the cure is a direct write. **Null means not measured**, which a truncated scan and every page after the first both are: it is tenant-wide, so it is read once per walk rather than per page, and zero would say &#x27;no unreachable grants&#x27;, which is the opposite answer. Reported at all because this view could previously see every grant EXCEPT the ones it exists to find. On 2026-09-07 one such row cost 516 claims their channel trust. | [optional]
**unscoped_claim_count** | **object** | Claims in this tenant carrying no space at all. They are invisible to the observed side, because equality never matches null, so a non-zero count here is why a grant may report as never observed while its facts are being harvested. It is the difference between &#x27;this source was never seen&#x27; and &#x27;nothing here is space-scoped yet&#x27;. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

