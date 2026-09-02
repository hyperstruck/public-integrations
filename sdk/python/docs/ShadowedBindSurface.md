# ShadowedBindSurface

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**binds** | [**ShadowedSurfaceForm**](ShadowedSurfaceForm.md) | The form a goal naming this text actually reaches. |
**is_settled_by_rank** | **object** | Whether a rule chose the winner. True when a canonical name beat an alias, which is deliberate and means the shadowed alias is redundant rather than lost. False when every form is the same kind, so nothing but which row was written first decided which entity a goal binds, and that is the case worth acting on. |
**shadowed** | **object** | The forms it does not reach. Each is registered, and unreachable by its own exact text. |
**surface** | **object** | The folded text both forms share. Not a name anyone typed; the form each fold produced. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

