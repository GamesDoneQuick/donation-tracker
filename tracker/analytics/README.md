# Tracker Analytics

The tracker code is instrumented to automatically create and send out analytics events for a variety of actions. These events allow you to construct real-time logs and dashboards to track information over time that is otherwise not available from the tracker's own models, such as "how much had an event raised at this point in time" or "what states did a donation go through".

However, the tracker does _not_ provide these analytics tools or storage for events internally. Instead, events are gathered throughout the request lifecycle and then emitted over HTTP to an analytics server.

We do not currently have an open-sourced server for reference, but the format that is emitted is relatively simple JSON:

```json
[
  { "event_name": "name_of_event", "properties": { ...event_properties } },
  { "event_name": "another_event", "properties": { ...another_event_properties } }
]
```

This information can then be stored and processed in whatever way works best for you.

# Configuration

There are a number of settings parameters (set in your main `settings.py`) to control analytics behavior:

**`TRACKER_ANALYTICS_INGEST_HOST`** - The URL for sending analytics events to. Example: 'http://localhost:5000'
**`TRACKER_ANALYTICS_NO_EMIT`** - When `True`, track events like normal, but don't actually emit them to the ingest host.
**`TRACKER_ANALYTICS_TEST_MODE`** - When `True`, Use the `test_path` path of the analytics host to send events. This is useful for end-to-end validation.

# Development

The following sections are relevant for making changes to the tracker and instrumentation itself. If you are just using a tracker instance in production, you do not need to do any of these things.

### Adding a new event

For now, events are very loosely defined, and validation of properties and event types should be done on the ingest side (i.e., where events are sent over HTTP).

To add a new event for tracking, add an entry with the name of the event to `AnalyticsEventTypes` in `./events.py`. Then wherever it is relevant in the tracker code, add a call to `analytics.track` with the event's information.

```python
from tracker.analytics import analytics, AnalyticsEventTypes

analytics.track(AnalyticsEventTypes.EVENT_NAME, { 'some-data': 'some-value' })
```
