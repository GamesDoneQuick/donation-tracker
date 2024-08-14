import { DateTime, Duration } from 'luxon';

import { SafeDispatch } from '@public/api/useDispatch';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { Bid, Model, ModelType, Run } from '@public/apiv2/Models';

export type BidFeed = 'pending' | 'all' | 'public' | 'current' | 'open' | 'closed';

type PartialWithId<T> = Partial<T> & { id: number };

// TODO: partially copied from V1

function onModelStatusLoad(model: ModelType) {
  return {
    type: 'MODEL_STATUS_LOADING',
    model,
  };
}

function onModelStatusSuccess(model: ModelType) {
  return {
    type: 'MODEL_STATUS_SUCCESS',
    model,
  };
}

function onModelStatusError(model: ModelType) {
  return {
    type: 'MODEL_STATUS_ERROR',
    model,
  };
}

function onModelCollectionReplace(model: ModelType, models: Model[]) {
  return {
    type: 'MODEL_COLLECTION_REPLACE',
    model,
    models,
  };
}

function onModelCollectionAdd(model: ModelType, models: Model[]) {
  return {
    type: 'MODEL_COLLECTION_ADD',
    model,
    models,
  };
}

export function parseTime(timestamp: string): DateTime {
  const result = DateTime.fromISO(timestamp);
  // eslint-disable-next-line no-console
  console.debug(result.toFormat('cccc')); // cache immutability error, see https://github.com/moment/luxon/issues/323
  return result;
}

export function parseDuration(duration: string): Duration {
  const pattern = /(\d+)(:(\d{2}))*/;
  if (!pattern.test(duration)) {
    throw new Error(`duration string did not follow expected format: ${duration}`);
  }
  const match = duration.split(':');
  let result: Duration;
  switch (match.length) {
    case 3: {
      const [hours, minutes, seconds] = match.map(m => +m);
      if (minutes > 59 || seconds > 59) {
        throw new Error(`duration string did not follow expected format: ${duration}`);
      }
      result = Duration.fromObject({
        hours,
        minutes,
        seconds,
      });
      break;
    }
    case 2: {
      const [minutes, seconds] = match.map(m => +m);
      if (minutes > 59 || seconds > 59) {
        throw new Error(`duration string did not follow expected format: ${duration}`);
      }
      result = Duration.fromObject({
        minutes,
        seconds,
      });
      break;
    }
    case 1: {
      const seconds = +match[0];
      if (seconds > 59) {
        throw new Error(`duration string did not follow expected format: ${duration}`);
      }
      result = Duration.fromObject({
        seconds,
      });
      break;
    }
    default:
      throw new Error(`duration string did not follow expected format: ${duration}`);
  }
  // eslint-disable-next-line no-console
  console.debug(result.toHuman()); // cache immutability error, see https://github.com/moment/luxon/issues/323
  return result;
}

interface APIData<APIModel extends Model> {
  count: number;
  previous: string | null;
  next: string | null;
  results: APIModel[];
}

function processResponse<APIModel extends Model>(
  modelName: ModelType,
  endpoint: string,
  params: object,
  additive: boolean,
  paginate: boolean,
  conversion?: (model: any) => APIModel,
) {
  return async (dispatch: SafeDispatch) => {
    dispatch(onModelStatusLoad(modelName));
    try {
      let models: APIModel[] = [];
      if (paginate) {
        let next: string | null = endpoint;
        do {
          // FIXME: not entirely sure why this needs an explicit type when the non-paginated version doesn't - BCC 2024/08/14
          const data: APIData<APIModel> = (await HTTPUtils.get<APIData<APIModel>>(next, params)).data;
          next = data.next;
          models.concat(data.results);
        } while (next != null);
      } else {
        models = (await HTTPUtils.get<APIData<APIModel>>(endpoint, params)).data.results;
      }
      if (conversion) {
        models = models.map(conversion);
      }
      const action = additive ? onModelCollectionAdd : onModelCollectionReplace;
      dispatch(action(modelName, models));
      dispatch(onModelStatusSuccess(modelName));
      return models;
    } catch (error) {
      if (!additive) {
        dispatch(onModelCollectionReplace(modelName, []));
      }
      dispatch(onModelStatusError(modelName));
      throw error;
    }
  };
}

function loadRuns(
  { eventId, includeUnordered, id }: { eventId?: number; includeUnordered?: boolean; id?: number | number[] },
  { additive = id != null, paginate = false }: { additive?: boolean; paginate?: boolean } = {},
) {
  return processResponse<Run>(
    'run',
    Endpoints.RUNS(eventId),
    { id, unordered: includeUnordered ? true : null },
    additive,
    paginate,
    (model: any): Run => ({
      ...(model as Run),
      event: eventId || model.event.id,
      starttime: parseTime(model.starttime),
      endtime: parseTime(model.endtime),
      run_time: parseDuration(model.run_time),
      setup_time: parseDuration(model.setup_time),
      anchor_time: model.anchor_time && parseTime(model.anchor_time),
    }),
  );
}

function loadBids(
  { eventId, feed, id, tree }: { eventId?: number; feed?: BidFeed; id?: number | number[]; tree?: boolean },
  { additive = id != null, paginate = false }: { additive?: boolean; paginate?: boolean } = {},
) {
  return processResponse<Bid>('bid', Endpoints.BIDS(eventId, feed, tree), { id }, additive, paginate);
}

function patchBid(data: PartialWithId<Bid>) {
  return async (dispatch: SafeDispatch) => {
    const { id, ...rest } = data;
    const { data: model } = await HTTPUtils.patch<Bid>(Endpoints.BID(id), rest);
    dispatch(onModelCollectionAdd('bid', [model]));
  };
}

function approveBid(id: number) {
  return async (dispatch: SafeDispatch) => {
    await HTTPUtils.patch<Bid>(Endpoints.APPROVE_BID(id));
  };
}

function denyBid(id: number) {
  return async (dispatch: SafeDispatch) => {
    await HTTPUtils.patch<Bid>(Endpoints.DENY_BID(id));
  };
}

export default {
  loadRuns,
  loadBids,
  patchBid,
  approveBid,
  denyBid,
};
