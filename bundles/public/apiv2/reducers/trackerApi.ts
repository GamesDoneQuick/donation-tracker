import type { AxiosError, AxiosRequestConfig } from 'axios';
import { Draft, WritableDraft } from 'immer';
import { DateTime, Duration } from 'luxon';
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { BaseQueryApi, QueryReturnValue, TypedMutationOnQueryStarted } from '@reduxjs/toolkit/query';
import { createApi } from '@reduxjs/toolkit/query/react';

import {
  Ad as APIAd,
  BidGet,
  BidState,
  Event as APIEvent,
  EventGet,
  FlatBid,
  Interview as APIInterview,
  InterviewGet,
  Me,
  Model,
  PaginationInfo,
  PrizeGet,
  Run as APIRun,
  RunGet,
  RunPatch,
  TreeBid,
} from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import { parseDuration, parseTime } from '@public/apiv2/helpers/luxon';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { Ad, Event, Interview, OrderedRun, Prize, Run } from '@public/apiv2/Models';
import { processInterstitial, processPrize, processRun } from '@public/apiv2/Processors';

export interface APIError {
  status?: number;
  statusText?: string;
  data?: any;
}

async function emptyRequest() {
  return axiosRequest<unknown>(undefined, {});
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
type WithID<T> = { id: number } & T;
type WithEvent<T = void> = { eventId?: number } & MaybeEmpty<T>;
type WithPage<T = void> = { page?: number } & MaybeEmpty<T>;

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
    add(state, action: PayloadAction<[string, number]>) {
      state[action.payload[0]] = { count: action.payload[1], age: new Date().valueOf() };
    },
  },
});

function identity<T>(r: T): T {
  return r;
}

type Empty = Record<string, never>;

type SingleQueryPromise<T> = Promise<QueryReturnValue<T, APIError, Empty>>;

type SingleMutation<T, PatchParams = void> = (
  args: PatchParams extends void ? number : WithID<PatchParams>,
  api: BaseQueryApi,
) => SingleQueryPromise<T>;

type MultiQueryPromise<T> = Promise<QueryReturnValue<T[], APIError, Empty>>;
type MultiMutation<T, PatchParams = void> = (
  args: PatchParams extends void ? number : WithID<PatchParams>,
  api: BaseQueryApi,
) => MultiQueryPromise<T>;

type PageQueryPromise<T> = Promise<QueryReturnValue<T[], APIError, Empty>>;
type PageQuery<T, URLParams = void, QueryParams = void> = (
  args: { urlParams?: URLParams; queryParams?: WithPage<QueryParams> },
  api: BaseQueryApi,
) => PageQueryPromise<T>;

function getRoot(api: BaseQueryApi): string | undefined {
  return (api.getState() as { apiRoot?: RootShape })?.apiRoot?.root;
}

function getCSRFToken(api: BaseQueryApi): string | undefined {
  return (api.getState() as { apiRoot?: RootShape })?.apiRoot?.csrfToken;
}

function simpleQuery<T, URLParams, QueryParams>(
  urlOrFunc: (URLParams extends void ? never : string) | ((r?: URLParams) => string),
) {
  return async (
    { urlArgs, queryArgs }: { urlArgs?: URLParams; queryArgs?: QueryParams } | void = {},
    api: BaseQueryApi,
  ): SingleQueryPromise<T> => {
    const url = typeof urlOrFunc === 'string' ? urlOrFunc : urlOrFunc(urlArgs);
    const value = await axiosRequest<T>(getRoot(api), { url, params: queryArgs });

    if (value.error) {
      return { error: value.error };
    } else {
      return { data: value.data };
    }
  };
}

function paginatedQuery<T, AT extends Model, URLParams, QueryParams>(
  urlOrFunc: (URLParams extends unknown ? string : never) | ((r?: URLParams) => string),
  map: (m: AT, i: number, a: AT[], e?: URLParams) => T,
  extraParams?: URLParams,
): PageQuery<T, URLParams, QueryParams> {
  return async (
    { urlParams, queryParams }: { urlParams?: URLParams; queryParams?: WithPage<QueryParams> } = {},
    api: BaseQueryApi,
  ): PageQueryPromise<T> => {
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
    const params = typeof urlParams === 'object' ? { ...urlParams, ...extraParams } : urlParams;
    const url = typeof urlOrFunc === 'string' ? urlOrFunc : urlOrFunc(params);
    const { page, ...rest } = queryParams ? queryParams : { page: null };
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
            params: { limit: 0, ...rest },
          });
          if (newInfo.error) {
            return { error: newInfo.error };
          }
          api.dispatch(pageInfo.actions.add([key, newInfo.data.count]));
          count = newInfo.data.count;
        }
      }
      const {
        apiRoot: { limit },
      } = api.getState() as { apiRoot: { limit: number } };
      const numPages = Math.min(Math.ceil(count / limit), 1);
      if (page > numPages) {
        return { error: { status: 404, statusText: 'Not Found', data: 'Page does not exist' } };
      }
      offset = limit * (page - 1);
    }
    const value = await axiosRequest<PaginationInfo<AT>>(getRoot(api), {
      url: url,
      params: { offset: offset, ...rest },
    });
    if (value.error) {
      return { error: value.error };
    } else {
      return { data: value.data.results.map((d, n, a) => map(d, n, a, params)) };
    }
  };
}

function mutation<T, PatchArgs = void, AT = T>(
  urlFunc: (r: number) => string,
  map?: (m: AT, i: number, a: AT[]) => T,
): SingleMutation<T, PatchArgs> {
  return async (args, api): SingleQueryPromise<T> => {
    const { id, ...params } = typeof args === 'object' ? { ...args } : { id: args };
    const url = urlFunc(id);
    const csrfToken = getCSRFToken(api);
    const result = await axiosRequest<AT>(getRoot(api), {
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
      return { data: map ? map(result.data, 0, [result.data]) : (result.data as unknown as T) };
    }
  };
}

function multiMutation<T, PatchArgs = void, AT = T>(
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

type MutationArgsType = number | { id: number };
type StoreModel = FlatBid | TreeBid | Run;

function optimisticMutation<T extends StoreModel, MutationArgs extends MutationArgsType>(
  k: CacheKey,
  preUpdate: (id: number, params: MutationArgs extends number ? void : Omit<MutationArgs, 'id'>) => (m: T[]) => void,
  postUpdate?: (data: T, m: T[]) => void,
  tags?: (keyof TagType)[],
): TypedMutationOnQueryStarted<T, MutationArgs, EmptyBaseQuery> {
  return async (args: MutationArgs, api) => {
    const { id, ...params } = typeof args === 'object' ? { ...args } : { id: args };
    const patchResults: { undo: () => void }[] = [];
    const queryArgs = trackerApi.util.selectCachedArgsForQuery(api.getState(), k);
    queryArgs.forEach(p => {
      // FIXME: is there a way to make the type system smart enough to know that this is guaranteed to be the same type?
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      patchResults.push(api.dispatch(trackerApi.util.updateQueryData(k, p, preUpdate(id, params))));
    });
    try {
      const { data } = await api.queryFulfilled;
      queryArgs.forEach(p => {
        api.dispatch(
          trackerApi.util.updateQueryData(k, p, drafts => {
            const e = drafts.findIndex(draft => draft.id === data.id && draft.type === data.type);
            if (e >= 0) {
              drafts[e] = data;
            }
            if (postUpdate) {
              // FIXME: is there a way to make the type system smart enough to know that this is guaranteed to be the same type?
              // eslint-disable-next-line @typescript-eslint/ban-ts-comment
              // @ts-ignore
              postUpdate(data, drafts);
            }
          }),
        );
      });
    } catch {
      patchResults.forEach(p => p.undo());
      if (tags) {
        api.dispatch(trackerApi.util.invalidateTags(tags));
      }
    }
  };
}

function optimisticMultiMutation<T extends StoreModel, MutationArgs extends MutationArgsType>(
  k: CacheKey,
  update: (id: number, a: MutationArgs extends number ? void : Omit<MutationArgs, 'id'>) => (m: T[]) => void,
): TypedMutationOnQueryStarted<T[], MutationArgs, EmptyBaseQuery> {
  return async (args: MutationArgs, api) => {
    const { id, ...rest } = typeof args === 'number' ? { id: args } : { ...args };
    const patchResults: { undo: () => void }[] = [];
    const queryArgs = trackerApi.util.selectCachedArgsForQuery(api.getState(), k);
    queryArgs.forEach(p => {
      // FIXME: is there a way to make the type system smart enough to know that this is guaranteed to be the same type?
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      patchResults.push(api.dispatch(trackerApi.util.updateQueryData(k, p, update(id, rest))));
    });
    try {
      const { data } = await api.queryFulfilled;
      queryArgs.forEach(p => {
        api.dispatch(
          trackerApi.util.updateQueryData(k, p, drafts => {
            data.forEach(d => {
              const e = drafts.findIndex(draft => draft.id === d.id && draft.type === d.type);
              if (e >= 0) {
                drafts[e] = d;
              }
            });
          }),
        );
      });
    } catch {
      patchResults.forEach(p => p.undo());
    }
  };
}

type OptimisticMutation<T extends StoreModel, MutationArgs extends MutationArgsType> = ReturnType<
  typeof optimisticMutation<T, MutationArgs>
>;

function optimisticMutations<T extends StoreModel, MutationArgs extends MutationArgsType>(
  o: OptimisticMutation<T, MutationArgs>[],
): TypedMutationOnQueryStarted<T, MutationArgs, EmptyBaseQuery> {
  return async (args: MutationArgs, api) => {
    await Promise.allSettled(o.map(p => p?.(args, api)));
  };
}

function updateOptionInTree(state: BidState) {
  return (id: number) => {
    return (a: Draft<TreeBid[]>) => {
      const d = a.find(b => b.options?.some(o => o.id === id))?.options?.find(o => o.id === id);
      if (d) {
        d.state = state;
      }
    };
  };
}

function updateFlatOption(state: BidState) {
  return (id: number) => {
    return (a: Draft<FlatBid[]>) => {
      const d = a.find(m => m.id === id);
      if (d) {
        d.state = state;
      }
    };
  };
}

function updateAllBids(state: BidState) {
  return optimisticMutations<FlatBid, number>([
    optimisticMutation<TreeBid, number>('bidTree', updateOptionInTree(state)),
    optimisticMutation<FlatBid, number>('bids', updateFlatOption(state)),
  ]);
}

function patchRun() {
  return optimisticMutation<Run, WithID<RunPatch>>('runs', (id, params) => (runs: Draft<Run[]>) => {
    const draftIndex = runs.findIndex(r => r.id === id);
    if (draftIndex !== -1) {
      const run = runs[draftIndex];
      const { run_time, setup_time, anchor_time, order, event, starttime } = run;
      const old_start_time = starttime;
      const new_anchor_time = parseTime(params.anchor_time !== undefined ? params.anchor_time : anchor_time);
      const new_run_time = parseDuration(params.run_time ?? run_time);
      const new_setup_time = parseDuration(params.setup_time ?? setup_time);

      runs[draftIndex] = {
        ...run,
        starttime: parseTime(params.anchor_time ?? starttime),
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
  return optimisticMultiMutation<Run, WithID<PatchMoveRun>>('runs', (id, args) => (runs: Draft<Run[]>) => {
    const d = runs.find(r => r.id === id);
    if (d) {
      let diff: -1 | 1 | 0 = 0;
      let movingRuns: WritableDraft<Run[]> = [];
      const ordered = runs.filter((r): r is WritableDraft<OrderedRun> => r.order != null);
      let o: OrderedRun | undefined;
      let first: number;
      let last: number | null = null;
      if ('order' in args) {
        const order = args.order === 'last' ? ordered.slice(-1)[0].order + 1 : args.order;
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
        d.order = order;
      } else if ('before' in args || 'after' in args) {
        let target: number;
        if ('before' in args) {
          o = ordered.find(r => r.id === args.before);
          if (o) {
            target = o.order;
          } else {
            throw new Error('invalid target');
          }
        } else {
          o = ordered.find(r => r.id === args.after);
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
        d.order = target;
      } else {
        throw new Error('missing argument');
      }
      movingRuns = ordered.filter(r => r.order >= first && (last == null || r.order < last));
      movingRuns.forEach(m => {
        if (m.order) {
          m.order = m.order + diff;
        }
      });
    }
  });
}

type PatchMoveRun = { before: number } | { after: number } | { order: number | null | 'last' };

enum TagType {
  'me',
  'events',
  'bids',
  'runs',
  'prizes',
  'interviews',
  'ads',
}

export const trackerApi = createApi({
  reducerPath: 'tracker',
  tagTypes: Object.keys(TagType),
  baseQuery: emptyRequest,
  endpoints: build => ({
    me: build.query<Me, void>({
      queryFn: simpleQuery(Endpoints.ME),
      providesTags: ['me'],
    }),
    events: build.query<Event[], { queryParams?: WithPage<EventGet> } | void>({
      queryFn: paginatedQuery(Endpoints.EVENTS, (e: APIEvent): Event => {
        const { datetime, ...rest } = e;
        return {
          datetime: DateTime.fromISO(datetime),
          ...rest,
        };
      }),
      providesTags: ['events'],
    }),
    runs: build.query<Run[], { urlParams?: Parameters<typeof Endpoints.RUNS>[0]; queryParams?: WithPage<RunGet> }>({
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
    bids: build.query<
      FlatBid[],
      {
        urlParams?: WithEvent<Parameters<typeof Endpoints.BIDS>[0]>;
        queryParams?: WithPage<BidGet>;
      }
    >({
      queryFn: paginatedQuery(Endpoints.BIDS, identity<FlatBid>, { tree: false }),
      providesTags: ['bids'],
    }),
    bidTree: build.query<
      TreeBid[],
      {
        urlParams?: WithEvent<Parameters<typeof Endpoints.BIDS>[0]>;
        queryParams?: WithPage<BidGet>;
      }
    >({
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
    prizes: build.query<
      Prize[],
      { urlParams?: Parameters<typeof Endpoints.PRIZES>[0]; queryParams?: WithPage<PrizeGet> }
    >({
      queryFn: paginatedQuery(Endpoints.PRIZES, processPrize),
      providesTags: ['prizes'],
    }),
    interviews: build.query<
      Interview[],
      {
        urlParams?: WithEvent<Parameters<typeof Endpoints.INTERVIEWS>[0]>;
        queryParams?: WithPage<InterviewGet>;
      }
    >({
      queryFn: paginatedQuery(Endpoints.INTERVIEWS, processInterstitial<APIInterview, Interview>),
      providesTags: ['interviews'],
    }),
    ads: build.query<
      Ad[],
      {
        urlParams?: WithEvent<Parameters<typeof Endpoints.ADS>[0]>;
        queryParams?: WithPage;
      }
    >({
      queryFn: paginatedQuery(Endpoints.ADS, processInterstitial<APIAd, Ad>),
      providesTags: ['ads'],
    }),
  }),
});

// TODO: do this without a circular reference?
// type CacheKey = Parameters<typeof trackerApi.util.selectCachedArgsForQuery>[1];
type CacheKey = 'bidTree' | 'bids' | 'runs';

export const {
  useMeQuery,
  useLazyMeQuery,
  useEventsQuery,
  useLazyEventsQuery,
  useRunsQuery,
  useLazyRunsQuery,
  usePatchRunMutation,
  useMoveRunMutation,
  useBidsQuery,
  useLazyBidsQuery,
  useBidTreeQuery,
  useLazyBidTreeQuery,
  useApproveBidMutation,
  useDenyBidMutation,
  usePrizesQuery,
  useLazyPrizesQuery,
  useInterviewsQuery,
  useLazyInterviewsQuery,
  useAdsQuery,
  useLazyAdsQuery,
} = trackerApi;

interface RootShape {
  root: string;
  limit: number;
  csrfToken: string;
}

export const apiRootSlice = createSlice({
  name: 'apiRoot',
  initialState: { root: '', limit: 0, csrfToken: '' },
  reducers: {
    setRoot(_, action: PayloadAction<RootShape>) {
      return action.payload;
    },
  },
});

export const { setRoot } = apiRootSlice.actions;
