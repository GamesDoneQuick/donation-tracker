import React from 'react';
import { useParams } from 'react-router';

import { useConstants } from '@common/Constants';
import { useCSRFToken } from '@public/apiv2/helpers/auth';
import { OrderedRun, Run, UnorderedRun } from '@public/apiv2/Models';
import { setRoot, useEventsQuery } from '@public/apiv2/reducers/trackerApi';
import { useAppDispatch } from '@public/apiv2/Store';

export function useEventParam() {
  const { eventId } = useParams<{ eventId: string }>();
  if (!eventId || !+eventId) {
    throw new Error('could not find valid event id in url');
  }
  return +eventId;
}

export function useEventFromQuery(id: number, params?: Parameters<typeof useEventsQuery>[0]) {
  return useEventsQuery(params, {
    selectFromResult: ({ data, error, ...rest }) => {
      const event = data?.find(e => e.id === id);
      return {
        data: event,
        // fetch succeeded, but we couldn't find a matching event
        error: !event && rest.isSuccess ? { status: 404, statusText: 'Event does not exist in provided query' } : error,
        ...rest,
      };
    },
  });
}

// unlike useEventParam this will return an error if the eventId is missing or invalid, rather than throwing

export function useEventFromRoute() {
  const { eventId } = useParams<{ eventId: string }>();
  return useEventFromQuery((eventId && +eventId) || 0);
}

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
