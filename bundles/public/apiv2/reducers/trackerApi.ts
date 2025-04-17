import { Draft } from 'immer';
import { DateTime, Duration } from 'luxon';
import { QueryArgFrom, QueryExtraOptions, ResultTypeFrom, TypedMutationOnQueryStarted } from '@reduxjs/toolkit/query';

import { PaginationInfo, ProcessingEvent } from '@public/apiv2/APITypes';
import { parseDuration, parseTime } from '@public/apiv2/helpers/luxon';
import { BidState, Donation, isOrdered, OrderedRun } from '@public/apiv2/Models';
import { processDonation } from '@public/apiv2/Processors';
import { addCallback, getSocketPath } from '@public/apiv2/reducers/sockets';
import { Dispatch } from '@public/apiv2/reducers/types';
import { compressInfinitePages } from '@public/apiv2/Util';
import { forceArray, MaybeArray, MaybePromise } from '@public/util/Types';

import {
  APIError,
  DonationQuery,
  EmptyBaseQuery,
  getLimit,
  PageOrInfinite,
  Tags,
  TrackerApiInfiniteQueryEndpoints,
  TrackerApiMutationEndpoints,
  TrackerApiQueryArgument,
  TrackerApiQueryData,
  TrackerApiQueryEndpoints,
  trackerBaseApi,
} from './trackerBaseApi';

// TODO: figure out if this is exported
type QueryFulfilledError =
  | {
      error: APIError;
      isUnhandledError: false;
      meta: unknown;
    }
  | {
      error: unknown;
      meta?: undefined;
      isUnhandledError: true;
    };

type TypedQueryOnCacheEntryAdded<ResultType = unknown, QueryArg = unknown> = NonNullable<
  QueryExtraOptions<string, ResultType, QueryArg, EmptyBaseQuery>['onCacheEntryAdded']
>;

type TrackerMutationOnQueryStarted<MK extends keyof TrackerApiMutationEndpoints> = TypedMutationOnQueryStarted<
  ResultTypeFrom<TrackerApiMutationEndpoints[MK]>,
  QueryArgFrom<TrackerApiMutationEndpoints[MK]>,
  EmptyBaseQuery
>;
type TrackerQueryOnCacheEntryAdded<K extends keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints> =
  TypedQueryOnCacheEntryAdded<TrackerApiQueryData<K>, TrackerApiQueryArgument<K>>;

function invalidateMeIfForbidden(dispatch: Dispatch, e: QueryFulfilledError) {
  if (!e.isUnhandledError && e.error.status === 403) {
    dispatch(trackerApi.util.invalidateTags(['me']));
  }
}

type Recipe<QueryData> = (draftData: QueryData | Draft<QueryData>) => void | QueryData | Draft<QueryData>;
type OptimisticRecipe<MutationArgs, QueryData, OriginalArgs = unknown> = (
  mutationArgs: MutationArgs,
  originalArgs: OriginalArgs,
) => Recipe<QueryData>;
type PessimisticRecipe<MutationArgs, QueryData, MutationData, OriginalArgs = unknown> = (
  mutationArgs: MutationArgs,
  data: MutationData,
  originalArgs: OriginalArgs,
) => Recipe<QueryData>;

/**
 * helper when a mutation wants to optimistically update the cache
 * @param {keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints} k - the cache key that will be updated
 * @param tags - optional list of tags to invalidate if the mutation fails
 * @return a function that takes an optimistic update, and an optional pessimistic update
 */

function optimisticMutation<const MK extends keyof TrackerApiMutationEndpoints>() {
  type MutationArgs = QueryArgFrom<TrackerApiMutationEndpoints[MK]>;
  type MutationData = ResultTypeFrom<TrackerApiMutationEndpoints[MK]>;
  return <const K extends keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints>(
    k: K,
    tags?: Tags,
  ) => {
    type OriginalArgs = TrackerApiQueryArgument<K>;
    type QueryData = TrackerApiQueryData<K>;
    return (
      optimistic: OptimisticRecipe<MutationArgs, QueryData, OriginalArgs>,
      pessimistic?: PessimisticRecipe<MutationArgs, QueryData, MutationData, OriginalArgs>,
    ): NonNullable<TypedMutationOnQueryStarted<MutationData, MutationArgs, EmptyBaseQuery>> => {
      return async (mutationArgs: MutationArgs, api) => {
        const undo = trackerApi.util.selectCachedArgsForQuery(api.getState(), k).map(originalArgs => {
          const recipe = optimistic(mutationArgs, originalArgs as OriginalArgs);
          // @ts-expect-error typing system doesn't like recipe
          return api.dispatch(trackerApi.util.updateQueryData(k, originalArgs, recipe)).undo;
        });

        try {
          const { data } = await api.queryFulfilled;
          if (typeof data !== 'string') {
            trackerApi.util.selectCachedArgsForQuery(api.getState(), k).forEach(originalArgs =>
              api.dispatch(
                trackerApi.util.updateQueryData(k, originalArgs, drafts => {
                  if (Array.isArray(drafts)) {
                    if (Array.isArray(data)) {
                      data.forEach(model => {
                        if (typeof model !== 'string') {
                          const i = drafts.findIndex(draft => draft.id === model.id && draft.type === model.type);
                          if (i !== -1) {
                            drafts[i] = { ...drafts[i], ...model };
                          }
                        }
                      });
                    } else if (data != null) {
                      const i = drafts.findIndex(draft => draft.id === data.id && draft.type === data.type);
                      if (i !== -1) {
                        drafts[i] = { ...drafts[i], ...data };
                      }
                    }
                  }
                  if (pessimistic) {
                    // @ts-expect-error typing system can't agree
                    const o: OriginalArgs = originalArgs;
                    // @ts-expect-error typing system can't agree
                    const d: QueryData | Draft<QueryData> = drafts;
                    pessimistic(mutationArgs, data, o)(d);
                  }
                }),
              ),
            );
          }
        } catch (e) {
          invalidateMeIfForbidden(api.dispatch, e as QueryFulfilledError);
          undo.forEach(u => u());
          api.dispatch(trackerApi.util.invalidateTags(forceArray(tags)));
        }
      };
    };
  };
}

// helper to wrap multiple optimistic mutations into one callback

function optimisticMutations<const MK extends keyof TrackerApiMutationEndpoints>(
  promises: ((...a: Parameters<NonNullable<TrackerMutationOnQueryStarted<MK>>>) => MaybePromise<void>)[],
): TrackerMutationOnQueryStarted<MK> {
  return async (args, api) => {
    await Promise.allSettled(promises.map(p => p(args, api)));
  };
}

type SimpleBidMutations = 'approveBid' | 'denyBid';

function updateAllBids(state: BidState): TrackerMutationOnQueryStarted<SimpleBidMutations> {
  return optimisticMutations([
    optimisticMutation<SimpleBidMutations>()('bidTree')(id => a => {
      const d = a.find(b => b.options?.some(o => o.id === id))?.options?.find(o => o.id === id);
      if (d) {
        d.state = state;
      }
    }),
    optimisticMutation<SimpleBidMutations>()('bids')(id => a => {
      const d = a.find(m => m.id === id);
      if (d) {
        d.state = state;
      }
    }),
  ]);
}

const patchRun = optimisticMutation<'patchRun'>()('runs')(mutationArgs => runs => {
  const draftIndex = runs.findIndex(r => r.id === mutationArgs.id);
  if (draftIndex !== -1) {
    const run = runs[draftIndex];
    const { run_time, setup_time, anchor_time, order, event, starttime } = run;
    const old_start_time = starttime;
    const new_anchor_time = parseTime(mutationArgs.anchor_time !== undefined ? mutationArgs.anchor_time : anchor_time);
    const new_run_time = parseDuration(mutationArgs.run_time ?? run_time);
    const new_setup_time = parseDuration(mutationArgs.setup_time ?? setup_time);

    runs[draftIndex] = {
      ...run,
      starttime: parseTime(mutationArgs.anchor_time ?? starttime),
      anchor_time: new_anchor_time,
      run_time: new_run_time,
      setup_time: new_setup_time,
    };

    // positive: push stuff into the future
    let time_diff = new_run_time.minus(run_time).plus(new_setup_time).minus(setup_time);

    if (new_anchor_time && old_start_time) {
      time_diff = time_diff.plus(new_anchor_time.diff(old_start_time));
    }

    if (time_diff.toMillis() === 0) {
      return;
    }

    if (order != null) {
      let foundAnchor = false;
      // FIXME: filter should be making these OrderedRun? something to do with immer maybe?
      (
        runs.filter((r): r is OrderedRun => r.order != null && r.event === event && r.order > order) as OrderedRun[]
      ).forEach((r, i, ri) => {
        if (foundAnchor) {
          return;
        }
        r.starttime = r.starttime.plus(time_diff);
        const a = ri.at(i + 1)?.anchor_time;
        if (a) {
          foundAnchor = true;
          r.setup_time = a.diff(r.starttime).minus(r.run_time);
          if (r.setup_time.toMillis() < 0) {
            // will get caught by the API and thrown back
            r.setup_time = Duration.fromMillis(0);
          }
        }
        r.endtime = r.starttime.plus(r.run_time.plus(r.setup_time));
      });
    }
  }
});

const moveRun = optimisticMutation<'moveRun'>()('runs')(mutationArgs => runs => {
  const d = runs.find(r => r.id === mutationArgs.id);
  if (d == null) {
    return;
  }
  let diff: -1 | 1 | 0 = 0;
  // FIXME: filter should be making these OrderedRun? something to do with immer maybe?
  const ordered = runs.filter(isOrdered) as OrderedRun[];
  let o: OrderedRun | undefined;
  let first: number;
  let last: number | null = null;
  if ('order' in mutationArgs) {
    const order = mutationArgs.order === 'last' ? (ordered.at(-1)?.order ?? 0) + 1 : mutationArgs.order;
    if (order == null) {
      if (d.order != null) {
        diff = -1;
        o = ordered.find(r => r.order > d.order!);
        if (o) {
          first = o.order;
        }
      }
    } else if (d.order) {
      first = Math.min(d.order, order);
      last = Math.max(d.order, order);
    } else {
      first = order;
    }
    if (d.order === order) {
      return;
    }
    d.order = order;
  } else if ('before' in mutationArgs || 'after' in mutationArgs) {
    let target: number;
    if ('before' in mutationArgs) {
      o = ordered.find(r => r.id === mutationArgs.before);
      if (o) {
        target = o.order;
      } else {
        throw new Error('invalid target');
      }
    } else {
      o = ordered.find(r => r.id === mutationArgs.after);
      if (o) {
        target = o.order + 1;
      } else {
        throw new Error('invalid target');
      }
    }
    if (d.order) {
      first = Math.min(target, d.order);
      last = Math.max(target, d.order);
      diff = d.order < target ? -1 : 1;
    } else {
      first = target;
      diff = 1;
    }
    if (d.order === target) {
      return;
    }
    d.order = target;
  } else {
    throw new Error('missing argument');
  }
  const movingRuns = ordered.filter(r => r.order >= first && (last == null || r.order < last));
  movingRuns.forEach(m => {
    if (m.order) {
      m.order = m.order + diff;
    }
  });
});

export type DonationState = 'unprocessed' | 'flagged' | 'unread' | 'done';

function getDonationStateFromReadState(donation: Donation, defaultState: DonationState): DonationState {
  switch (donation.readstate) {
    case 'READY':
      return 'unread';
    case 'FLAGGED':
      return 'flagged';
    case 'READ':
    case 'IGNORED':
      return 'done';
    default:
      return defaultState;
  }
}

function getDonationState(donation: Donation): DonationState {
  switch (donation.commentstate) {
    case 'APPROVED':
      return getDonationStateFromReadState(donation, 'done');
    case 'ABSENT':
    case 'PENDING':
      return getDonationStateFromReadState(donation, 'unprocessed');
    // FLAGGED does not get used on commentstates (never assigned in code)
    case 'FLAGGED':
    case 'DENIED':
    default:
      return 'done';
  }
}

function isNullOrEqual<T>(o: T | null, n: T) {
  return o == null || o === n;
}

function isNullOrEqualOrContains<T>(o: MaybeArray<T> | null, n: T) {
  return Array.isArray(o) ? o.includes(n) : isNullOrEqual(o, n);
}

/**
 * searches the list of provided pages for a slot for the donation, assuming that each page is sorted in descending
 * order, if we're on the final page and this donation is older than all of them, we can place it at the end
 */

function findDonationPage(pages: PaginationInfo<Donation>[], newDonation: Donation): Donation[] {
  let pageIndex = pages.findIndex((p, i, pages) => {
    // pages are sorted in descending order
    const newest = p.results.at(0);
    const oldest = p.results.at(-1);
    const lastItem = (p.previous ? pages.at(i - 1) : null)?.results.at(-1);
    // if we're on page 1, lastItem will always be null, so it belongs on this page if it's newer than the newest item, because it's the new first overall item
    // if we're on any other page, then check to see if the new item falls on the page boundary and would be the new first item for the current page
    if (
      (lastItem == null || lastItem.timereceived > newDonation.timereceived) &&
      (newest == null || newDonation.timereceived > newest.timereceived)
    ) {
      return true;
    } else if (oldest && newest) {
      // Interval.contains is open on the endpoint, so direct comparison is needed
      // either we're inclusively between the extremes of this page, or we're on the last page -and- we're all the way at
      // the end
      return (
        (newest.timereceived >= newDonation.timereceived && newDonation.timereceived >= oldest.timereceived) ||
        (i === pages.length - 1 && oldest.timereceived >= newDonation.timereceived)
      );
    } else {
      // blank page, so just assume it belongs here
      return true;
    }
  });
  if (pageIndex === -1) {
    pageIndex = pages.length;
    pages.push({ count: 0, previous: pages.length === 0 ? null : '__FAKE__VALUE__', next: null, results: [] });
  }
  return pages[pageIndex].results;
}

/**
 * helper for findIndex to find the insertion slot for the donation in the array, or -1 if it belongs at the end
 */

function findDonationByTime(newDonation: Donation): Parameters<Donation[]['findIndex']>[0] {
  return (d, i, a) => {
    const prev = i === 0 ? null : a[i - 1];
    return (
      (prev == null || prev.timereceived >= newDonation.timereceived) && newDonation.timereceived >= d.timereceived
    );
  };
}

function donationMatchesQuery(donation: Donation, query: DonationQuery | void) {
  if (query == null) {
    return true;
  }
  const { urlParams: { state, eventId } = {}, queryParams: { id, time_gte } = {} } = query;
  const newState = getDonationState(donation);
  return (
    isNullOrEqual(state, newState) &&
    isNullOrEqual(eventId, donation.event) &&
    isNullOrEqualOrContains(id, donation.id) &&
    (time_gte == null || donation.timereceived >= DateTime.fromISO(time_gte))
  );
}

function forcePages<T>(data: PageOrInfinite<T>): PaginationInfo<T>[] {
  if (Array.isArray(data)) {
    return [{ count: data.length, previous: null, next: null, results: data }];
  } else {
    return data.pages;
  }
}

function findPage<T>(data: PageOrInfinite<T>, matcher: (t: T) => boolean): T[] {
  return forcePages(data).find(({ results }) => results.find(matcher))?.results ?? [];
}

// TODO: will be useful for infinite queries, perhaps
function _findInPages<T>(data: PageOrInfinite<T>, matcher: (t: T) => boolean): T | undefined {
  return findPage(data, matcher).find(matcher);
}

export type TrackerSimpleDonationMutations =
  | 'approveDonationComment'
  | 'denyDonationComment'
  | 'flagDonation'
  | 'ignoreDonation'
  | 'pinDonation'
  | 'readDonation'
  | 'sendDonationToReader'
  | 'unpinDonation'
  | 'unprocessDonation';

function mutateDonation(fields: Partial<Pick<Donation, 'commentstate' | 'readstate' | 'pinned'>>) {
  return optimisticMutations<TrackerSimpleDonationMutations>([
    optimisticMutation<TrackerSimpleDonationMutations>()('donations')(
      (id, originalArgs) => donations => {
        const index = donations.findIndex(d => d.id === id);
        if (index !== -1) {
          donations[index] = {
            ...donations[index],
            ...fields,
          };
          // TODO: optimistically remove the donation when processed?
          // if (!donationMatchesQuery(results[index], originalArgs)) {
          //   results.splice(index, 1);
          // }
        }
      },
      (id, donation, originalArgs) => donations => {
        let index = donations.findIndex(d => d.id === id);
        if (donationMatchesQuery(donation, originalArgs)) {
          if (index === -1) {
            // doesn't exist yet, so find the right slot
            index = donations.findIndex(findDonationByTime(donation));
          }
          if (index === -1) {
            // didn't exist yet and belongs at the end
            donations.push(donation);
          } else {
            // might exist, so check to see if we're pointing at the old one and delete it if necessary
            donations.splice(index, donations[index].id === donation.id ? 1 : 0, donation);
          }
        } else if (index !== -1) {
          // exists and shouldn't
          donations.splice(index, 1);
        }
      },
    ),
  ]);
}

const updateDonationComment = optimisticMutation<'editDonationComment'>()('donations')(
  ({ comment, id }) =>
    donations => {
      const index = donations.findIndex(d => d.id === id);
      if (index !== -1) {
        donations[index] = {
          ...donations[index],
          modcomment: comment,
        };
      }
    },
);

type DonationGroupMutations = 'createDonationGroup' | 'deleteDonationGroup';

function updateDonationGroups(add: boolean): TrackerMutationOnQueryStarted<DonationGroupMutations> {
  const mutations = [
    optimisticMutation<DonationGroupMutations>()('donationGroups')(group => groups => {
      if (add && !groups.includes(group)) {
        return [...groups, group];
      } else if (!add && groups.includes(group)) {
        return groups.filter(g => g !== group);
      }
    }),
  ];

  function removeGroupFromDonations(group: string, donations: PageOrInfinite<Donation>) {
    forcePages(donations).forEach(({ results }) =>
      results.forEach(d => {
        if (d.groups?.includes(group)) {
          d.groups = d.groups.filter(g => g !== group);
        }
      }),
    );
  }

  if (!add) {
    mutations.push(
      optimisticMutation<DonationGroupMutations>()('donations')(
        group => donations => removeGroupFromDonations(group, donations),
      ),
      optimisticMutation<DonationGroupMutations>()('allDonations')(
        group => donations => removeGroupFromDonations(group, donations),
      ),
    );
  }

  return optimisticMutations(mutations);
}

type DonationGroupListMutations = 'addDonationToGroup' | 'removeDonationFromGroup';

function updateGroupsOnDonation(add: boolean): TrackerMutationOnQueryStarted<DonationGroupListMutations> {
  function sync(donations: PageOrInfinite<Donation>, id: number, group: string) {
    const donation = forcePages(donations)
      .find(({ results }) => results.find(d => d.id === id))
      ?.results.find(d => d.id === id);
    if (donation?.groups) {
      if (add && !donation.groups.includes(group)) {
        donation.groups.push(group);
      } else if (!add && donation.groups.includes(group)) {
        donation.groups = donation.groups.filter(g => g !== group);
      }
    }
  }
  return optimisticMutations([
    optimisticMutation<DonationGroupListMutations>()('donations')(
      ({ donationId, group }) =>
        donations =>
          sync(donations, donationId, group),
    ),
    optimisticMutation<DonationGroupListMutations>()('allDonations')(
      ({ donationId, group }) =>
        donations =>
          sync(donations, donationId, group),
    ),
  ]);
}

const socketDonation: TrackerQueryOnCacheEntryAdded<'donations' | 'allDonations'> = async (arg, api) => {
  if (!arg?.listen) {
    return;
  }
  const url = getSocketPath(api, 'processing');
  const remove = await addCallback(
    url,
    api.dispatch,
    async ev => {
      await api.cacheDataLoaded;

      const data = JSON.parse(ev.data) as ProcessingEvent;

      if ('donation' in data) {
        const newDonation = processDonation(data.donation);

        const limit = getLimit(api);

        api.updateCachedData(donations => {
          let page: Donation[];
          const matches = donationMatchesQuery(newDonation, arg);
          if (Array.isArray(donations)) {
            // regular query, so don't worry about the page size
            page = donations;
          } else if (matches) {
            // infinite query, and this donation belongs, so find the proper page for it
            page = findDonationPage(donations.pages, newDonation);
          } else {
            // infinite query, and this donation does not belong, so just search without adjusting
            // if it doesn't exist just return a blank fake page
            page = donations.pages.find(({ results }) => results.find(d => d.id === newDonation.id))?.results ?? [];
          }
          const currentIndex = page.findIndex(d => d.id === newDonation.id);
          if (currentIndex === -1) {
            if (matches) {
              // insert in the proper place, which might be the end
              const index = page.findIndex(findDonationByTime(newDonation));
              if (index === -1) {
                page.push(newDonation);
              } else {
                page.splice(index, 0, newDonation);
              }
            }
          } else {
            // replace or delete depending on if it belongs or not
            page.splice(currentIndex, 1, ...(matches ? [newDonation] : []));
          }
          if (!Array.isArray(donations)) {
            compressInfinitePages(donations.pages, limit);
          }
        });
      } else if (data.action === 'group_deleted') {
        api.updateCachedData(donations => {
          forcePages(donations).forEach(page => {
            page.results.forEach(donation => {
              if (donation.groups?.includes(data.group)) {
                donation.groups = donation.groups.filter(g => g !== data.group);
              }
            });
          });
        });
      }
    },
    ['donations'],
  );
  await api.cacheEntryRemoved;
  remove();
};

const socketEvents: TrackerQueryOnCacheEntryAdded<'events'> = async (arg, api) => {
  if (!arg?.listen || arg?.queryParams?.totals == null) {
    return;
  }
  const remove = await addCallback(
    getSocketPath(api, 'processing'),
    api.dispatch,
    async ev => {
      await api.cacheDataLoaded;

      const data = JSON.parse(ev.data) as ProcessingEvent;

      if (data.type !== 'donation_received') {
        return;
      }

      api.updateCachedData(events => {
        const event = events.find(e => e.id === data.donation.event);
        if (event) {
          event.donation_count = data.donation_count;
          event.amount = data.event_total;
        }
      });
    },
    ['events'],
  );
  await api.cacheEntryRemoved;
  remove();
};

const socketDonationGroups: TrackerQueryOnCacheEntryAdded<'donationGroups'> = async (arg, api) => {
  if (!arg?.listen) {
    return;
  }
  const url = getSocketPath(api, 'processing');
  const remove = await addCallback(url, api.dispatch, async ev => {
    await api.cacheDataLoaded;
    const event = JSON.parse(ev.data) as ProcessingEvent;
    if (event.type === 'processing_action') {
      switch (event.action) {
        case 'group_created':
          api.updateCachedData(groups => {
            if (!groups.includes(event.group)) {
              groups.push(event.group);
            }
          });
          break;
        case 'group_deleted':
          api.updateCachedData(groups => {
            const index = groups.findIndex(g => g === event.group);
            if (index !== -1) {
              groups.splice(index, 1);
            }
          });
          break;
      }
    }
  });
  await api.cacheEntryRemoved;
  remove();
};

// enhance the base api with additional lifecycle management

export const trackerApi = trackerBaseApi.enhanceEndpoints({
  endpoints: {
    events: {
      onCacheEntryAdded: socketEvents,
    },
    patchRun: {
      onQueryStarted: patchRun,
    },
    moveRun: {
      onQueryStarted: moveRun,
    },
    approveBid: {
      onQueryStarted: updateAllBids('OPENED'),
    },
    denyBid: {
      onQueryStarted: updateAllBids('DENIED'),
    },
    donationGroups: {
      onCacheEntryAdded: socketDonationGroups,
    },
    createDonationGroup: {
      onQueryStarted: updateDonationGroups(true),
    },
    deleteDonationGroup: {
      onQueryStarted: updateDonationGroups(false),
    },
    donations: {
      onCacheEntryAdded: socketDonation,
    },
    allDonations: {
      async onCacheEntryAdded(arg, api) {
        // TODO: https://github.com/reduxjs/redux-toolkit/issues/4901
        // should be fixed in 2.7.0
        if (api.updateCachedData == null) {
          api.updateCachedData = updateRecipe =>
            api.dispatch(trackerApi.util.updateQueryData('allDonations', arg, updateRecipe));
        }
        await socketDonation(arg, api);
      },
    },
    unprocessDonation: {
      onQueryStarted: mutateDonation({ commentstate: 'PENDING', readstate: 'PENDING' }),
    },
    approveDonationComment: {
      onQueryStarted: mutateDonation({ commentstate: 'APPROVED', readstate: 'IGNORED' }),
    },
    denyDonationComment: {
      onQueryStarted: mutateDonation({ commentstate: 'DENIED', readstate: 'IGNORED' }),
    },
    flagDonation: {
      onQueryStarted: mutateDonation({ commentstate: 'APPROVED', readstate: 'FLAGGED' }),
    },
    sendDonationToReader: {
      onQueryStarted: mutateDonation({ commentstate: 'APPROVED', readstate: 'READY' }),
    },
    pinDonation: {
      onQueryStarted: mutateDonation({ pinned: true }),
    },
    unpinDonation: {
      onQueryStarted: mutateDonation({ pinned: false }),
    },
    readDonation: {
      onQueryStarted: mutateDonation({ readstate: 'READ' }),
    },
    ignoreDonation: {
      onQueryStarted: mutateDonation({ readstate: 'IGNORED' }),
    },
    editDonationComment: {
      onQueryStarted: updateDonationComment,
    },
    addDonationToGroup: {
      onQueryStarted: updateGroupsOnDonation(true),
    },
    removeDonationFromGroup: {
      onQueryStarted: updateGroupsOnDonation(false),
    },
  },
});
