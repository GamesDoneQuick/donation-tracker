import { castDraft } from 'immer';
import { DateTime, Duration } from 'luxon';
import { QueryArgFrom, QueryExtraOptions, ResultTypeFrom, TypedMutationOnQueryStarted } from '@reduxjs/toolkit/query';

import { APIDonation, findBidInTree, FlatBid, PaginationInfo, ProcessingEvent, TreeBid } from '@public/apiv2/APITypes';
import { BidFeed } from '@public/apiv2/Endpoints';
import { parseDuration, parseTime } from '@public/apiv2/helpers/luxon';
import {
  BidState,
  compareDonation,
  Donation,
  DonationBid,
  isOrdered,
  OrderedRun,
  VALID_PARENT_STATES,
} from '@public/apiv2/Models';
import { processDonation } from '@public/apiv2/Processors';
import { addCallback, getSocketPath } from '@public/apiv2/reducers/sockets';
import { Dispatch } from '@public/apiv2/reducers/types';
import { compressInfinitePages } from '@public/apiv2/Util';
import { forceArray, MaybeArray, MaybeDrafted, MaybePromise } from '@public/util/Types';

import {
  APIError,
  BidQuery,
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
      meta: never;
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

type Recipe<QueryData> = (draftData: MaybeDrafted<QueryData>) => void | MaybeDrafted<QueryData>;
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
 * helper when a mutation wants to optimistically and/or pessimistically update the cache, if the request is successful
 *   it will merge the result from the server into the cache and call the pessimistic update, if the request fails it
 *   will roll back the optimistic update
 * @param {keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints} k - the cache key that will be updated
 * @param tags - optional list of tags to invalidate if the mutation fails
 * @param optimistic - takes the mutation arguments, and the original query arguments, and returns a function that takes
 *   the existing cache data and updates it before the request is sent; rolled back if the request fails
 * @param pessimistic - takes the mutation arguments, the original query arguments, and the result from the server, and
 *   returns a function that takes the existing cache data and updates it after the response is received; only called if
 *   the request was successful
 * @return a function that takes an optimistic update, and an optional pessimistic update
 */

function optimisticMutation<const MK extends keyof TrackerApiMutationEndpoints>() {
  type MutationArgs = QueryArgFrom<TrackerApiMutationEndpoints[MK]>;
  type MutationData = ResultTypeFrom<TrackerApiMutationEndpoints[MK]>;
  return <const K extends keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints>(
    k: K,
    tags?: Tags,
  ) => {
    type OriginalArgs = Exclude<TrackerApiQueryArgument<K>, unknown>;
    type QueryData = TrackerApiQueryData<K>;
    return (
      optimistic: OptimisticRecipe<MutationArgs, QueryData, OriginalArgs>,
      pessimistic?: PessimisticRecipe<MutationArgs, QueryData, MutationData, OriginalArgs>,
    ): NonNullable<TypedMutationOnQueryStarted<MutationData, MutationArgs, EmptyBaseQuery>> => {
      return async (mutationArgs: MutationArgs, api) => {
        const undo = trackerApi.util.selectCachedArgsForQuery(api.getState(), k).map(originalArgs => {
          // @ts-expect-error why does it think OriginalArgs can ever be 'unknown' here?
          const o: OriginalArgs = originalArgs;
          const recipe = optimistic(mutationArgs, o);
          // @ts-expect-error type system doesn't like recipe
          return api.dispatch(trackerApi.util.updateQueryData(k, o, recipe)).undo;
        });

        try {
          const { data } = await api.queryFulfilled;
          if (typeof data !== 'string') {
            trackerApi.util.selectCachedArgsForQuery(api.getState(), k).forEach(originalArgs => {
              // @ts-expect-error why does it think OriginalArgs can ever be 'unknown' here?
              const o: OriginalArgs = originalArgs;
              api.dispatch(
                trackerApi.util.updateQueryData(k, o, drafts => {
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
                    } else if (data != null && 'id' in data) {
                      const i = drafts.findIndex(draft => draft.id === data.id && draft.type === data.type);
                      if (i !== -1) {
                        drafts[i] = { ...drafts[i], ...data };
                      }
                    }
                  }
                }),
              );
            });
          }
          if (pessimistic) {
            trackerApi.util.selectCachedArgsForQuery(api.getState(), k).forEach(originalArgs => {
              // @ts-expect-error why does it think OriginalArgs can ever be 'unknown' here?
              const o: OriginalArgs = originalArgs;

              api.dispatch(
                trackerApi.util.updateQueryData(k, o, drafts => {
                  // @ts-expect-error typing system can't agree
                  const d: MaybeDrafted<QueryData> = drafts;
                  pessimistic(mutationArgs, data, o)(d);
                  if (d && 'pages' in d) {
                    compressInfinitePages(d, getLimit(api));
                  }
                }),
              );
            });
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

// helper to wrap multiple optimistic mutations that take the same arguments into one callback

function optimisticMutations<const MK extends keyof TrackerApiMutationEndpoints>(
  promises: Array<(...a: Parameters<NonNullable<TrackerMutationOnQueryStarted<MK>>>) => MaybePromise<void>>,
): TrackerMutationOnQueryStarted<MK> {
  return async (args, api) => {
    await Promise.allSettled(promises.map(p => p(args, api)));
  };
}

type SimpleBidMutations = 'approveBid' | 'denyBid';

function updateAllBids(state: BidState): TrackerMutationOnQueryStarted<SimpleBidMutations> {
  return optimisticMutations([
    optimisticMutation<SimpleBidMutations>()('bidTree')(id => bids => {
      const child = findBidInTree(bids, id);
      if (child) {
        child.state = state;
      }
    }),
    optimisticMutation<SimpleBidMutations>()('bids')(id => bids => {
      const child = bids.find(m => m.id === id);
      if (child) {
        child.state = state;
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

function isNullishOrEqual<T>(o: T | null | undefined, n: T) {
  return o == null || o === n;
}

function isNullishOrEqualOrContains<T>(o: MaybeArray<T> | null | undefined, n: T) {
  return Array.isArray(o) ? o.includes(n) : isNullishOrEqual(o, n);
}

/**
 * searches the list of provided pages for a slot for the model to be upserted, using the provided comparison function
 * if no page is found, it means the last page was full and the item belongs past the end, so this can insert a new
 * blank page at the end if insert is true
 * for convenience also accepts a bare array (from non-infinite endpoints), which will just be returned as-is
 * @template T
 * @param {PageOrInfinite<T>} data - either an array of models or InfiniteData
 * @param {T} newModel - the new model instance to be upserted
 * @param {Function} compareFn - a sort() compatible comparison function
 * @param {boolean} [insert=true] - whether to insert a new blank page at the end if necessary
 * @returns {T[]} - the array of models from the page where the model should be upserted, will be blank if either:
 *  - the last page was full and the provided model belongs past the end
 *  - no pages currently exist
 * Note that if either of these was true and insert was false, it will return a frozen blank array to help you
 * catch programming mistakes
 */

function findModelPage<T>(data: PageOrInfinite<T>, newModel: T, compareFn: (a: T, b: T) => number, insert = true): T[] {
  if (Array.isArray(data)) {
    return data;
  }
  const { pages } = data;
  let pageIndex = pages.findIndex((page, i, pages) => {
    const prevPageLastItem = (page.previous ? pages.at(i - 1) : null)?.results.at(-1);
    const first = page.results.at(0);
    const last = page.results.at(-1);
    // if we're on page 1, prevPageLastItem will always be null, so it belongs on this page if it's before the first item, because it's the new first overall item
    // if we're on any other page, then check to see if the new item falls on the page boundary and would be the new first item for the current page
    if (
      (prevPageLastItem == null || compareFn(prevPageLastItem, newModel) < 0) &&
      (first == null || compareFn(newModel, first) < 0)
    ) {
      return true;
    } else if (last && first) {
      // either we're inclusively between the extremes of this page, or we're on the last page -and- we're all the way at
      // the end
      return (
        (compareFn(first, newModel) <= 0 && compareFn(newModel, last) <= 0) ||
        (i === pages.length - 1 && compareFn(last, newModel) <= 0)
      );
    } else {
      // blank page, so just assume it belongs here
      return true;
    }
  });
  // couldn't find a page, so insert a new blank one at the end if we can
  if (pageIndex === -1) {
    if (!insert) {
      // @ts-expect-error return a frozen array so we don't accidentally modify it, because this is almost certainly a
      // programming mistake
      return Object.freeze([]);
    }
    pageIndex = pages.length;
    pages.push({ count: 0, previous: pages.length === 0 ? null : '__FAKE__VALUE__', next: null, results: [] });
  }
  return pages[pageIndex].results;
}

/**
 * helper for findIndex to find the upsertion slot for the model in the array, or -1 if it belongs at the end
 */

function findSlot<T>(newModel: T, compareFn: (a: T, b: T) => number): Parameters<T[]['findIndex']>[0] {
  return (d, i, a) => {
    const prev = i === 0 ? null : a[i - 1];
    return (prev == null || compareFn(prev, newModel) < 0) && compareFn(newModel, d) <= 0;
  };
}

function donationMatchesQuery(donation: Donation, query: DonationQuery | void) {
  if (query == null) {
    return true;
  }
  const { urlParams, queryParams: { id, time_gte } = {} } = query;
  let state;
  let eventId;
  if (typeof urlParams === 'number') {
    eventId = urlParams;
  } else {
    eventId = urlParams?.eventId;
    state = urlParams?.state;
  }
  const newState = getDonationState(donation);
  return (
    isNullishOrEqual(state, newState) &&
    isNullishOrEqual(eventId, donation.event) &&
    isNullishOrEqualOrContains(id, donation.id) &&
    (time_gte == null || donation.timereceived >= DateTime.fromISO(time_gte))
  );
}

function belongsToFeed(state: BidState, feed: BidFeed = 'public') {
  if (feed === 'all') {
    return true;
  }
  switch (feed) {
    case 'pending':
      return state === 'PENDING';
    case 'closed':
      return state === 'CLOSED';
    case 'public':
    case 'current':
      return state === 'CLOSED' || state === 'OPENED';
    case 'open':
      return state === 'OPENED';
  }
}

function donationBidMatchesQuery(donation: Donation | APIDonation, bid: DonationBid, query: BidQuery = {}) {
  const { urlParams } = query;

  let feed;
  let eventId;

  if (typeof urlParams === 'number') {
    eventId = urlParams;
  } else {
    eventId = urlParams?.eventId;
    feed = urlParams?.feed;
  }

  return isNullishOrEqual(eventId, donation.event) && belongsToFeed(bid.bid_state, feed);
}

function forcePages<T>(data: PageOrInfinite<T>): Array<PaginationInfo<T>> {
  if (Array.isArray(data)) {
    return [{ count: data.length, previous: null, next: null, results: data }];
  } else {
    return data.pages;
  }
}

function findPage<T>(data: PageOrInfinite<T>, matcher: (t: T) => boolean): T[] {
  return forcePages(data).find(({ results }) => results.find(matcher))?.results ?? [];
}

function findPageAndIndex<T>(data: PageOrInfinite<T>, matcher: (t: T) => boolean): [T[], number] {
  const page = findPage(data, matcher);
  return [page, page.findIndex(matcher)];
}

function findInPages<T>(data: PageOrInfinite<T>, matcher: (t: T) => boolean): T | undefined {
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

function mutateDonation(
  fields: Partial<Pick<Donation, 'commentstate' | 'readstate' | 'pinned'>>,
): TrackerMutationOnQueryStarted<TrackerSimpleDonationMutations> {
  function optimistic(id: number, originalArgs: DonationQuery | void) {
    return (donations: PageOrInfinite<Donation>) => {
      const [page, index] = findPageAndIndex(donations, d => d.id === id);
      if (index !== -1) {
        page[index] = {
          ...page[index],
          ...fields,
        };
        // TODO: optimistically remove the donation when processed?
        // if (!donationMatchesQuery(page[index], originalArgs)) {
        //   page.splice(index, 1);
        // }
      }
    };
  }
  function pessimistic(id: number, donation: Donation, originalArgs: DonationQuery | void) {
    return (donations: PageOrInfinite<Donation>) => {
      let [page, index] = findPageAndIndex(donations, d => d.id === id);
      if (donationMatchesQuery(donation, originalArgs)) {
        if (index === -1) {
          // doesn't exist yet, so find the right slot
          index = page.findIndex(findSlot(donation, compareDonation));
        }
        if (index === -1) {
          // didn't exist yet and belongs at the end
          page.push(donation);
        } else {
          // might exist, so check to see if we're pointing at the old one and delete it if necessary
          page.splice(index, page[index].id === donation.id ? 1 : 0, donation);
        }
      } else if (index !== -1) {
        // exists and shouldn't
        page.splice(index, 1);
      }
    };
  }

  return optimisticMutations<TrackerSimpleDonationMutations>([
    optimisticMutation<TrackerSimpleDonationMutations>()('donations')(optimistic, pessimistic),
    optimisticMutation<TrackerSimpleDonationMutations>()('allDonations')(optimistic, pessimistic),
  ]);
}

function updateDonationComment(): TrackerMutationOnQueryStarted<'editDonationComment'> {
  function update({ comment, id }: { comment: string; id: number }) {
    return (donations: PageOrInfinite<Donation>) => {
      const donation = findInPages(donations, d => d.id === id);
      if (donation) {
        donation.modcomment = comment;
      }
    };
  }
  return optimisticMutations<'editDonationComment'>([
    optimisticMutation<'editDonationComment'>()('donations')(update),
    optimisticMutation<'editDonationComment'>()('allDonations')(update),
  ]);
}

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

  function removeGroupFromDonations(group: string) {
    return (donations: PageOrInfinite<Donation>) => {
      forcePages(donations).forEach(({ results }) =>
        results.forEach(d => {
          if (d.groups?.includes(group)) {
            d.groups = d.groups.filter(g => g !== group);
          }
        }),
      );
    };
  }

  if (!add) {
    mutations.push(
      optimisticMutation<DonationGroupMutations>()('donations')(removeGroupFromDonations),
      optimisticMutation<DonationGroupMutations>()('allDonations')(removeGroupFromDonations),
    );
  }

  return optimisticMutations(mutations);
}

type DonationGroupListMutations = 'addDonationToGroup' | 'removeDonationFromGroup';

function updateGroupsOnDonation(add: boolean): TrackerMutationOnQueryStarted<DonationGroupListMutations> {
  function sync({ donationId, group }: { donationId: number; group: string }) {
    return (donations: PageOrInfinite<Donation>) => {
      const donation = findInPages(donations, d => d.id === donationId);
      if (donation?.groups) {
        if (add && !donation.groups.includes(group)) {
          donation.groups.push(group);
        } else if (!add && donation.groups.includes(group)) {
          donation.groups = donation.groups.filter(g => g !== group);
        }
      }
    };
  }

  return optimisticMutations([
    optimisticMutation<DonationGroupListMutations>()('donations')(sync),
    optimisticMutation<DonationGroupListMutations>()('allDonations')(sync),
  ]);
}

const socketDonation: TrackerQueryOnCacheEntryAdded<'donations' | 'allDonations'> = async (args, api) => {
  if (!args?.listen) {
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
          const matches = donationMatchesQuery(newDonation, args);
          const page = findModelPage(donations, newDonation, compareDonation, matches);
          const currentIndex = page.findIndex(d => d.id === newDonation.id);
          if (currentIndex === -1) {
            if (matches) {
              // insert in the proper place, which might be the end
              const index = page.findIndex(findSlot(newDonation, compareDonation));
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
          compressInfinitePages(donations, limit);
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

const socketEvents: TrackerQueryOnCacheEntryAdded<'events'> = async (args, api) => {
  if (!args?.listen || args?.queryParams?.totals == null) {
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

function isFlat(data: TreeBid[] | FlatBid[]): data is FlatBid[] {
  return data[0] && 'level' in data[0];
}

function isTree(data: TreeBid[] | FlatBid[]): data is TreeBid[] {
  return data[0] && !('level' in data[0]);
}

const socketBids: TrackerQueryOnCacheEntryAdded<'bids' | 'bidTree'> = async (args, api) => {
  if (!args?.listen) {
    return;
  }

  const url = getSocketPath(api, 'processing');
  const remove = await addCallback(url, api.dispatch, async ev => {
    await api.cacheDataLoaded;
    const event = JSON.parse(ev.data) as ProcessingEvent;
    if ('donation' in event && event.donation.bids.length > 0) {
      api.updateCachedData(data => {
        const endpoint = api.getCacheEntry().endpointName;
        const flat = endpoint === 'bids' && isFlat(data) ? data : null;
        const tree = endpoint === 'bidTree' && isTree(data) ? data : null;
        // it's possible both are null here if either the state is empty or corrupt, so the rest of this should be
        // robust enough to handle that
        event.donation.bids.forEach(incoming => {
          const bid = castDraft(flat ? flat.find(b => b.id === incoming.bid) : findBidInTree(tree ?? [], incoming.bid));
          const matches = donationBidMatchesQuery(event.donation, incoming, args);
          if (bid && matches) {
            const parent = castDraft(
              'parent' in bid
                ? flat?.find(b => b.id === bid.parent)
                : tree?.find(b => b.options?.some(b => b.id === bid.id)),
            );
            if ('parent' in bid && bid.parent != null && parent == null) {
              // this is a pathological case where the incoming bid is already in the tree, but somehow the parent is
              // not, and is probably indicative of a bug
              api.dispatch(trackerBaseApi.util.invalidateTags(['bids']));
            } else {
              bid.state = incoming.bid_state;
              bid.count = incoming.bid_count;
              bid.total = incoming.bid_total;

              if ('goal' in bid && bid.goal != null) {
                let chain_steps: Array<{ total: number; goal: number }> = [];
                if (flat && 'level' in bid && bid.chain) {
                  let next: FlatBid | undefined = bid;
                  while ((next = flat.find(c => c.parent === next?.id))) {
                    // @ts-expect-error next.goal is never null here in practice
                    chain_steps.push(next);
                  }
                } else if ('chain_steps' in bid && bid.chain_steps != null) {
                  chain_steps = bid.chain_steps;
                }
                let remaining = bid.total - bid.goal;
                chain_steps.forEach(step => {
                  step.total = Math.max(0, remaining);
                  remaining -= step.goal;
                });
              }

              if (parent != null) {
                const children = (
                  ('options' in parent ? parent.options : flat?.filter(b => b.parent === parent.id)) ?? []
                )
                  .map(({ state, count, total }) => ({ state, count, total }))
                  // the API does not include pending/denied children in the totals
                  .filter(({ state }) => VALID_PARENT_STATES.includes(state))
                  .reduce((t, c) => ({ count: t.count + c.count, total: t.total + c.total }), { count: 0, total: 0 });
                parent.count = children.count;
                parent.total = children.total;
              }
            }
          } else if ((bid != null) !== matches) {
            // either it matches and we couldn't find it (e.g. a new option was approved),
            // or it existed and no longer matches (e.g. listening to the open feed, but the bid is now closed)
            // TODO: this is a bit of a sledgehammer but it works enough for now since it's rare
            // and the donation payload doesn't contain the necessary information
            // probably best to add a new event type to the socket when bid state changes
            api.dispatch(trackerBaseApi.util.invalidateTags(['bids']));
          }
        });
      });
    }
  });
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
    bids: {
      onCacheEntryAdded: socketBids,
    },
    bidTree: {
      onCacheEntryAdded: socketBids,
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
      onCacheEntryAdded: socketDonation,
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
      onQueryStarted: updateDonationComment(),
    },
    addDonationToGroup: {
      onQueryStarted: updateGroupsOnDonation(true),
    },
    removeDonationFromGroup: {
      onQueryStarted: updateGroupsOnDonation(false),
    },
  },
});
