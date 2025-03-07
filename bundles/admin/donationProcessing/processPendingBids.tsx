import React from 'react';
import cn from 'classnames';

import { useConstants } from '@common/Constants';
import APIErrorList from '@public/APIErrorList';
import { usePermission } from '@public/apiv2/helpers/auth';
import { useEventFromQuery, useEventParam } from '@public/apiv2/hooks';
import { BidState } from '@public/apiv2/Models';
import { useApproveBidMutation, useBidTreeQuery, useDenyBidMutation } from '@public/apiv2/reducers/trackerApi';
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

const stateIcon: Record<LocalBidState, string> = {
  OPENED: 'fa-check',
  CLOSED: 'fa-check',
  HIDDEN: 'fa-check',
  DENIED: 'fa-times',
  PENDING: 'fa-question',
  SAVING: 'fa-save',
  FAILED: 'fa-warning',
};

const stateMap: Record<LocalBidState, string> = {
  OPENED: 'Accepted',
  CLOSED: 'Accepted',
  HIDDEN: 'Accepted',
  DENIED: 'Denied',
  PENDING: 'Pending',
  SAVING: 'Saving',
  FAILED: 'Failure while Saving',
};

export default React.memo(function ProcessPendingBids() {
  const { ADMIN_ROOT } = useConstants();
  const eventId = useEventParam();
  const {
    data: bids,
    error: bidError,
    refetch: refetchBids,
    isFetching: bidFetching,
  } = useBidTreeQuery({
    urlParams: { eventId, feed: 'pending' },
  });
  const { data: event, error: eventError, isLoading: eventLoading } = useEventFromQuery(eventId);

  const canApproveBids = usePermission('tracker.approve_bid');
  const canChangeBids = usePermission('tracker.change_bid');
  const [approve, approveState] = useApproveBidMutation();
  const [deny, denyState] = useDenyBidMutation();
  const [bidState, dispatchState] = React.useReducer(stateReducer, {} as State);
  const action = React.useCallback(
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
  const refetch = React.useCallback(() => {
    refetchBids();
    approveState.reset();
    denyState.reset();
  }, [approveState, denyState, refetchBids]);

  return (
    <div>
      <h3>{event?.name}</h3>
      <div>
        <button onClick={refetch}>Refresh</button>
      </div>
      <APIErrorList errors={[eventError, bidError]}>
        <APIErrorList errors={[approveState.error, denyState.error]} />
        <Spinner spinning={eventLoading || bidFetching} showPartial={bids != null}>
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
                          <td data-test-state={bidState[c.id] ?? c.state} className={styles['status']}>
                            <span className={cn('fa', stateIcon[bidState[c.id] ?? c.state])}>
                              {stateMap[bidState[c.id] ?? c.state]}
                            </span>
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
