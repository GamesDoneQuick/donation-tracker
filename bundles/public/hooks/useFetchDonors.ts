import modelActions from '../api/actions/models';
import { useSelector, useDispatch } from 'react-redux';
import { useEffect } from 'react';

export function useFetchDonors(eventId: number | string | undefined) {
  const donations = useSelector((state: any) => state.models.donation);
  const donors = useSelector((state: any) => state.models.donor);
  const dispatch = useDispatch();

  useEffect(() => {
    if (!donors && eventId != null) {
      dispatch(modelActions.loadModels('donor', { event: +eventId }));
    } else if (donations) {
      donations.forEach((donation: any) => {
        if (!donors[donation.donor]) {
          dispatch(modelActions.loadModels('donor', { pk: donation.donor }, true));
        }
      });
    }
  }, [dispatch, donations, donors, eventId]);
}
