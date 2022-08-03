import React, { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useParams } from 'react-router';

import { useConstants } from '@common/Constants';
import ModelErrors from '@common/ModelErrors';
import modelActions from '@public/api/actions/models';
import { usePermission } from '@public/api/helpers/auth';
import { useCachedCallback } from '@public/hooks/useCachedCallback';
import { useFetchDonors } from '@public/hooks/useFetchDonors';
import Spinner from '@public/spinner';

import styles from './donations.mod.css';

type Mode = 'confirm' | 'regular';
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
  const { event: eventId } = useParams<{ event: string }>();
  const status = useSelector((state: any) => state.status);
  const donations = useSelector((state: any) => state.models.donation);
  const donors = useSelector((state: any) => state.models.donor);
  const event = useSelector((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));
  const dispatch = useDispatch();
  const canApprove = usePermission('tracker.send_to_reader');
  const canEditDonors = usePermission('tracker.change_donor');
  const [partitionId, setPartitionId] = useState(1);
  const [partitionCount, setPartitionCount] = useState(1);
  const [mode, setMode] = useState<Mode>('regular');
  const setProcessingMode = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setMode(e.target.value as Mode);
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
      if (mode === 'confirm') {
        params.readstate = 'FLAGGED';
      } else {
        params.feed = 'toprocess';
      }
      dispatch(modelActions.loadModels('donation', params));
      e?.preventDefault();
    },
    [dispatch, eventId, mode],
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
  const sortedDonations = useMemo(() => {
    return donations
      ? donations
          .filter((donation: any) => donation.pk % partitionCount === partitionId - 1)
          .sort((a: any, b: any) => b.pk - a.pk)
      : [];
  }, [donations, partitionCount, partitionId]);

  return (
    <div>
      <h3>{event?.name}</h3>
      <div className={styles['navbar']}>
        <label>
          Partition ID:{' '}
          <input
            name="partition-id"
            type="number"
            value={partitionId}
            onChange={e => setPartitionId(+e.target.value)}
            min={1}
            max={partitionCount}
          />
        </label>
        <label>
          Partition Count:{' '}
          <input
            name="partition-count"
            type="number"
            value={partitionCount}
            onChange={e => setPartitionCount(+e.target.value)}
            min="1"
          />
        </label>

        {canApprove && !event?.use_one_step_screening && (
          <label>
            Processing Mode
            <select data-test-id="processing-mode" onChange={setProcessingMode} value={mode}>
              <option value="confirm">Confirmation</option>
              <option value="regular">Regular</option>
            </select>
          </label>
        )}
        <button data-test-id="refresh" onClick={fetchDonations}>
          Refresh
        </button>
      </div>
      <ModelErrors />
      <Spinner spinning={status.donation === 'loading'}>
        <table className="table table-condensed table-striped small">
          <tbody>
            {sortedDonations.map((donation: any) => {
              const donor = donors?.find((d: any) => d.pk === donation.donor);
              const donorLabel = donor?.alias ? `${donor.alias}#${donor.alias_num}` : '(Anonymous)';

              return (
                <tr key={donation.pk} data-test-pk={donation.pk}>
                  <td>
                    {canEditDonors ? <a href={`${ADMIN_ROOT}donor/${donation.donor}`}>{donorLabel}</a> : donorLabel}
                  </td>
                  <td>
                    <a href={`${ADMIN_ROOT}donation/${donation.pk}`}>&yen;{(+donation.amount).toFixed(0)}</a>
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
