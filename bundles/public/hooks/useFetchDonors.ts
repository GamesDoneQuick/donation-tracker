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
      const ids = new Set(
        donations
          .filter(
            (dn: any) => dn.donor && dn.donor__visibility !== 'ANON' && !donors?.find((dr: any) => dr.pk === dn.donor),
          )
          .map((dn: any) => dn.donor),
      );
      if (ids.size) {
        dispatch(modelActions.loadModels('donor', { ids: [...ids.values()].join(',') }, true));
      }
    }
  }, [dispatch, donations, donors, eventId]);
}
