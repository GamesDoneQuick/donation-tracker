# Django Donation Tracker API Types

There are three categories of types described in these declarations:

- enums (e.g. BidState)
- models returned from the API (e.g. Donation)
- request arguments for the API (e.g. DonationGet, InterviewPatch)

It does NOT include any actual code, e.g. endpoint definitions.

Any Get argument that is typed as `''` means that the API will treat *any value at all* (including an empty string) as
true. e.g. `/events/?totals` is the same as `/events/?totals=1`.

Certain mutation endpoints will accept multiple types of input when describing a relation, as indicated by `SingleKey`
or similar. e.g. when POSTing a run, you can specify the `event` field as either the numeric id, or the matching`short`
field. A more complicated example is when creating something related to a run, as the uniqueness constraints require 3
values: `name`, `category`, and `event.short`. (e.g. `["Mega Man", "any%", "cgdq"]`)

Certain fields are also typed in a way that indicates the format the server expects, e.g. URLString for the `image`
field on a Prize. This has no meaning client-side other than a validation hint.

For the majority of models that are nested under an Event, the `event` field will be omitted from the data when the
Event is implied by the endpoint, e.g. `/events/20/runs'.
