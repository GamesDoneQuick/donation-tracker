import React from 'react';
import { useParams } from 'react-router';

import { OrderedRun, Run, UnorderedRun } from '@public/apiv2/Models';
import { useEventsQuery } from '@public/apiv2/reducers/trackerApi';

export function useEventParam() {
  const { eventId } = useParams<{ eventId: string }>();
  if (!eventId || !+eventId) {
    throw new Error('insanity');
  }
  return +eventId;
}

export function useEventFromQuery(id: number, params?: Parameters<typeof useEventsQuery>[0]) {
  return useEventsQuery(params, {
    selectFromResult: ({ data, error, ...rest }) => {
      const event = data?.find(e => e.id === id);
      return {
        event,
        error: !event && rest.isSuccess ? { status: 404, statusText: 'Event does not exist in provided query' } : error,
        ...rest,
      };
    },
  });
}

export function useRoutedEvent() {
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
