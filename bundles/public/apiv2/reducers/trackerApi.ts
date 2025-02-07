import type { AxiosError, AxiosRequestConfig } from 'axios';
import { Draft } from 'immer';
import { DateTime } from 'luxon';
import { useParams } from 'react-router';
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { BaseQueryApi, QueryReturnValue, TypedMutationOnQueryStarted } from '@reduxjs/toolkit/query';
import { createApi } from '@reduxjs/toolkit/query/react';

import { APIEvent, APIModel, BidGet, EventGet, FlatBid, Me, PaginationInfo, TreeBid } from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { BidState, Event } from '@public/apiv2/Models';

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
  map: (r: AT, i: number, a: AT[]) => T,
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
    const url = typeof urlOrFunc === 'string' ? urlOrFunc : urlOrFunc({ ...urlParams, ...extraParams } as URLParams);
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
      return { data: value.data.results.map(map) };
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

export const trackerApi = createApi({
  reducerPath: 'tracker',
  tagTypes: ['me', 'events', 'bids'],
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
type CacheKey = 'bidTree' | 'bids';

export const {
  useMeQuery,
  useEventsQuery,
  useLazyEventsQuery,
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
