import type { AxiosError, AxiosRequestConfig, Method } from 'axios';
import { DateTime, Duration } from 'luxon';
import { useDispatch } from 'react-redux';
import SturdyWebSocket from 'sturdy-websocket';
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import {
  BaseQueryApi,
  BaseQueryError,
  BaseQueryMeta,
  InfiniteData,
  QueryExtraOptions,
  QueryReturnValue,
  TagDescription,
  TypedMutationOnQueryStarted,
} from '@reduxjs/toolkit/query';
import { createApi } from '@reduxjs/toolkit/query/react';

import {
  APIAd,
  APIInterview,
  APIModel,
  APIRun,
  BidGet,
  DonationGet,
  EventGet,
  FlatBid,
  InterviewGet,
  Me,
  MilestoneGet,
  PaginationInfo,
  PrizeGet,
  ProcessingEvent,
  RunGet,
  RunPatch,
  TreeBid,
} from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import { parseDuration, parseTime } from '@public/apiv2/helpers/luxon';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import {
  Ad,
  BidState,
  Donation,
  Event,
  Interview,
  isOrdered,
  Milestone,
  OrderedRun,
  Prize,
  Run,
} from '@public/apiv2/Models';
import {
  processDonation,
  processEvent,
  processInterstitial,
  processMilestone,
  processPrize,
  processRun,
} from '@public/apiv2/Processors';
import { compressInfinitePages } from '@public/apiv2/Util';
import { Flatten, forceArray, MaybeArray, MaybePromise } from '@public/util/Types';

type Dispatch = ReturnType<typeof useDispatch>;

export interface APIError {
  status?: number;
  statusText?: string;
  data?: any;
}

async function emptyRequest() {
  return axiosRequest<void>(undefined, {});
}

type EmptyBaseQuery = typeof emptyRequest;

async function axiosRequest<T>(
  baseURL: string | undefined,
  { url, method, data, params, headers }: Omit<AxiosRequestConfig, 'baseURL'>,
): Promise<QueryReturnValue<T, APIError, Empty>> {
  if (!baseURL) {
    return {
      error: {
        status: 400,
        statusText: 'Bad Request',
        data: 'No API root set',
      },
    };
  }
  try {
    return {
      data: (
        await HTTPUtils.request<T>({
          url,
          baseURL,
          method,
          data,
          params,
          headers,
          paramsSerializer: { indexes: null },
        })
      ).data,
    };
  } catch (axiosError) {
    const err = axiosError as AxiosError;
    return {
      error: {
        status: err.response?.status,
        data: err.response?.data || err.message,
      },
    };
  }
}

type MaybeEmpty<T> = T extends void ? object : T;
type MaybeObject<T> = T extends object ? T : never;
type WithID<T> = { id: number } & T;
type WithEvent<T = void> = MaybeEmpty<T> & { eventId?: number };
type WithListen<T = void> = MaybeEmpty<T> & { listen?: boolean };

interface PageParams {
  page?: number;
  limit?: number;
}

type WithPage<T = void> = MaybeEmpty<T> & PageParams;
type WithoutPage<T extends { queryParams?: PageParams }> = Omit<T, 'queryParams'> & {
  queryParams?: Omit<T['queryParams'], 'page' | 'limit'>;
};
type RemovePageParams<T> = Omit<T, 'page' | 'limit'>;

interface PageInfoState {
  [k: string]: {
    count: number;
    age: number;
  };
}

export const pageInfo = createSlice({
  name: 'pageInfo',
  initialState: {} as PageInfoState,
  reducers: {
    add(state, { payload: [key, count] }: PayloadAction<[string, number]>) {
      state[key] = { count, age: new Date().valueOf() };
    },
  },
});

function identity<T>(r: T): T {
  return r;
}

type Empty = Record<string, never>;

type SingleQueryPromise<T> = Promise<QueryReturnValue<T, APIError, Empty>>;
type MultiQueryPromise<T> = Promise<QueryReturnValue<T[], APIError, Empty>>;

type SingleMutation<T, PatchParams = void> = (
  args: PatchParams extends void ? number : WithID<PatchParams>,
  api: BaseQueryApi,
) => SingleQueryPromise<T>;

type MultiMutation<T, PatchParams = void> = (
  args: PatchParams extends void ? number : WithID<PatchParams>,
  api: BaseQueryApi,
) => MultiQueryPromise<T>;

type SingleQuery<T, URLParams = void, QueryParams = void> = (
  params: { urlParams?: URLParams; queryParams?: QueryParams } | URLParams | void,
  api: BaseQueryApi,
) => SingleQueryPromise<T>;

type PageQuery<T, URLParams = void, QueryParams = void> = (
  args: { urlParams?: URLParams; queryParams?: WithPage<QueryParams> },
  api: BaseQueryApi,
) => MultiQueryPromise<T>;

type InfiniteQueryPromise<T> = Promise<QueryReturnValue<PaginationInfo<T>, APIError, Empty>>;
type InfiniteQuery<T, URLParams = void, QueryParams = void> = (
  args: {
    queryArg: {
      urlParams?: URLParams;
      queryParams?: RemovePageParams<QueryParams>;
    };
    pageParam: number;
  },
  api: BaseQueryApi,
) => InfiniteQueryPromise<T>;

type PageOrInfinite<T> = T[] | InfiniteData<PaginationInfo<T>, number>;

function getRoot(api: { getState: () => unknown }): string | undefined {
  return (api.getState() as { apiRoot?: RootShape })?.apiRoot?.root;
}

export function getSocketPath(apiOrState: { getState: () => unknown } | { apiRoot: RootShape }, path: string) {
  const r = 'getState' in apiOrState ? getRoot(apiOrState) : apiOrState.apiRoot.root;
  if (r == null) {
    throw new Error('insanity');
  }
  const url = `${r}/../../ws/${path}/`.replace(/\/\/+/g, '/');
  return new URL(url, window.location.origin).toString();
}

function getCSRFToken(api: { getState: () => unknown }): string {
  const csrfToken = (api.getState() as { apiRoot?: RootShape })?.apiRoot?.csrfToken;
  if (csrfToken == null) {
    throw new Error('insanity');
  }
  return csrfToken;
}

function getLimit(api: { getState: () => unknown }): number {
  const limit = (api.getState() as { apiRoot?: RootShape })?.apiRoot?.limit;
  if (limit == null) {
    throw new Error('insanity');
  }
  return limit;
}

type URLOrFunc<T> =
  | (T extends unknown ? string : never)
  | (T extends void ? () => string : T extends undefined ? (r?: T) => string : (r: T) => string);
type MapFunc<T, AT extends APIModel, URLParams> = (m: AT, i: number, a: AT[], e?: URLParams) => T;
type SimpleMapFunc<T, AT extends APIModel> = (m: AT, i: number, a: AT[]) => T;

function urlAndParams<URLParams, QueryParams>(
  urlOrFunc: URLOrFunc<URLParams>,
  params: { urlParams?: URLParams | void; queryParams?: QueryParams } | URLParams | void,
  extraParams?: MaybeObject<URLParams>,
): [string, QueryParams | void] {
  let maybeParams: URLParams | void;
  if (params != null) {
    if (typeof params === 'object') {
      if ('urlParams' in params || 'queryParams' in params) {
        maybeParams = params.urlParams;
      } else {
        maybeParams = params as URLParams;
      }
    } else {
      maybeParams = params;
    }
  }
  const urlParams = typeof maybeParams === 'object' ? { ...maybeParams, ...extraParams } : maybeParams;

  let url: string;
  if (typeof urlOrFunc === 'string') {
    url = urlOrFunc;
  } else {
    url = urlOrFunc(urlParams as URLParams);
  }
  const queryParams =
    (typeof params === 'object' && params && 'queryParams' in params && params.queryParams) || undefined;
  return [url, queryParams];
}

function simpleQuery<T, URLParams, QueryParams>(
  urlOrFunc: URLOrFunc<URLParams>,
  method: Method = 'GET',
): SingleQuery<T, URLParams, QueryParams> {
  return async (params, api): SingleQueryPromise<T> => {
    const [url, queryParams] = urlAndParams(urlOrFunc, params);
    const value = await axiosRequest<T>(getRoot(api), { url, method, params: queryParams });

    if (value.error) {
      return { error: value.error };
    } else {
      return { data: value.data };
    }
  };
}

async function fetchPage<AT extends APIModel>(
  url: string,
  params: AxiosRequestConfig['params'],
  api: BaseQueryApi,
  pageParams: PageParams,
): Promise<QueryReturnValue<PaginationInfo<AT>, APIError, Empty>> {
  let key = api.queryCacheKey || '';
  // derive the page key without the page or limit parameters
  let m = /(,?)"page":\d+(,?)/.exec(key);
  function trim() {
    if (m) {
      let n = m[0].length;
      if (m[1] && m[2]) {
        // only cut out one comma
        --n;
      }
      key = key.slice(0, m.index) + key.slice(m.index + n);
    }
  }
  trim();
  m = /(,?)"limit":\d+(,?)/.exec(key);
  trim();
  let offset: number | undefined;
  if ('page' in params || 'limit' in params || 'offset' in params) {
    return { error: { status: 400, statusText: 'Bad Request', data: 'Page parameters in QueryParams' } };
  }
  const limit = getLimit(api);
  if (pageParams.page != null) {
    if (pageParams.page < 1) {
      return { error: { status: 400, statusText: 'Bad Request', data: 'Invalid page number' } };
    }
    if (pageParams.limit != null && pageParams.limit < 1) {
      return { error: { status: 400, statusText: 'Bad Request', data: 'Invalid limit parameter' } };
    }
    const { pageInfo: info } = api.getState() as { pageInfo: PageInfoState };
    let count = info[key]?.count || 0;
    if (pageParams.page > 1) {
      // refetch if it is more than 5 minutes old
      if (info[key]?.age || 0 < new Date().valueOf() - 300000) {
        const newInfo = await axiosRequest<PaginationInfo<AT>>(getRoot(api), {
          url: url,
          params: { limit: 0, ...params },
        });
        if (newInfo.error) {
          return { error: newInfo.error };
        }
        api.dispatch(pageInfo.actions.add([key, newInfo.data.count]));
        count = newInfo.data.count;
      }
    }
    const numPages = Math.max(Math.ceil(count / (pageParams.limit || limit)), 1);
    if (pageParams.page > numPages) {
      return { error: { status: 404, statusText: 'Not Found', data: 'Page does not exist' } };
    }
    offset = limit * (pageParams.page - 1);
  }
  const finalParams = { offset, ...params };
  if (pageParams.limit && pageParams.limit !== limit) {
    finalParams.limit = pageParams.limit;
  }
  return axiosRequest<PaginationInfo<AT>>(getRoot(api), {
    url: url,
    params: finalParams,
  });
}

function infiniteQuery<T, AT extends APIModel, URLParams, QueryParams>(
  urlOrFunc: URLOrFunc<URLParams>,
  map: MapFunc<T, AT, URLParams>,
  extraParams?: MaybeObject<URLParams>,
): InfiniteQuery<T, URLParams, QueryParams> {
  return async ({ queryArg: { urlParams, queryParams }, pageParam }, api): InfiniteQueryPromise<T> => {
    const [url, finalParams] = urlAndParams(urlOrFunc, { urlParams, queryParams }, extraParams);
    const page = await fetchPage<AT>(url, finalParams, api, { page: pageParam });
    if (page.data) {
      const { results, ...rest } = page.data;
      return {
        data: {
          ...rest,
          results: results.map((m, i, a) => map(m, i, a, urlParams)),
        },
      };
    } else {
      return page;
    }
  };
}

function paginatedQuery<T, AT extends APIModel, URLParams, QueryParams>(
  urlOrFunc: URLOrFunc<URLParams>,
  map: MapFunc<T, AT, URLParams>,
  extraParams?: URLParams extends object ? URLParams : never,
): PageQuery<T, URLParams, QueryParams> {
  return async ({ urlParams, queryParams } = {}, api): MultiQueryPromise<T> => {
    let key = api.queryCacheKey || '';
    const m = /(,?)"page":\d+(,?)/.exec(key);
    if (m) {
      let n = m[0].length;
      if (m[1] && m[2]) {
        --n;
      }
      key = key.slice(0, m.index) + key.slice(m.index + n);
    }
    let offset: number | undefined;
    const { page, ...rest } = queryParams ? queryParams : { page: null };
    const [url, finalParams] = urlAndParams(urlOrFunc, { urlParams, queryParams: rest }, extraParams);
    const limit = getLimit(api);
    if (limit == null) {
      return { error: { status: 400, statusText: 'Bad Request', data: 'No API page limit defined' } };
    }
    if (page != null) {
      if (page < 1) {
        return { error: { status: 400, statusText: 'Bad Request', data: 'Invalid page number' } };
      }
      const { pageInfo: info } = api.getState() as { pageInfo: PageInfoState };
      let count = info[key]?.count || 0;
      if (page > 1) {
        if (info[key]?.age || 0 < new Date().valueOf() - 300) {
          const newInfo = await axiosRequest<PaginationInfo<AT>>(getRoot(api), {
            url: url,
            params: { limit: 0, ...finalParams },
          });
          if (newInfo.error) {
            return { error: newInfo.error };
          }
          api.dispatch(pageInfo.actions.add([key, newInfo.data.count]));
          count = newInfo.data.count;
        }
      }
      const numPages = Math.max(Math.ceil(count / limit), 1);
      if (page > numPages) {
        return { error: { status: 404, statusText: 'Not Found', data: 'Page does not exist' } };
      }
      offset = limit * (page - 1);
    }
    const value = await axiosRequest<PaginationInfo<AT>>(getRoot(api), {
      url: url,
      params: { offset: offset, limit, ...finalParams },
    });
    if (value.error) {
      return { error: value.error };
    } else {
      return { data: value.data.results.map((d, n, a) => map(d, n, a, urlParams)) };
    }
  };
}

function mutation<T, PatchArgs = void, AT extends APIModel = T extends APIModel ? T : never>(
  urlFunc: (r: number) => string,
  map?: SimpleMapFunc<T, AT>,
  method?: Method,
): SingleMutation<T, PatchArgs> {
  return async (args, api): SingleQueryPromise<T> => {
    const { id, ...params } = typeof args === 'object' ? { ...args } : { id: args };
    const url = urlFunc(id);
    const csrfToken = getCSRFToken(api);
    const result = await axiosRequest<AT>(getRoot(api), {
      url,
      method: method ?? 'PATCH',
      data: params,
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });
    if (result.error) {
      return { error: result.error };
    } else {
      return { data: map ? map(result.data, 0, [result.data]) : (result.data as unknown as T) };
    }
  };
}

function multiMutation<T, PatchArgs = void>(urlFunc: (r: number) => string): MultiMutation<T, PatchArgs>;
function multiMutation<T, PatchArgs, AT>(
  urlFunc: (r: number) => string,
  map: (m: AT, i: number, a: AT[]) => T,
): MultiMutation<T, PatchArgs>;

function multiMutation<T, PatchArgs = void, AT = unknown>(
  urlFunc: (r: number) => string,
  map?: (m: AT, i: number, a: AT[]) => T,
): MultiMutation<T, PatchArgs> {
  return async (args, api): MultiQueryPromise<T> => {
    const { id, ...params } = typeof args === 'object' ? { ...args } : { id: args };
    const url = urlFunc(id);
    const csrfToken = getCSRFToken(api);
    const result = await axiosRequest<AT[]>(getRoot(api), {
      url,
      method: 'patch',
      data: params,
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });
    if (result.error) {
      return { error: result.error };
    } else {
      return { data: map ? result.data.map(map) : (result.data as unknown as T[]) };
    }
  };
}

type MutationArgsType = number | string | { id: number };

// this needs to be here to avoid circular references

type EventQuery = WithListen<{ queryParams?: WithPage<EventGet> }>;
type RunQuery = { urlParams?: Parameters<typeof Endpoints.RUNS>[0]; queryParams?: WithPage<RunGet> };
type BidQuery = {
  urlParams?: WithEvent<Parameters<typeof Endpoints.BIDS>[0]>;
  queryParams?: WithPage<BidGet>;
};
type DonationQuery = WithListen<{
  urlParams?: Parameters<typeof Endpoints.DONATIONS>[0];
  queryParams?: WithPage<DonationGet>;
}>;
type DonationGroupQuery = WithListen;

type MutationResult = FlatBid | Donation | Run | Run[];

type StoreTypeMap = {
  me: {
    query: void;
    result: Me;
    store: Me;
  };
  bidTree: {
    query: BidQuery | void;
    result: TreeBid[];
    store: TreeBid[];
  };
  bids: {
    query: BidQuery | void;
    result: FlatBid[];
    store: FlatBid[];
  };
  donations: {
    query: DonationQuery | void;
    result: Donation[];
    store: Donation[];
  };
  allDonations: {
    query: WithoutPage<DonationQuery> | void;
    result: PaginationInfo<Donation>;
    store: PaginationInfo<Donation>[];
  };
  runs: {
    query: RunQuery | void;
    result: Run[];
    store: Run[];
  };
};

// TODO: figure out if this is exported
type QueryFulfilledError =
  | {
      error: BaseQueryError<typeof axiosRequest>;
      isUnhandledError: false;
      meta: BaseQueryMeta<typeof axiosRequest>;
    }
  | {
      error: unknown;
      meta?: undefined;
      isUnhandledError: true;
    };

function invalidateMeIfForbidden(dispatch: Dispatch, e: QueryFulfilledError) {
  if (!e.isUnhandledError && e.error.status === 403) {
    dispatch(trackerApi.util.invalidateTags(['me']));
  }
}

/**
 * helper when a mutation wants to optimistically update the cache
 * @template T - either a single model type, or an array type, depending on what the endpoint returns
 * @template MutationArgs - the arguments passed to the mutation hook
 * @template OriginalArgs - the arguments that were passed to the query hooks, can be left off if your mutation doesn't
 *   care about them
 * @param {CacheKey} k - the cache key that will be updated
 * @param {Function} preUpdate - a function that will receive the id of the updated model, plus any additional mutation
 *   parameters, and should return a function that receives a writeable array of the model type and actually performs
 *   the update
 * @param {Function} postUpdate - an optional function that will receive the result of the mutation and the current
 *   cache value, in case certain updates cannot be performed until after the server result is known
 * @param {Tags} tags - an optional tag or list of tags to invalidate if the mutation fails, to ensure that the client
 *   state matches the server state
 * @return a function suitable to pass into onQueryStarted
 */

function optimisticMutation<
  MutationArgs extends MutationArgsType,
  const K extends CacheKey,
  Result extends MutationResult = Flatten<StoreTypeMap[K]['result']> extends MutationResult
    ? Flatten<StoreTypeMap[K]['result']>
    : never,
  UpdateParams = {
    originalArgs: StoreTypeMap[K]['query'];
    mutationArgs: MutationArgs extends number ? void : Omit<MutationArgs, 'id'>;
  },
>(
  k: K,
  preUpdate: (id: number | string, params: UpdateParams) => (cacheData: StoreTypeMap[K]['store']) => void,
  postUpdate?: (queryData: Result, cacheData: StoreTypeMap[K]['store'], params: UpdateParams) => void,
  tags?: Tags,
): NonNullable<TypedMutationOnQueryStarted<Result, MutationArgs, EmptyBaseQuery>> {
  return async (args: MutationArgs, api) => {
    const { id, ...mutationArgs } = typeof args === 'object' ? { ...args } : { id: args };
    function update(recipe: (o: StoreTypeMap[K]['query']) => (cacheData: StoreTypeMap[K]['store']) => void) {
      return (
        trackerApi.util
          .selectCachedArgsForQuery(api.getState(), k)
          // FIXME: make the type system happy
          // eslint-disable-next-line @typescript-eslint/ban-ts-comment
          // @ts-ignore
          .map(o => api.dispatch(trackerApi.util.updateQueryData(k, o, recipe(o))))
      );
    }
    // FIXME: make the type system happy
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    const undo = update(originalArgs => preUpdate(id, { originalArgs, mutationArgs })).map(r => r.undo);
    try {
      const { data } = await api.queryFulfilled;
      update(originalArgs => drafts => {
        if (Array.isArray(drafts)) {
          if (Array.isArray(data)) {
            data.forEach(model => {
              const i = drafts.findIndex(draft => draft.id === model.id && draft.type === model.type);
              if (i !== -1) {
                drafts[i] = { ...drafts[i], ...model };
              }
            });
          } else {
            const i = drafts.findIndex(draft => draft.id === data.id && draft.type === data.type);
            if (i !== -1) {
              drafts[i] = { ...drafts[i], ...data };
            }
          }
        }
        if (postUpdate) {
          // FIXME: make the type system happy
          // eslint-disable-next-line @typescript-eslint/ban-ts-comment
          // @ts-ignore
          postUpdate(data, drafts, { originalArgs, mutationArgs });
        }
      });
    } catch (e) {
      invalidateMeIfForbidden(api.dispatch, e as QueryFulfilledError);
      undo.forEach(u => u());
      api.dispatch(trackerApi.util.invalidateTags(forceArray(tags)));
    }
  };
}

type OptimisticMutation<
  MutationArgs extends MutationArgsType,
  K extends CacheKey,
  Result extends MutationResult = StoreTypeMap[K]['result'] extends MutationResult ? StoreTypeMap[K]['result'] : never,
> = ReturnType<typeof optimisticMutation<MutationArgs, K, Result>>;

function updateOptionInTree(state: BidState) {
  return (id: number | string) => (a: TreeBid[]) => {
    const d = a.find(b => b.options?.some(o => o.id === id))?.options?.find(o => o.id === id);
    if (d) {
      d.state = state;
    }
  };
}

function updateFlatOption(state: BidState) {
  return (id: number | string) => {
    return (a: FlatBid[]) => {
      const d = a.find(m => m.id === id);
      if (d) {
        d.state = state;
      }
    };
  };
}

function updateAllBids(state: BidState): OptimisticMutation<number, 'bids', FlatBid> {
  return async (args, api) => {
    const treeResult = optimisticMutation<number, 'bidTree', FlatBid>('bidTree', updateOptionInTree(state))(args, api);
    const flatResult = optimisticMutation<number, 'bids'>('bids', updateFlatOption(state))(args, api);
    // await after ensuring the optimistic updates have fired
    await treeResult;
    return flatResult;
  };
}

function patchRun() {
  return optimisticMutation<WithID<RunPatch>, 'runs', Run>('runs', (id, { mutationArgs }) => runs => {
    const draftIndex = runs.findIndex(r => r.id === id);
    if (draftIndex !== -1) {
      const run = runs[draftIndex];
      const { run_time, setup_time, anchor_time, order, event, starttime } = run;
      const old_start_time = starttime;
      const new_anchor_time = parseTime(
        mutationArgs.anchor_time !== undefined ? mutationArgs.anchor_time : anchor_time,
      );
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
        runs
          .filter((r): r is OrderedRun => r.order != null && r.event === event && r.order > order)
          .forEach((r, i, ri) => {
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
}

function moveRun() {
  return optimisticMutation<WithID<PatchMoveRun>, 'runs', Run[]>('runs', (id, { mutationArgs }) => runs => {
    const d = runs.find(r => r.id === id);
    if (d == null) {
      return;
    }
    let diff: -1 | 1 | 0 = 0;
    const ordered = runs.filter(isOrdered);
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
}

type PatchMoveRun = { before: number } | { after: number } | { order: number | null | 'last' };

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

type TypedQueryOnCacheEntryAdded<ResultType = unknown, QueryArg = unknown> = NonNullable<
  QueryExtraOptions<string, ResultType, QueryArg, EmptyBaseQuery>['onCacheEntryAdded']
>;

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
 * helper for findIndex to find a possible insertion slot for the donation in the array
 */

function findDonationByTime(newDonation: Donation): Parameters<Donation[]['findIndex']>[0] {
  return (d, i, a) => {
    const prev = i === 0 ? null : a[i - 1];
    return (
      (prev == null || prev.timereceived >= newDonation.timereceived) && newDonation.timereceived >= d.timereceived
    );
  };
}

function donationMatchesQuery(donation: Donation, query: DonationQuery) {
  const { urlParams: { state, eventId } = {}, queryParams: { id, time_gte } = {} } = query;
  const newState = getDonationState(donation);
  return (
    isNullOrEqual(state, newState) &&
    isNullOrEqual(eventId, donation.event) &&
    isNullOrEqualOrContains(id, donation.id) &&
    (time_gte == null || donation.timereceived >= DateTime.fromISO(time_gte))
  );
}

const socketDonation: TypedQueryOnCacheEntryAdded<PageOrInfinite<Donation>, DonationQuery | void> = async (
  arg,
  api,
) => {
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

      if (!('donation' in data)) {
        return;
      }

      const newDonation = processDonation(data.donation, 0, [data.donation]);

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
    },
    ['donations'],
  );
  await api.cacheEntryRemoved;
  remove();
};

function mutateDonation(fields: Partial<Pick<Donation, 'commentstate' | 'readstate' | 'pinned'>>) {
  // TODO: have this update `allDonations` as well? currently the only pages that can mutate donations do not use it
  return optimisticMutation<number, 'donations', Donation>(
    'donations',
    id => donations => {
      const index = donations.findIndex(d => d.id === id);
      if (index !== -1) {
        donations[index] = {
          ...donations[index],
          ...fields,
        };
      }
    },
    (donation, donations, { originalArgs }) => {
      const currentIndex = donations.findIndex(d => d.id === donation.id);
      const index = donations.findIndex(findDonationByTime(donation));
      if (originalArgs == null || donationMatchesQuery(donation, originalArgs)) {
        if (currentIndex === -1) {
          donations.splice(index, 0, donation);
        }
      } else if (currentIndex !== -1) {
        donations.splice(currentIndex, 1);
      }
    },
  );
}

const updateDonationComment = optimisticMutation<WithID<{ comment: string }>, 'donations', Donation>(
  'donations',
  (id, { mutationArgs: { comment } }) =>
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

function updateDonationGroups(
  add: boolean,
): TypedMutationOnQueryStarted<string[], Parameters<typeof Endpoints.DONATIONS_GROUPS>[0], EmptyBaseQuery> {
  return async ({ donationId, group }, api) => {
    function sync(donation?: Donation) {
      if (donation?.groups) {
        if (add && !donation.groups.includes(group)) {
          donation.groups.push(group);
        } else if (!add && donation.groups.includes(group)) {
          donation.groups = donation.groups.filter(g => g !== group);
        }
      }
    }
    const undo = trackerApi.util.selectCachedArgsForQuery(api.getState(), 'donations').map(
      args =>
        api.dispatch(
          trackerApi.util.updateQueryData('donations', args, donations => {
            sync(donations.find(d => d.id === donationId));
          }),
        ).undo,
    );
    undo.concat(
      trackerApi.util.selectCachedArgsForQuery(api.getState(), 'allDonations').map(
        args =>
          api.dispatch(
            trackerApi.util.updateQueryData('allDonations', args, donations => {
              sync(
                donations.pages
                  .find(p => p.results.find(d => d.id === donationId))
                  ?.results.find(d => d.id === donationId),
              );
            }),
          ).undo,
      ),
    );
    try {
      await api.queryFulfilled;
    } catch (e) {
      invalidateMeIfForbidden(api.dispatch, e as QueryFulfilledError);
      undo.forEach(u => u());
    }
  };
}

enum TagType {
  'me',
  'events',
  'bids',
  'runs',
  'prizes',
  'interviews',
  'ads',
  'donations',
  'donationGroups',
  'milestones',
}

type Tags = MaybeArray<TagDescription<keyof typeof TagType>>;

const infiniteQueryOptions = {
  initialPageParam: 1,
  getNextPageParam: (
    lastPage: PaginationInfo<unknown>,
    allPages: PaginationInfo<unknown>[],
    lastPageParam: number,
    allPageParams: number[],
  ) => (lastPage.next != null ? lastPageParam + 1 : undefined),
  getPreviousPageParam: (
    firstPage: PaginationInfo<unknown>,
    allPages: PaginationInfo<unknown>[],
    firstPageParam: number,
    allPageParams: number[],
  ) => (firstPage.previous != null ? firstPageParam - 1 : undefined),
};

type SocketCallbacks = { socket: SturdyWebSocket; callbacks: ((ev: MessageEvent) => MaybePromise<void>)[] };
const sockets: Record<string, SocketCallbacks> = {};

function newSocket(url: string) {
  const socket = new SturdyWebSocket(url, {
    shouldReconnect: ev => !ev.wasClean,
  });
  socket.addEventListener(
    'message',
    async ev => await Promise.allSettled(sockets[url].callbacks.map(async cb => await cb(ev))),
  );
  return socket;
}

/*
 * looks for an existing socket at the specified url, creates one if none exist, and sets up callbacks to track the
 * state of the socket in the Redux store as well as optionally invalidating query tags if the socket has to reconnect
 * to ensure that the data stays in sync
 */
async function getSocket(url: string, dispatch: Dispatch, tags: Tags = []) {
  let socket = sockets[url]?.socket;
  if (socket == null || socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED) {
    socket = newSocket(url);
    dispatch(socketsSlice.actions.setState({ [url]: socket.readyState }));
    socket.addEventListener('open', () => {
      dispatch(socketsSlice.actions.setState({ [url]: WebSocket.OPEN }));
    });
    socket.addEventListener('reopen', () => {
      dispatch(socketsSlice.actions.setState({ [url]: WebSocket.OPEN }));
      dispatch(trackerApi.util.invalidateTags(forceArray(tags)));
    });
    socket.addEventListener('close', () => {
      dispatch(socketsSlice.actions.setState({ [url]: WebSocket.CLOSED }));
    });
    socket.addEventListener('down', () => {
      dispatch(socketsSlice.actions.setState({ [url]: WebSocket.CONNECTING }));
    });
    sockets[url] = { socket, callbacks: [] };
  }
  if (socket.readyState !== WebSocket.OPEN) {
    // TODO: does this ever happen with SturdyWebSocket? maybe if the network is disabled?
    await new Promise<void>((resolve, reject) => {
      function open() {
        socket.removeEventListener('open', open);
        socket.removeEventListener('close', close);
        resolve();
      }
      function close() {
        socket.removeEventListener('open', open);
        socket.removeEventListener('close', close);
        reject();
      }
      socket.addEventListener('open', open);
      socket.addEventListener('close', close);
    });
  }
  return sockets[url];
}

async function addCallback(url: string, dispatch: Dispatch, callback: (ev: MessageEvent) => void, tags: Tags = []) {
  url = new URL(url, window.location.origin).toString();
  if (/^https?:\/\//.test(url)) {
    url = url.replace(/^http/, 'ws');
  }
  const socket = await getSocket(url, dispatch, tags);
  socket.callbacks.push(callback);
  return () => {
    sockets[url].callbacks = sockets[url].callbacks.filter(c => c !== callback);
    if (sockets[url].callbacks.length === 0) {
      sockets[url].socket.close();
      delete sockets[url];
      dispatch(socketsSlice.actions.remState(url));
    }
  };
}

type MilestoneQuery = { urlParams?: Parameters<typeof Endpoints.MILESTONES>[0]; queryParams?: WithPage<MilestoneGet> };
type PrizeQuery = { urlParams?: Parameters<typeof Endpoints.PRIZES>[0]; queryParams?: WithPage<PrizeGet> };
type InterviewQuery = {
  urlParams?: WithEvent<Parameters<typeof Endpoints.INTERVIEWS>[0]>;
  queryParams?: WithPage<InterviewGet>;
};
type AdQuery = {
  urlParams?: WithEvent<Parameters<typeof Endpoints.ADS>[0]>;
  queryParams?: WithPage;
};
export const trackerApi = createApi({
  reducerPath: 'tracker',
  tagTypes: Object.keys(TagType),
  baseQuery: emptyRequest,
  endpoints: build => ({
    me: build.query<Me, void>({
      queryFn: simpleQuery(Endpoints.ME),
      providesTags: ['me'],
    }),
    events: build.query<Event[], EventQuery | void>({
      queryFn: paginatedQuery(Endpoints.EVENTS, processEvent),
      providesTags: ['events'],
      async onCacheEntryAdded(arg, api) {
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
      },
    }),
    runs: build.query<Run[], RunQuery>({
      queryFn: paginatedQuery(Endpoints.RUNS, processRun),
      providesTags: ['runs'],
    }),
    patchRun: build.mutation<Run, WithID<RunPatch>>({
      queryFn: mutation<Run, RunPatch, APIRun>(Endpoints.RUN, processRun),
      onQueryStarted: patchRun(),
    }),
    moveRun: build.mutation<Run[], WithID<PatchMoveRun>>({
      queryFn: multiMutation<Run, PatchMoveRun, APIRun>(Endpoints.MOVE_RUN, processRun),
      onQueryStarted: moveRun(),
    }),
    milestones: build.query<Milestone[], MilestoneQuery | void>({
      queryFn: paginatedQuery(Endpoints.MILESTONES, processMilestone),
      providesTags: ['milestones'],
    }),
    bids: build.query<FlatBid[], BidQuery | void>({
      queryFn: paginatedQuery(Endpoints.BIDS, identity<FlatBid>, { tree: false }),
      providesTags: ['bids'],
    }),
    bidTree: build.query<TreeBid[], BidQuery | void>({
      queryFn: paginatedQuery(Endpoints.BIDS, identity<TreeBid>, { tree: true }),
      providesTags: ['bids'],
    }),
    approveBid: build.mutation<FlatBid, number>({
      queryFn: mutation(Endpoints.APPROVE_BID),
      onQueryStarted: updateAllBids('OPENED'),
    }),
    denyBid: build.mutation<FlatBid, number>({
      queryFn: mutation(Endpoints.DENY_BID),
      onQueryStarted: updateAllBids('DENIED'),
    }),
    prizes: build.query<Prize[], PrizeQuery | void>({
      queryFn: paginatedQuery(Endpoints.PRIZES, processPrize),
      providesTags: ['prizes'],
    }),
    interviews: build.query<Interview[], InterviewQuery | void>({
      queryFn: paginatedQuery(Endpoints.INTERVIEWS, processInterstitial<APIInterview, Interview>),
      providesTags: ['interviews'],
    }),
    ads: build.query<Ad[], AdQuery | void>({
      queryFn: paginatedQuery(Endpoints.ADS, processInterstitial<APIAd, Ad>),
      providesTags: ['ads'],
    }),
    donationGroups: build.query<string[], DonationGroupQuery | void>({
      queryFn: simpleQuery(Endpoints.DONATION_GROUPS),
      providesTags: ['donationGroups'],
      async onCacheEntryAdded(arg, api) {
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
      },
    }),
    createDonationGroup: build.mutation<string, string>({
      queryFn: simpleQuery(Endpoints.DONATION_GROUP, 'PUT'),
      async onQueryStarted(arg, api) {
        const args = trackerApi.util.selectCachedArgsForQuery(api.getState(), 'donationGroups');
        const undo = args.map(a => {
          const { undo } = api.dispatch(
            trackerApi.util.updateQueryData('donationGroups', a, data => {
              if (!data.includes(arg)) {
                data.push(arg);
              }
            }),
          );
          return undo;
        });
        try {
          await api.queryFulfilled;
        } catch (e) {
          invalidateMeIfForbidden(api.dispatch, e as QueryFulfilledError);
          undo.forEach(u => u());
        }
      },
    }),
    deleteDonationGroup: build.mutation<void, string>({
      queryFn: simpleQuery(Endpoints.DONATION_GROUP, 'DELETE'),
      async onQueryStarted(arg, api) {
        const args = trackerApi.util.selectCachedArgsForQuery(api.getState(), 'donationGroups');
        const undo = args.map(a => {
          const { undo } = api.dispatch(
            trackerApi.util.updateQueryData('donationGroups', a, data => {
              const index = data.findIndex(g => g === arg);
              if (index !== -1) {
                data.splice(index, 1);
              }
            }),
          );
          return undo;
        });
        try {
          await api.queryFulfilled;
        } catch (e) {
          invalidateMeIfForbidden(api.dispatch, e as QueryFulfilledError);
          undo.forEach(u => u());
        }
      },
    }),
    donations: build.query<Donation[], DonationQuery | void>({
      queryFn: paginatedQuery(Endpoints.DONATIONS, processDonation),
      providesTags: ['donations'],
      onCacheEntryAdded: socketDonation,
    }),
    allDonations: build.infiniteQuery<PaginationInfo<Donation>, WithoutPage<DonationQuery> | void, number>({
      queryFn: infiniteQuery(Endpoints.DONATIONS, processDonation),
      providesTags: ['donations'],
      async onCacheEntryAdded(arg, api) {
        // TODO: https://github.com/reduxjs/redux-toolkit/issues/4901
        // should be fixed in 2.6.2
        if (api.updateCachedData == null) {
          api.updateCachedData = updateRecipe =>
            api.dispatch(trackerApi.util.updateQueryData('allDonations', arg, updateRecipe));
        }
        await socketDonation(arg, api);
      },
      infiniteQueryOptions,
    }),
    unprocessDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_UNPROCESS, processDonation),
      onQueryStarted: mutateDonation({ commentstate: 'PENDING', readstate: 'PENDING' }),
    }),
    approveDonationComment: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_APPROVE_COMMENT, processDonation),
      onQueryStarted: mutateDonation({ commentstate: 'APPROVED', readstate: 'IGNORED' }),
    }),
    denyDonationComment: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_DENY_COMMENT, processDonation),
      onQueryStarted: mutateDonation({ commentstate: 'DENIED', readstate: 'IGNORED' }),
    }),
    flagDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_FLAG, processDonation),
      onQueryStarted: mutateDonation({ commentstate: 'APPROVED', readstate: 'FLAGGED' }),
    }),
    sendDonationToReader: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_SEND_TO_READER, processDonation),
      onQueryStarted: mutateDonation({ commentstate: 'APPROVED', readstate: 'READY' }),
    }),
    pinDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_PIN, processDonation),
      onQueryStarted: mutateDonation({ pinned: true }),
    }),
    unpinDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_UNPIN, processDonation),
      onQueryStarted: mutateDonation({ pinned: false }),
    }),
    readDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_READ, processDonation),
      onQueryStarted: mutateDonation({ readstate: 'READ' }),
    }),
    ignoreDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_IGNORE, processDonation),
      onQueryStarted: mutateDonation({ readstate: 'IGNORED' }),
    }),
    editDonationComment: build.mutation<Donation, WithID<{ comment: string }>>({
      queryFn: mutation(Endpoints.DONATIONS_COMMENT, processDonation),
      onQueryStarted: updateDonationComment,
    }),
    addDonationToGroup: build.mutation<string[], Parameters<typeof Endpoints.DONATIONS_GROUPS>[0]>({
      queryFn: simpleQuery(Endpoints.DONATIONS_GROUPS, 'PATCH'),
      onQueryStarted: updateDonationGroups(true),
    }),
    removeDonationFromGroup: build.mutation<string[], Parameters<typeof Endpoints.DONATIONS_GROUPS>[0]>({
      queryFn: simpleQuery(Endpoints.DONATIONS_GROUPS, 'DELETE'),
      onQueryStarted: updateDonationGroups(false),
    }),
  }),
  refetchOnReconnect: true,
});

// TODO: do this without a circular reference?
// type CacheKey = Parameters<typeof trackerApi.util.selectCachedArgsForQuery>[1];
type CacheKey = 'bidTree' | 'bids' | 'runs' | 'donations';

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

export type UseDonationMutation = typeof useApproveDonationCommentMutation;
export type UseDonationMutationResult = ReturnType<UseDonationMutation>;
type TrackerEndpoints = typeof trackerApi.endpoints;
export type TrackerQueryKeys = keyof {
  [K in keyof TrackerEndpoints as TrackerEndpoints[K] extends { useQuery: any } ? K : never]: TrackerEndpoints[K];
};
export type TrackerInfiniteQueryKeys = keyof {
  [K in keyof TrackerEndpoints as TrackerEndpoints[K] extends { useInfiniteQuery: any }
    ? K
    : never]: TrackerEndpoints[K];
};
export type TrackerAllQueryKeys = TrackerQueryKeys | TrackerInfiniteQueryKeys;
export type TrackerMutationKeys = keyof {
  [K in keyof TrackerEndpoints as TrackerEndpoints[K] extends { useMutation: any } ? K : never]: TrackerEndpoints[K];
};

interface RootShape {
  root: string;
  limit: number;
  csrfToken: string;
}

export const apiRootSlice = createSlice({
  name: 'apiRoot',
  initialState: { root: '', limit: 0, csrfToken: '' } as RootShape,
  reducers: {
    setRoot(_, action: PayloadAction<RootShape>) {
      return action.payload;
    },
  },
});

export const { setRoot } = apiRootSlice.actions;

interface SocketShape {
  [url: string]: number;
}

export const socketsSlice = createSlice({
  name: 'sockets',
  initialState: {} as SocketShape,
  reducers: {
    setState(state, { payload }: PayloadAction<SocketShape>) {
      return { ...state, ...payload };
    },
    remState(state, { payload }: PayloadAction<string>) {
      delete state[payload];
    },
  },
});
