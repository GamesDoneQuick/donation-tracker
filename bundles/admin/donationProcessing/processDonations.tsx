import React, { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useParams } from 'react-router';
import modelActions from '../../public/api/actions/models';
import { usePermission } from '../../public/api/helpers/auth';
import { useConstants } from '../../common/Constants';
import Spinner from '../../public/spinner';

import styles from './donations.mod.css';
import { useCachedCallback } from '../../public/hooks/useCachedCallback';
import { useFetchDonors } from '../../public/hooks/useFetchDonors';

type Action = 'approved' | 'sent' | 'blocked';

interface State {
  [k: number]: Action;
}

function reducer(state: State, { pk, action }: { pk: number; action: Action }) {
  return { ...state, [pk]: action };
}

const stateMap = {
  approved: 'Comment Approved',
  sent: 'Comment Sent Up',
  blocked: 'Comment Blocked',
};

export default React.memo(function ProcessDonations() {
  const { ADMIN_ROOT } = useConstants();
  const { event: eventId } = useParams();
  const status = useSelector((state: any) => state.status);
  const donations = useSelector((state: any) => state.models.donation);
  const donors = useSelector((state: any) => state.models.donor);
  const event = useSelector((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));
  const dispatch = useDispatch();
  const canApprove = usePermission('tracker.send_to_reader');
  const canEditDonors = usePermission('tracker.change_donor');
  const [partitionId, setPartitionId] = useState(0);
  const [partitionCount, setPartitionCount] = useState(1);
  const [mode, setMode] = useState<'confirm' | 'regular'>('regular');
  const setProcessingMode = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setMode(e.target.value as 'confirm' | 'regular');
  }, []);
  const secondStep = useMemo(() => {
    return (canApprove && mode === 'confirm') || event?.use_one_step_screening;
  }, [canApprove, mode, event]);
  const fetchDonations = useCallback(
    (e?: React.MouseEvent<HTMLButtonElement>) => {
      const params: any = {
        all_comments: '',
        event: eventId,
      };
      if (secondStep) {
        params.readstate = 'FLAGGED';
      } else {
        params.feed = 'toprocess';
      }
      dispatch(modelActions.loadModels('donation', params));
      e?.preventDefault();
    },
    [dispatch, secondStep, eventId],
  );
  useFetchDonors(eventId);
  useEffect(() => {
    fetchDonations();
  }, [fetchDonations]);
  const [donationState, dispatchState] = useReducer(reducer, {} as State);
  const action = useCachedCallback(
    ({
      pk,
      action,
      readstate,
      commentstate,
    }: {
      pk: number;
      action: Action;
      readstate: string;
      commentstate: string;
    }) => {
      dispatchState({ pk, action });
      dispatch(
        modelActions.saveDraftModels([
          {
            pk: pk,
            fields: { readstate: readstate, commentstate: commentstate },
            type: 'donation',
          },
        ]),
      );
    },
    [dispatch],
  );

  return (
    <div>
      <h3>{event?.name}</h3>
      <div className={styles['navbar']}>
        <label>
          Partition ID:{' '}
          <input
            type="number"
            value={partitionId}
            onChange={e => setPartitionId(+e.target.value)}
            min="0"
            max={partitionCount - 1}
          />
        </label>
        <label>
          Partition Count:{' '}
          <input type="number" value={partitionCount} onChange={e => setPartitionCount(+e.target.value)} min="1" />
        </label>

        {canApprove && !event?.use_one_step_screening && (
          <label>
            Processing Mode
            <select onChange={setProcessingMode} value={mode}>
              <option value="confirm">Confirmation</option>
              <option value="regular">Regular</option>
            </select>
          </label>
        )}
        <button onClick={fetchDonations}>Refresh</button>
      </div>
      <Spinner spinning={status.donation === 'loading'}>
        <table className="table table-condensed table-striped small">
          <tbody>
            {donations
              ?.filter((donation: any) => donation.pk % partitionCount === partitionId)
              .map((donation: any) => {
                const donor = donors.find((d: any) => d.pk === donation.donor);
                const donorLabel = donor?.alias ? `${donor.alias}#${donor.alias_no}` : '(Anonymous)';

                return (
                  <tr key={donation.pk}>
                    <td>
                      {canEditDonors ? <a href={`${ADMIN_ROOT}donor/${donation.donor}`}>{donorLabel}</a> : donorLabel}
                    </td>
                    <td>
                      <a href={`${ADMIN_ROOT}donation/${donation.pk}`}>${(+donation.amount).toFixed(2)}</a>
                    </td>
                    <td className={styles['comment']}>{donation.comment}</td>
                    <td>
                      <button
                        onClick={action({
                          pk: donation.pk,
                          action: 'approved',
                          readstate: 'IGNORED',
                          commentstate: 'APPROVED',
                        })}
                        disabled={donation._internal?.saving}>
                        Approve Comment Only
                      </button>
                      <button
                        onClick={action({
                          pk: donation.pk,
                          action: 'sent',
                          readstate: secondStep ? 'READY' : 'FLAGGED',
                          commentstate: 'APPROVED',
                        })}
                        disabled={donation._internal?.saving}>
                        {secondStep ? 'Send to Reader' : 'Send to Head'}
                      </button>
                      <button
                        onClick={action({
                          pk: donation.pk,
                          action: 'blocked',
                          readstate: 'IGNORED',
                          commentstate: 'DENIED',
                        })}
                        disabled={donation._internal?.saving}>
                        Block Comment
                      </button>
                    </td>
                    <td className={styles['status']}>
                      <Spinner spinning={!!donation._internal?.saving}>
                        {donationState[donation.pk] && stateMap[donationState[donation.pk]]}
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
