import React, { useCallback, useReducer } from 'react';

import { useConstants } from '@common/Constants';
import { usePermission } from '@public/api/helpers/auth';
import APIErrorList from '@public/APIErrorList';
import { BidState } from '@public/apiv2/Models';
import {
  useApproveBidMutation,
  useBidTreeQuery,
  useDenyBidMutation,
  useEventFromQuery,
  useEventParam,
} from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

import styles from './donations.mod.css';

type LocalBidState = BidState | 'SAVING' | 'FAILED';

interface State {
  [k: number]: LocalBidState;
}

function stateReducer(state: State, { id, action }: { id: number; action: null | LocalBidState }) {
  if (action) {
    return { ...state, [id]: action };
  } else {
    const { [id]: _, ...rest } = state;
    return rest;
  }
}

const stateMap: Record<LocalBidState, string> = {
  OPENED: '✅Accepted',
  CLOSED: '✅Accepted',
  HIDDEN: '✅Accepted',
  DENIED: '❌Denied',
  PENDING: '❓Pending',
  SAVING: '💾Saving',
  FAILED: '💥Failure while Saving',
};

export default React.memo(function ProcessPendingBids() {
  const { ADMIN_ROOT } = useConstants();
  const eventId = useEventParam();
  const {
    data: bids,
    error: bidError,
    refetch: refetchBids,
    isLoading: bidLoading,
  } = useBidTreeQuery({
    urlParams: { eventId, feed: 'pending' },
  });
  const { event, error: eventError, isLoading: eventLoading } = useEventFromQuery(eventId);

  const canApproveBids = usePermission('tracker.approve_bid');
  const canChangeBids = usePermission('tracker.change_bid');
  const [approve] = useApproveBidMutation();
  const [deny] = useDenyBidMutation();
  const [bidState, dispatchState] = useReducer(stateReducer, {} as State);
  const action = useCallback(
    async ({ id, action }: { id: number; action: 'accept' | 'deny' }) => {
      dispatchState({ id, action: 'SAVING' });
      try {
        switch (action) {
          case 'accept':
            await approve(id).unwrap();
            break;
          case 'deny':
            await deny(id).unwrap();
            break;
          default:
            throw new Error('what');
        }
        dispatchState({ id, action: null });
      } catch {
        dispatchState({ id, action: 'FAILED' });
      }
    },
    [approve, deny],
  );

  return (
    <div>
      <h3>{event?.name}</h3>
      <button onClick={refetchBids}>Refresh</button>
      <APIErrorList errors={[eventError, bidError]}>
        <Spinner spinning={eventLoading || bidLoading}>
          <table className="table table-condensed table-striped small">
            <thead>
              <tr>
                <th>Name</th>
                {(canApproveBids || canChangeBids) && (
                  <>
                    <th>Actions</th>
                    <th>Status</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {bids?.map(bid => (
                <React.Fragment key={bid.id}>
                  <tr data-test-pk={bid.id}>
                    <td>
                      <a href={`${ADMIN_ROOT}bid/${bid.id}`}>{bid.name}</a>
                    </td>
                    <td colSpan={2}>
                      {bid.allowuseroptions && bid.option_max_length && `Max Option Length: ${bid.option_max_length}`}
                    </td>
                  </tr>
                  {bid.options?.map(c => (
                    <tr key={c.id} data-test-pk={c.id}>
                      <td style={{ paddingLeft: 12 }}>
                        <a href={`${ADMIN_ROOT}bid/${c.id}`}>{c.name}</a>
                      </td>
                      {(canApproveBids || canChangeBids) && (
                        <>
                          <td>
                            {c.state === 'PENDING' && (
                              <>
                                <button
                                  data-test-id="accept"
                                  onClick={() =>
                                    action({
                                      id: c.id,
                                      action: 'accept',
                                    })
                                  }
                                  disabled={bidState[c.id] === 'SAVING'}>
                                  Accept
                                </button>
                                <button
                                  data-test-id="deny"
                                  onClick={() =>
                                    action({
                                      id: c.id,
                                      action: 'deny',
                                    })
                                  }
                                  disabled={bidState[c.id] === 'SAVING'}>
                                  Deny
                                </button>
                              </>
                            )}
                          </td>
                          <td data-test-state={c.state} className={styles['status']}>
                            <Spinner spinning={bidState[c.id] === 'SAVING'}>
                              {bidState[c.id] ? stateMap[bidState[c.id]] : stateMap[c.state]}
                            </Spinner>
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </Spinner>
      </APIErrorList>
    </div>
  );
});
