import { add } from 'lodash';

import { SafeDispatch } from '@public/api/useDispatch';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { Bid, Model, ModelType } from '@public/apiv2/Models';

export type BidFeed = 'pending' | 'all' | 'current' | 'open' | 'closed';

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

function loadBids(
  { eventId, feed, id, tree }: { eventId?: number; feed?: BidFeed; id?: number[]; tree?: boolean },
  additive = false,
) {
  if (tree == null && feed !== 'pending') {
    tree = true;
  }
  return async (dispatch: SafeDispatch) => {
    dispatch(onModelStatusLoad('bid'));
    try {
      const models = (await HTTPUtils.get<{ results: Bid[] }>(Endpoints.BIDS(eventId, feed, tree), { id })).data
        .results;
      const action = additive ? onModelCollectionAdd : onModelCollectionReplace;
      dispatch(action('bid', models));
      dispatch(onModelStatusSuccess('bid'));
      return models;
    } catch (error) {
      if (!additive) {
        dispatch(onModelCollectionReplace('bid', []));
      }
      dispatch(onModelStatusError('bid'));
      throw error;
    }
  };
}

function patchBid(data: PartialWithId<Bid>) {
  return async (dispatch: SafeDispatch) => {
    const { id, ...rest } = data;
    const { data: model } = await HTTPUtils.patch<Bid>(Endpoints.BID(id), rest);
    dispatch(onModelCollectionAdd('bid', [model]));
  };
}

export default {
  loadBids,
  patchBid,
};
