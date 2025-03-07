import React from 'react';
import { useParams } from 'react-router';

import { useConstants } from '@common/Constants';
import { useCSRFToken } from '@public/apiv2/helpers/auth';
import { Event, OrderedRun, Run, UnorderedRun } from '@public/apiv2/Models';
import { setRoot, useEventsQuery } from '@public/apiv2/reducers/trackerApi';
import { useAppDispatch } from '@public/apiv2/Store';

export function useEventParam() {
  const { eventId } = useParams<{ eventId: string }>();
  if (!eventId || !+eventId) {
    throw new Error('could not find valid event id in url');
  }
  return +eventId;
}

export function useEventFromQuery(id: number | string, params?: Parameters<typeof useEventsQuery>[0]) {
  if (typeof id === 'string' && /^\d+$/.test(id)) {
    id = +id;
  }
  const finder = typeof id === 'number' ? (e: Event) => e.id === id : (e: Event) => e.short === id;
  return useEventsQuery(params, {
    selectFromResult: ({ data, error, ...rest }) => {
      const event = data?.find(finder);
      return {
        data: event,
        id: typeof id === 'number' ? id : event?.id,
        path: id,
        // fetch succeeded, but we couldn't find a matching event
        error: !event && rest.isSuccess ? { status: 404, statusText: 'Event does not exist in provided query' } : error,
        ...rest,
      };
    },
  });
}

// unlike useEventParam this will return an error if the eventId is missing or invalid, rather than throwing, and will also accept string matches against `short`

export function useEventFromRoute() {
  const { eventId } = useParams<{ eventId: string }>();
  return useEventFromQuery(eventId || '');
}

// TODO: helpers for the event-reliant queries to make them easier to use when eventId might be `id` -or- `short`

export function useSplitRuns(runs?: Run[]): [OrderedRun[], UnorderedRun[]] {
  const orderedRuns = React.useMemo(
    () => (runs || []).filter((r): r is OrderedRun => r.order != null).sort((a, b) => a.order - b.order),
    [runs],
  );
  const unorderedRuns = React.useMemo(
    () => (runs || []).filter((r): r is UnorderedRun => r.order == null).sort((a, b) => a.name.localeCompare(b.name)),
    [runs],
  );

  return [orderedRuns, unorderedRuns];
}

export function useTrackerInit() {
  const dispatch = useAppDispatch();
  const { APIV2_ROOT, PAGINATION_LIMIT } = useConstants();
  const csrfToken = useCSRFToken();
  React.useLayoutEffect(() => {
    dispatch(setRoot({ root: APIV2_ROOT, limit: PAGINATION_LIMIT, csrfToken }));
  }, [APIV2_ROOT, csrfToken, PAGINATION_LIMIT, dispatch]);
}
