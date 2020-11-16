import modelActions from '../api/actions/models';
import { useSelector, useDispatch } from 'react-redux';
import * as React from 'react';

export function useFetchDonors(eventId: number | string | undefined) {
  const { donation: donations, donor: donors } = useSelector((state: any) => state.models);
  const { donor: donorStatus } = useSelector((state: any) => state.status);
  const dispatch = useDispatch();
  const [timeoutId, setTimeoutId] = React.useState<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => {
    if (!timeoutId && donorStatus !== 'loading') {
      setTimeoutId(
        setTimeout(() => {
          if (!donors && eventId != null) {
            dispatch(modelActions.loadModels('donor', { event: +eventId }));
          } else if (donations) {
            const ids = new Set(
              donations
                .filter(
                  (dn: any) =>
                    dn.donor && dn.donor__visibility !== 'ANON' && !donors?.find((dr: any) => dr.pk === dn.donor),
                )
                .map((dn: any) => dn.donor),
            );
            if (ids.size) {
              dispatch(modelActions.loadModels('donor', { ids: [...ids.values()].join(',') }, true));
            }
          }
          setTimeoutId(null);
        }, 0),
      );
    }
  }, [dispatch, donations, donors, donorStatus, eventId, timeoutId]);
}
