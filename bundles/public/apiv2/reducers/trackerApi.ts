import type { AxiosError, AxiosRequestConfig } from 'axios';
import { current, Draft, freeze, isDraft, original, WritableDraft } from 'immer';
import { DateTime, Duration } from 'luxon';
import { useParams } from 'react-router';
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { BaseQueryApi, QueryReturnValue, TypedMutationOnQueryStarted } from '@reduxjs/toolkit/query';
import { createApi } from '@reduxjs/toolkit/query/react';

import {
  APIEvent,
  APIModel,
  APIRun,
  BidGet,
  EventGet,
  FlatBid,
  Me,
  PaginationInfo,
  RunGet,
  TreeBid,
} from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { BidState, Event, OrderedRun, Run, RunBase } from '@public/apiv2/Models';

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

function paginatedQuery<T, AT extends APIModel, URLParams, QueryParams>(
  urlOrFunc: (URLParams extends unknown ? string : never) | ((r?: URLParams) => string),
  map: (r: AT, i: number, a: AT[], e?: URLParams) => T,
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

function mutation<T, PatchArgs = void>(urlFunc: (r: number) => string): SingleMutation<T, PatchArgs> {
  return async (args, api): SingleQueryPromise<T> => {
    let id: number;
    let params: PatchArgs | void;
    if (typeof args === 'object') {
      const { id: idd, ...paramss } = args;
      id = idd;
      params = paramss as PatchArgs;
    } else {
      id = args;
    }
    const url = urlFunc(id);
    const csrfToken = getCSRFToken(api);
    const result = await axiosRequest<T>(getRoot(api), {
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
      return { data: result.data };
    }
  };
}

type MutationArgsType = number | { id: number };

function optimisticMutation<T extends APIModel, MutationArgs extends MutationArgsType>(
  k: CacheKey,
  update: (id: number) => (m: T[]) => void,
): TypedMutationOnQueryStarted<T, MutationArgs, EmptyBaseQuery> {
  return async (args: MutationArgs, api) => {
    const id = typeof args === 'number' ? args : args.id;
    const patchResults: { undo: () => void }[] = [];
    const queryArgs = trackerApi.util.selectCachedArgsForQuery(api.getState(), k);
    queryArgs.forEach(p => {
      // FIXME: is there a way to make the type system smart enough to know that this is guaranteed to be the same type?
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      patchResults.push(api.dispatch(trackerApi.util.updateQueryData(k, p, update(id))));
    });
    try {
      await api.queryFulfilled;
    } catch {
      patchResults.forEach(p => p.undo());
    }
  };
}

function optimisticMultiMutation<T, MutationArgs extends MutationArgsType>(
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
      await api.queryFulfilled;
    } catch {
      patchResults.forEach(p => p.undo());
    }
  };
}

type OptimisticMutation<T extends APIModel, MutationArgs extends MutationArgsType> = ReturnType<
  typeof optimisticMutation<T, MutationArgs>
>;

function optimisticMutations<T extends APIModel, MutationArgs extends MutationArgsType>(
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

function moveRun() {
  return optimisticMultiMutation<Run, WithID<PatchMoveRun>>('runs', (id, args) => (runs: Draft<Run[]>) => {
    const d = runs.find(r => r.id === id);
    let diff: -1 | 1 | 0 = 0;
    let movingRuns: WritableDraft<Run[]> = [];
    const ordered = runs
      .filter((r): r is WritableDraft<OrderedRun> => r.order != null)
      .map(r => (isDraft(r) ? original(r) : r) as OrderedRun);
    let o: OrderedRun | undefined;
    let first: number;
    let last: number | null = null;
    if (d) {
      debugger;
      if ('order' in args) {
        if (args.order == null) {
          if (d.order != null) {
            diff = -1;
            o = ordered.find(r => r.order > d.order!);
            if (o) {
              first = o.order;
            }
          }
        } else if (d.order) {
          first = Math.min(d.order, args.order);
          last = Math.max(d.order, args.order);
        } else {
          first = args.order;
        }
        d.order = args.order;
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
      } else {
        throw new Error('missing argument');
      }
      movingRuns = ordered.filter(r => r.order >= first && (last == null || r.order < last));
      movingRuns.forEach(m => {
        m.order! += diff;
      });
    }
  });
}

function parseDuration(s: string): Duration {
  if (!/^(((\d+):)?(([0-5]?\d):))?[0-5]?\d$/.test(s)) {
    throw new Error(`unparseable duration (string mismatch): ${s}`);
  }
  const parts = s.split(':');
  let value: Duration;
  switch (parts.length) {
    case 3:
      value = Duration.fromObject({ hour: +parts[0], minute: +parts[1], second: +parts[2] });
      break;
    case 2:
      value = Duration.fromObject({ minute: +parts[0], second: +parts[1] });
      break;
    case 1:
      value = Duration.fromObject({ second: +parts[0] });
      break;
    default:
      throw new Error(`unparseable duration (wrong number of parts): ${s}`);
  }
  if (!value.isValid) {
    throw new Error(`unparseable duration (invalid duration result): ${s}`);
  }
  return value;
}

type PatchMoveRun = { before: number } | { after: number } | { order: number | null };
export const trackerApi = createApi({
  reducerPath: 'tracker',
  tagTypes: ['me', 'events', 'bids', 'runs'],
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
    runs: build.query<RunBase[], { urlParams?: Parameters<typeof Endpoints.RUNS>[0]; queryParams?: WithPage<RunGet> }>({
      queryFn: paginatedQuery(Endpoints.RUNS, (r: APIRun, _0, _1, u): RunBase => {
        const { event, starttime, endtime, run_time, setup_time, anchor_time, ...rest } = r;
        const eventId = u || event?.id;
        if (eventId == null) {
          throw new Error('no event could be parsed');
        }
        return {
          event: eventId,
          starttime: starttime ? DateTime.fromISO(starttime) : null,
          endtime: endtime ? DateTime.fromISO(endtime) : null,
          run_time: parseDuration(run_time),
          setup_time: parseDuration(setup_time),
          anchor_time: anchor_time ? DateTime.fromISO(anchor_time) : null,
          ...rest,
        };
      }),
      providesTags: ['runs'],
    }),
    moveRun: build.mutation<APIRun[], WithID<PatchMoveRun>>({
      queryFn: mutation<APIRun[], PatchMoveRun>(Endpoints.MOVE_RUN),
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
  }),
});

// TODO: do this without a circular reference?
// type CacheKey = Parameters<typeof trackerApi.util.selectCachedArgsForQuery>[1];
type CacheKey = 'bidTree' | 'bids' | 'runs';

export const {
  useMeQuery,
  useEventsQuery,
  useLazyEventsQuery,
  useRunsQuery,
  useMoveRunMutation,
  useBidsQuery,
  useBidTreeQuery,
  useApproveBidMutation,
  useDenyBidMutation,
} = trackerApi;

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
