import { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';

import useSafeDispatch from '@public/api/useDispatch';
import modelV2Actions from '@public/apiv2/actions/models';
import { Bid } from '@public/apiv2/Models';

export function useFetchParents() {
  const bids = useSelector((state: any) => state.models.bid) as Bid[] | undefined;
  const dispatch = useSafeDispatch();
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const failedParents = useRef(new Set<number>());

  useEffect(() => {
    if (bids) {
      const parentIds = new Set<number>(
        bids
          .filter(b => b.parent && !bids.find(p => p.id === b.parent) && !failedParents.current.has(b.parent))
          .map(b => b.parent!),
      );
      if (parentIds.size) {
        setLoading(true);
        dispatch(modelV2Actions.loadBids({ id: [...parentIds.values()] }, { additive: true }))
          .then((models: Bid[]) => {
            if (models.length !== parentIds.size) {
              setFailed(true);
              const returned = new Set<number>(models.map(m => m.id));
              for (const id of parentIds) {
                if (!returned.has(id)) {
                  failedParents.current.add(id);
                }
              }
            } else {
              setFailed(false);
            }
          })
          .catch(() => {
            setFailed(true);
          })
          .finally(() => setLoading(false));
      }
    }
  }, [dispatch, bids]);
  return { loading, failed };
}
