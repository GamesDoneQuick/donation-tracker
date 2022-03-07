import React, { useCallback, useEffect, useReducer } from 'react';
import { useParams } from 'react-router';
import { useDispatch, useSelector } from 'react-redux';

import { useConstants } from '@common/Constants';
import modelActions from '@public/api/actions/models';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import { useFetchParents } from '@public/hooks/useFetchParents';
import Spinner from '@public/spinner';

import styles from './donations.mod.css';

type Action = 'accept' | 'deny';

interface State {
  [k: number]: Action;
}

function stateReducer(state: State, { pk, action }: { pk: number; action: Action }) {
  return { ...state, [pk]: action };
}

const stateMap = {
  accept: 'Accepted',
  deny: 'Denied',
};

export default React.memo(function ProcessPendingBids() {
  const { ADMIN_ROOT } = useConstants();
  const { event: eventId } = useParams();
  const status = useSelector((state: any) => state.status);
  const bids = useSelector((state: any) => state.models.bid);
  const event = useSelector((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));
  const dispatch = useDispatch();
  const fetchBids = useCallback(
    (e?: React.MouseEvent<HTMLButtonElement>) => {
      const params = {
        feed: 'pending',
        event: eventId,
      };
      dispatch(modelActions.loadModels('bidtarget', params));
      e?.preventDefault();
    },
    [dispatch, eventId],
  );
  useFetchParents();
  useEffect(() => {
    fetchBids();
  }, [fetchBids]);
  const [bidState, dispatchState] = useReducer(stateReducer, {} as State);
  const action = useCachedCallback(
    ({ pk, action, state }: { pk: number; action: Action; state: string }) => {
      dispatchState({ pk, action });
      dispatch(
        modelActions.saveDraftModels([
          {
            pk: pk,
            fields: { state },
            type: 'bid',
          },
        ]),
      );
    },
    [dispatch],
  );

  return (
    <div>
      <h3>{event?.name}</h3>
      <button onClick={fetchBids}>Refresh</button>
      <Spinner spinning={status.bid === 'loading'}>
        <table className="table table-condensed table-striped small">
          <thead>
            <tr>
              <th>Name</th>
              <th>Parent</th>
              <th>Actions</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {bids
              ?.filter((bid: any) => bid.parent)
              .map((bid: any) => {
                const parent = bids.find((parent: any) => parent.pk === bid.parent);

                return (
                  <tr key={bid.pk}>
                    <td>
                      <a href={`${ADMIN_ROOT}bid/${bid.pk}`}>{bid.name}</a>
                    </td>
                    <td>
                      <a href={`${ADMIN_ROOT}bid/${bid.parent}`}>{parent?.public || 'parent'}</a>
                      {parent?.option_max_length && <> &mdash; Max Option Length: {parent.option_max_length}</>}
                    </td>
                    <td>
                      <button
                        onClick={action({
                          pk: bid.pk,
                          action: 'accept',
                          state: 'OPENED',
                        })}
                        disabled={bid._internal?.saving}>
                        Accept
                      </button>
                      <button
                        onClick={action({
                          pk: bid.pk,
                          action: 'deny',
                          state: 'DENIED',
                        })}
                        disabled={bid._internal?.saving}>
                        Deny
                      </button>
                    </td>
                    <td className={styles['status']}>
                      <Spinner spinning={!!bid._internal?.saving}>
                        {bidState[bid.pk] && stateMap[bidState[bid.pk]]}
                      </Spinner>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </Spinner>
    </div>
  );
});
