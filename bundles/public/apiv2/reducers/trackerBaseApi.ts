import { AxiosError, AxiosRequestConfig, AxiosResponse, Method } from 'axios';
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import {
  BaseQueryApi,
  DefinitionsFromApi,
  DefinitionType,
  InfiniteData,
  InfiniteQueryArgFrom,
  InfiniteQueryConfigOptions,
  PageParamFrom,
  QueryArgFrom,
  QueryReturnValue,
  ResultTypeFrom,
  TagDescription,
} from '@reduxjs/toolkit/query';
import { createApi } from '@reduxjs/toolkit/query/react';

import {
  APIAd,
  APIInterview,
  APIModel,
  APIRun,
  BidGet,
  DonationGet,
  DonationPost,
  EventGet,
  FlatBid,
  InterviewGet,
  Me,
  MilestoneGet,
  PaginationInfo,
  PrizeGet,
  RunGet,
  RunPatch,
  TreeBid,
} from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { Ad, Donation, Event, Interview, Milestone, Prize, Run } from '@public/apiv2/Models';
import {
  processDonation,
  processEvent,
  processInterstitial,
  processMilestone,
  processPrize,
  processRun,
} from '@public/apiv2/Processors';
import { MaybeEmpty, MaybeObject } from '@public/apiv2/reducers/types';
import { MaybeArray } from '@public/util/Types';

import { getRoot, RootShape } from './apiRoot';

export type RecursiveRecord = { [k: string]: string | string[] | RecursiveRecord | RecursiveRecord[] };

export type APIError = {
  statusText?: string;
} & (
  | {
      status: 400;
      data: RecursiveRecord;
    }
  | {
      status?: number;
      data?: unknown;
    }
);

const internal = Symbol('tracker_internal');

interface PageInfoState {
  [k: string]: {
    count: number;
    age: number;
  };
}

const pageInfo = createSlice({
  name: 'pageInfo',
  initialState: (): PageInfoState => ({}),
  reducers: {
    add(state, { payload: [i, key, count] }: PayloadAction<[typeof internal, string, number]>) {
      if (i !== internal) {
        throw new Error('internal use only');
      }
      state[key] = { count, age: new Date().valueOf() };
    },
  },
});

// actions are internal use only

export const { reducerPath: pageInfoReducerPath, reducer: pageInfoReducer } = pageInfo;

const empty = Symbol('empty');

function emptyRequest() {
  return axiosRequest<void>(empty, {});
}

export type EmptyBaseQuery = typeof emptyRequest;

type AxiosMeta = {
  config?: Omit<AxiosRequestConfig, 'paramsSerializer'>;
  response?: Omit<AxiosResponse<unknown>, 'config' | 'data' | 'request'>;
};

async function axiosRequest<T>(
  baseURL: string | undefined | typeof empty,
  config: Omit<AxiosRequestConfig, 'baseURL' | 'paramsSerializer'>,
): Promise<QueryReturnValue<T, APIError, AxiosMeta>> {
  if (baseURL === empty) {
    return {
      error: {
        status: 400,
        statusText: 'Bad Request',
        data: 'Empty request',
      },
      meta: { config },
    };
  } else if (!baseURL) {
    return {
      error: {
        status: 400,
        statusText: 'Bad Request',
        data: 'No API root set',
      },
      meta: { config },
    };
  } else {
    try {
      const {
        config: _c,
        request: _r,
        ...response
      } = await HTTPUtils.request<T>({
        ...config,
        baseURL,
        paramsSerializer: { indexes: null },
      });

      return {
        data: response.data,
        meta: { config: { ...config, baseURL }, response },
      };
    } catch (axiosError) {
      const err = axiosError as AxiosError<T>;
      return {
        error: {
          status: err.response?.status,
          statusText: err.message,
          data: err.response?.data,
        },
        meta: { config: { ...config, baseURL }, response: err.response },
      };
    }
  }
}

type WithID<T> = { id: number } & T;
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

function identity<T>(r: T): T {
  return r;
}

type SingleQueryPromise<T> = Promise<QueryReturnValue<T, APIError, AxiosMeta>>;
type MultiQueryPromise<T> = Promise<QueryReturnValue<T[], APIError, AxiosMeta>>;
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
type InfiniteQueryPromise<T> = Promise<QueryReturnValue<PaginationInfo<T>, APIError, AxiosMeta>>;
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
export type PageOrInfinite<T> = T[] | InfiniteData<PaginationInfo<T>, number>;

function getCSRFToken(api: { getState: () => unknown }): string {
  const csrfToken = (api.getState() as { apiRoot?: RootShape })?.apiRoot?.csrfToken;
  if (csrfToken == null) {
    throw new Error('insanity');
  }
  return csrfToken;
}

export function getLimit(api: { getState: () => unknown }): number {
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
  let maybeParams: URLParams | undefined | void;
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
  return async (params, api) => {
    const [url, queryParams] = urlAndParams(urlOrFunc, params);
    const csrfToken = getCSRFToken(api);
    const { data, error, meta } = await axiosRequest<T>(getRoot(api), {
      url,
      method,
      params: queryParams,
      headers: ['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase()) ? {} : { 'X-CSRFToken': csrfToken },
    });

    if (error) {
      return { error, meta };
    } else {
      return { data, meta };
    }
  };
}

async function fetchPage<AT extends APIModel>(
  url: string,
  params: AxiosRequestConfig['params'],
  api: BaseQueryApi,
  pageParams: PageParams,
): Promise<QueryReturnValue<PaginationInfo<AT>, APIError, AxiosMeta>> {
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
  if (params != null && ('page' in params || 'limit' in params || 'offset' in params)) {
    return { error: { status: 400, statusText: 'Bad Request', data: 'Page parameters in QueryParams' } };
  }
  const limit = getLimit(api);
  if (pageParams.page != null) {
    if (pageParams.page < 1) {
      return { error: { status: 400, statusText: 'Bad Request', data: 'Invalid page number' } };
    }
    if (pageParams.limit != null) {
      if (pageParams.limit < 1 || pageParams.limit > limit) {
        return { error: { status: 400, statusText: 'Bad Request', data: 'Invalid limit parameter' } };
      }
    }
    const { pageInfo: info } = api.getState() as { pageInfo: PageInfoState };
    let count = info[key]?.count ?? 0;
    if (pageParams.page > 1) {
      // refetch if it is more than 5 minutes old
      const age = info[key]?.age ?? 0;
      if (age < new Date().valueOf() - 300000) {
        const newInfo = await axiosRequest<PaginationInfo<AT>>(getRoot(api), {
          url: url,
          params: { limit: 0, ...params },
        });
        if (newInfo.error) {
          return { error: newInfo.error, meta: newInfo.meta };
        }
        api.dispatch(pageInfo.actions.add([internal, key, newInfo.data.count]));
        count = newInfo.data.count;
      }
      offset = limit * (pageParams.page - 1);
    }
    const numPages = Math.max(Math.ceil(count / (pageParams.limit || limit)), 1);
    if (pageParams.page > numPages) {
      return { error: { status: 404, statusText: 'Not Found', data: 'Page does not exist' } };
    }
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
  return async ({ queryArg: { urlParams, queryParams }, pageParam }, api) => {
    const [url, finalParams] = urlAndParams(urlOrFunc, { urlParams, queryParams }, extraParams);
    const { data, error, meta } = await fetchPage<AT>(url, finalParams, api, { page: pageParam });
    if (data) {
      const { results, ...rest } = data;
      return {
        data: {
          ...rest,
          results: results.map((m, i, a) => map(m, i, a, urlParams)),
        },
        meta,
      };
    } else {
      return {
        error,
        meta,
      };
    }
  };
}

function paginatedQuery<T, AT extends APIModel, URLParams, QueryParams>(
  urlOrFunc: URLOrFunc<URLParams>,
  map: MapFunc<T, AT, URLParams>,
  extraParams?: URLParams extends object ? URLParams : never,
): PageQuery<T, URLParams, QueryParams> {
  return async ({ urlParams, queryParams } = {}, api) => {
    const { page: pageParam, ...rest } = queryParams ? queryParams : { page: 1 };
    const [url, finalParams] = urlAndParams(urlOrFunc, { urlParams, queryParams: rest }, extraParams);
    const { data, error, meta } = await fetchPage<AT>(url, finalParams, api, { page: pageParam });
    if (data) {
      return {
        data: data.results.map((m, i, a) => map(m, i, a, urlParams)),
        meta,
      };
    } else {
      return { error, meta };
    }
  };
}

function mutation<T, PatchArgs = void, AT extends APIModel = T extends APIModel ? T : never>(
  urlFunc: (r: number) => string,
  map: SimpleMapFunc<T, AT>,
  method?: Method,
): SingleMutation<T, PatchArgs> {
  return async (args, api): SingleQueryPromise<T> => {
    const { id, ...params } = typeof args === 'object' ? { ...args } : { id: args };
    const url = urlFunc(id);
    const csrfToken = getCSRFToken(api);
    const { data, error, meta } = await axiosRequest<AT>(getRoot(api), {
      url,
      method: method ?? 'PATCH',
      data: params,
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });
    if (error) {
      return { error, meta };
    } else {
      return { data: map ? map(data, 0, [data]) : (data as unknown as T), meta };
    }
  };
}

// TODO: can this be unified into mutation?

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
    const { data, error, meta } = await axiosRequest<AT[]>(getRoot(api), {
      url,
      method: 'patch',
      data: params,
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });
    if (error) {
      return { error, meta };
    } else {
      return { data: map ? data.map(map) : (data as unknown as T[]), meta };
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

export type Tags = MaybeArray<TagDescription<keyof typeof TagType>>;
export type EventQuery = WithListen<{ queryParams?: WithPage<EventGet> }>;
export type RunQuery = { urlParams?: Parameters<typeof Endpoints.RUNS>[0]; queryParams?: WithPage<RunGet> };
export type BidQuery = WithListen<{
  urlParams?: Parameters<typeof Endpoints.BIDS>[0];
  queryParams?: WithPage<BidGet>;
}>;
export type DonationQuery = WithListen<{
  urlParams?: Parameters<typeof Endpoints.DONATIONS>[0];
  queryParams?: WithPage<DonationGet>;
}>;
export type DonationGroupQuery = WithListen;
export type MilestoneQuery = {
  urlParams?: Parameters<typeof Endpoints.MILESTONES>[0];
  queryParams?: WithPage<MilestoneGet>;
};
export type PrizeQuery = { urlParams?: Parameters<typeof Endpoints.PRIZES>[0]; queryParams?: WithPage<PrizeGet> };
export type InterviewQuery = {
  urlParams?: Parameters<typeof Endpoints.INTERVIEWS>[0];
  queryParams?: WithPage<InterviewGet>;
};
export type AdQuery = {
  urlParams?: Parameters<typeof Endpoints.ADS>[0];
  queryParams?: WithPage;
};

const infiniteQueryOptions: InfiniteQueryConfigOptions<PaginationInfo<unknown>, number> = {
  initialPageParam: 1,
  getNextPageParam: (
    lastPage: PaginationInfo<unknown>,
    allPages: Array<PaginationInfo<unknown>>,
    lastPageParam: number,
    allPageParams: number[],
  ) => (lastPage.next != null ? lastPageParam + 1 : undefined),
  getPreviousPageParam: (
    firstPage: PaginationInfo<unknown>,
    allPages: Array<PaginationInfo<unknown>>,
    firstPageParam: number,
    allPageParams: number[],
  ) => (firstPage.previous != null ? firstPageParam - 1 : undefined),
};

export type PatchMoveRun = { before: number } | { after: number } | { order: number | null | 'last' };

// base API for endpoint typing, without any fancy lifecycle additions

export const trackerBaseApi = createApi({
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
    }),
    runs: build.query<Run[], RunQuery | void>({
      queryFn: paginatedQuery(Endpoints.RUNS, processRun),
      providesTags: ['runs'],
    }),
    // use moveRun for order
    patchRun: build.mutation<Run, Omit<WithID<RunPatch>, 'order'>>({
      queryFn: mutation<Run, Omit<RunPatch, 'order'>, APIRun>(Endpoints.RUN, processRun),
    }),
    moveRun: build.mutation<Run[], WithID<PatchMoveRun>>({
      queryFn: multiMutation<Run, PatchMoveRun, APIRun>(Endpoints.MOVE_RUN, processRun),
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
      queryFn: simpleQuery(Endpoints.APPROVE_BID, 'PATCH'),
    }),
    denyBid: build.mutation<FlatBid, number>({
      queryFn: simpleQuery(Endpoints.DENY_BID, 'PATCH'),
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
    }),
    createDonationGroup: build.mutation<string, string>({
      queryFn: simpleQuery(Endpoints.DONATION_GROUP, 'PUT'),
    }),
    deleteDonationGroup: build.mutation<void, string>({
      queryFn: simpleQuery(Endpoints.DONATION_GROUP, 'DELETE'),
    }),
    donations: build.query<Donation[], DonationQuery | void>({
      queryFn: paginatedQuery(Endpoints.DONATIONS, processDonation),
      providesTags: ['donations'],
    }),
    allDonations: build.infiniteQuery<PaginationInfo<Donation>, WithoutPage<DonationQuery> | void, number>({
      queryFn: infiniteQuery(Endpoints.DONATIONS, processDonation),
      providesTags: ['donations'],
      infiniteQueryOptions,
    }),
    donatePreflight: build.query<void, void>({
      // ensures that the session cookie etc. is set
      queryFn: simpleQuery('/donate/'),
    }),
    donate: build.mutation<{ confirm_url: string }, DonationPost>({
      queryFn: mutation(() => '/donate/', identity, 'POST'),
    }),
    unprocessDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_UNPROCESS, processDonation),
    }),
    approveDonationComment: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_APPROVE_COMMENT, processDonation),
    }),
    denyDonationComment: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_DENY_COMMENT, processDonation),
    }),
    flagDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_FLAG, processDonation),
    }),
    sendDonationToReader: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_SEND_TO_READER, processDonation),
    }),
    pinDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_PIN, processDonation),
    }),
    unpinDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_UNPIN, processDonation),
    }),
    readDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_READ, processDonation),
    }),
    ignoreDonation: build.mutation<Donation, number>({
      queryFn: mutation(Endpoints.DONATIONS_IGNORE, processDonation),
    }),
    editDonationComment: build.mutation<Donation, WithID<{ comment: string }>>({
      queryFn: mutation(Endpoints.DONATIONS_COMMENT, processDonation),
    }),
    addDonationToGroup: build.mutation<string[], Parameters<typeof Endpoints.DONATIONS_GROUPS>[0]>({
      queryFn: simpleQuery(Endpoints.DONATIONS_GROUPS, 'PATCH'),
    }),
    removeDonationFromGroup: build.mutation<string[], Parameters<typeof Endpoints.DONATIONS_GROUPS>[0]>({
      queryFn: simpleQuery(Endpoints.DONATIONS_GROUPS, 'DELETE'),
    }),
  }),
  refetchOnReconnect: true,
});

export type TrackerApiEndpointDefinitions = DefinitionsFromApi<typeof trackerBaseApi>;

export type TrackerApiQueryEndpoints = {
  [K in keyof TrackerApiEndpointDefinitions as TrackerApiEndpointDefinitions[K] extends {
    type: DefinitionType.query;
  }
    ? K
    : never]: TrackerApiEndpointDefinitions[K];
};
export type TrackerApiInfiniteQueryEndpoints = {
  [K in keyof TrackerApiEndpointDefinitions as TrackerApiEndpointDefinitions[K] extends {
    type: DefinitionType.infinitequery;
  }
    ? K
    : never]: TrackerApiEndpointDefinitions[K];
};
export type TrackerApiMutationEndpoints = {
  [K in keyof TrackerApiEndpointDefinitions as TrackerApiEndpointDefinitions[K] extends {
    type: DefinitionType.mutation;
  }
    ? K
    : never]: TrackerApiEndpointDefinitions[K];
};
export type TrackerApiQueryArgument<K extends keyof TrackerApiEndpointDefinitions> =
  K extends keyof TrackerApiQueryEndpoints
    ? QueryArgFrom<TrackerApiQueryEndpoints[K]>
    : K extends keyof TrackerApiInfiniteQueryEndpoints
      ? InfiniteQueryArgFrom<TrackerApiInfiniteQueryEndpoints[K]>
      : never;
export type TrackerApiQueryData<K extends keyof TrackerApiEndpointDefinitions> =
  K extends keyof TrackerApiQueryEndpoints
    ? ResultTypeFrom<TrackerApiQueryEndpoints[K]>
    : K extends keyof TrackerApiInfiniteQueryEndpoints
      ? InfiniteData<
          ResultTypeFrom<TrackerApiInfiniteQueryEndpoints[K]>,
          PageParamFrom<TrackerApiInfiniteQueryEndpoints[K]>
        >
      : never;
