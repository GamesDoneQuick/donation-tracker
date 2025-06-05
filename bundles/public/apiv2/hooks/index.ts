import React from 'react';
import { produce } from 'immer';
import { ReactReduxContext, shallowEqual } from 'react-redux';
import { useParams } from 'react-router';
import { skipToken } from '@reduxjs/toolkit/query';

import { useConstants } from '@common/Constants';
import { Permission } from '@common/Permissions';
import { Me, PaginationInfo } from '@public/apiv2/APITypes';
import {
  compareDonation,
  compareRun,
  Donation,
  Event,
  Model,
  OrderedRun,
  Run,
  UnorderedRun,
} from '@public/apiv2/Models';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { DonationState, trackerApi } from '@public/apiv2/reducers/trackerApi';
import { useAppDispatch, useAppSelector } from '@public/apiv2/Store';
import { MaybeArray } from '@public/util/Types';

import { useDonationGroup } from '@processing/modules/donation-groups/DonationGroupsStore';

// TODO: wrap the queries that can return different types depending on parameters
// events, runs, donations

export const {
  // me
  useMeQuery,
  useLazyMeQuery,
  // events
  useEventsQuery,
  useLazyEventsQuery,
  // runs
  useRunsQuery,
  useLazyRunsQuery,
  usePatchRunMutation,
  useMoveRunMutation,
  // milestones
  useMilestonesQuery,
  useLazyMilestonesQuery,
  // bids
  useBidsQuery,
  useLazyBidsQuery,
  useBidTreeQuery,
  useLazyBidTreeQuery,
  useApproveBidMutation,
  useDenyBidMutation,
  // prizes
  usePrizesQuery,
  useLazyPrizesQuery,
  // interviews
  useInterviewsQuery,
  useLazyInterviewsQuery,
  // ads
  useAdsQuery,
  useLazyAdsQuery,
  // donation groups
  useDonationGroupsQuery,
  useLazyDonationGroupsQuery,
  useCreateDonationGroupMutation,
  useDeleteDonationGroupMutation,
  // donations
  useDonationsQuery,
  useLazyDonationsQuery,
  useAllDonationsInfiniteQuery,
  useUnprocessDonationMutation,
  useApproveDonationCommentMutation,
  useDenyDonationCommentMutation,
  useFlagDonationMutation,
  useSendDonationToReaderMutation,
  usePinDonationMutation,
  useUnpinDonationMutation,
  useReadDonationMutation,
  useIgnoreDonationMutation,
  useEditDonationCommentMutation,
  useAddDonationToGroupMutation,
  useRemoveDonationFromGroupMutation,
} = trackerApi;

function idOrShort(id: number | string) {
  // try to coerce it to a number
  if (id && !Number.isNaN(+id)) {
    return +id;
  } else {
    return id; // assume it's a short id
  }
}

export type UseDonationMutation = typeof useApproveDonationCommentMutation;
export type UseDonationMutationResult = ReturnType<UseDonationMutation>;

export function useInfinitePages<T extends Model>(pages: Array<PaginationInfo<T>> | undefined) {
  return React.useMemo(() => (pages ?? []).reduce<T[]>((models, page) => [...models, ...page.results], []), [pages]);
}

export function useEventParam() {
  const { eventId } = useParams<{ eventId: string }>();
  if (!eventId || !+eventId) {
    throw new Error('could not find a valid numeric event id in url');
  }
  return +eventId;
}

export const allEvents = Symbol('all_events');

export function useEventAllParam(): number | typeof allEvents {
  const { eventId } = useParams<{ eventId: string }>();
  if (eventId === '@all') {
    return allEvents;
  }
  if (!eventId || !+eventId) {
    throw new Error('could not find a valid numeric event id in url');
  }
  return +eventId;
}

export function useEventFromQuery(
  id: number | string | typeof skipToken,
  params?: Parameters<typeof useEventsQuery>[0],
) {
  if (id !== skipToken) {
    id = idOrShort(id);
  }
  const finder = typeof id === 'number' ? (e: Event) => e.id === id : (e: Event) => e.short === id;
  return useEventsQuery(params, {
    skip: id === skipToken,
    selectFromResult: ({ data, error, ...rest }) => {
      const event = data?.find(finder);
      return {
        data: event,
        id: typeof id === 'number' ? id : event?.id,
        path: id === skipToken ? '@all' : id,
        // fetch succeeded, but we couldn't find a matching event
        error: !event && rest.isSuccess ? { status: 404, statusText: 'Event does not exist in provided query' } : error,
        ...rest,
      };
    },
  });
}

// unlike useEventParam this will return an error if the eventId is missing or invalid, rather than throwing, and will also accept string matches against `short`

export function useEventFromRoute(params?: Parameters<typeof useEventsQuery>[0]) {
  const { eventId = '' } = useParams<{ eventId: string }>();
  return useEventFromQuery(eventId, params);
}

// TODO: helpers for the event-reliant queries to make them easier to use when eventId might be `id` -or- `short`

function queryIdMatches(
  id: number,
  result: {
    originalArgs?: { queryParams?: { id?: MaybeArray<number> } } | void;
  },
) {
  return result.originalArgs?.queryParams?.id === id;
}

export function useDonation(id: number): Omit<ReturnType<typeof useDonationsQuery>, 'data'> & { data?: Donation } {
  const redux = React.useContext(ReactReduxContext);
  const dispatch = useAppDispatch();
  const [args, setArgs] = React.useState(
    redux?.store ? trackerApi.util.selectCachedArgsForQuery(redux.store.getState(), 'donations') : [],
  );
  React.useEffect(
    () =>
      redux?.store.subscribe(() => {
        const args = trackerApi.util.selectCachedArgsForQuery(redux.store.getState(), 'donations');
        setArgs(oldArgs =>
          produce(oldArgs, draft => {
            args.forEach((a, n) => {
              draft[n] = a;
            });
            if (draft.length > args.length) {
              draft.splice(args.length);
            }
          }),
        );
      }),
    [redux],
  );
  const selectors = React.useMemo(() => (args ?? []).map(a => trackerApi.endpoints.donations.select(a)), [args]);
  const allResults = useAppSelector(state => selectors.map(s => s(state)), shallowEqual);
  const queryResult = allResults.find(r => r.data?.find(d => d.id === id));
  const [lazyFetch, lazyResult] = useLazyDonationsQuery();
  // the args from the lazyFetch won't show up for at least one update cycle because of the timing
  const data = queryResult?.data || lazyResult.data;
  // only show the lazyResult error if the donation was never found
  let error = queryResult ? undefined : lazyResult.error;
  const donation = data?.find(d => d.id === id);
  const refetch = React.useCallback(() => {
    if (queryResult) {
      dispatch(trackerApi.endpoints.donations.initiate(queryResult.originalArgs)).refetch();
    } else {
      lazyFetch({ queryParams: { id } });
    }
  }, [dispatch, lazyFetch, id, queryResult]);
  if (donation == null && lazyResult.data != null && queryIdMatches(id, lazyResult)) {
    // still couldn't find it even after specifically requesting it
    error = {
      status: 404,
      statusText: 'Not found',
      message: 'Donation either does not exist or you do not have permission to view it.',
    };
  }
  React.useEffect(() => {
    // no query results exist that include the id, so ensure there's a query in flight
    if (donation == null && !queryIdMatches(id, lazyResult)) {
      lazyFetch({ queryParams: { id } });
    }
  }, [donation, lazyFetch, id, lazyResult]);
  return { ...(queryResult ?? lazyResult), refetch, data: donation, error };
}

export type DonationPredicate = (donation: Donation) => boolean;

function sortDonations(donations: Donation[]) {
  // show oldest first
  return donations.toSorted((a, b) => -compareDonation(a, b));
}

export function useFilteredDonations(donationState: DonationState, groupIdOrPredicate: string | DonationPredicate) {
  const status = useDonationsInState(donationState);
  const group = useDonationGroup(typeof groupIdOrPredicate === 'string' ? groupIdOrPredicate : '');
  return React.useMemo(() => {
    const { data, ...rest } = status;
    if (data) {
      if (typeof groupIdOrPredicate === 'function') {
        return {
          ...rest,
          data: data.filter(groupIdOrPredicate),
        };
      } else if (group) {
        return {
          ...rest,
          data: [
            ...group.order.map(i => data.find(d => d.id === i)).filter((d): d is Donation => d != null),
            ...data.filter(d => !group.order.includes(d.id) && d.groups?.includes(groupIdOrPredicate)),
          ],
        };
      }
      // if we get here it means the group id is somehow invalid
    }
    return {
      ...rest,
      data: data ?? [],
    };
  }, [groupIdOrPredicate, status, group]);
}

export function useDonationsInState(donationState: DonationState, filter?: DonationPredicate) {
  const eventId = useEventParam();
  // TODO: do we ever NOT want to listen?
  const status = useDonationsQuery({ urlParams: { eventId, state: donationState }, listen: true });

  return React.useMemo(() => {
    const { data, ...rest } = status;
    return {
      ...rest,
      data: data && sortDonations(filter ? data.filter(filter) : data),
    };
  }, [filter, status]);
}

export function useSplitRuns(runs?: Run[]): [OrderedRun[], UnorderedRun[]] {
  const sorted = React.useMemo(() => (runs ?? []).toSorted(compareRun), [runs]);
  const orderedRuns = React.useMemo(() => sorted.filter((r): r is OrderedRun => r.order != null), [sorted]);
  const unorderedRuns = React.useMemo(() => sorted.filter((r): r is UnorderedRun => r.order == null), [sorted]);

  return [orderedRuns, unorderedRuns];
}

function hasPermission(user: Me, permission: Permission) {
  return user.staff && (user.superuser || user.permissions.includes(permission));
}

export function usePermission(...permissions: Permission[]) {
  const { data } = useMeQuery();

  return data != null && permissions.every(p => hasPermission(data, p));
}

export function useArchivedPermission(event_or_perm?: Event | Permission, ...permissions: Permission[]) {
  const otherPermissions = usePermission(
    ...[...(typeof event_or_perm === 'string' ? [event_or_perm] : []), ...permissions],
  );
  let { data: event } = useEventFromRoute();
  if (typeof event_or_perm !== 'string' && event_or_perm != null) {
    if (event?.id != null && event.id !== event_or_perm.id) {
      throw new Error('got different event from route and from parameter');
    }
    event = event_or_perm;
  }
  return event?.archived === false && otherPermissions;
}

export function useCSRFToken() {
  return document.querySelector<HTMLInputElement>('input[name=csrfmiddlewaretoken]')?.value ?? '';
}

export function useTrackerInit() {
  const dispatch = useAppDispatch();
  const { APIV2_ROOT, PAGINATION_LIMIT } = useConstants();
  const csrfToken = useCSRFToken();
  React.useLayoutEffect(() => {
    dispatch(setRoot({ root: APIV2_ROOT, limit: PAGINATION_LIMIT, csrfToken }));
  }, [APIV2_ROOT, csrfToken, PAGINATION_LIMIT, dispatch]);
}
