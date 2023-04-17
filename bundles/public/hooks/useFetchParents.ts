import { useEffect } from 'react';
import { useSelector } from 'react-redux';

import useSafeDispatch from '@public/api/useDispatch';

import modelActions from '../api/actions/models';

export function useFetchParents() {
  const bids = useSelector((state: any) => state.models.bid);
  const dispatch = useSafeDispatch();

  useEffect(() => {
    if (bids) {
      const parentIds = new Set(
        bids.filter((b: any) => b.parent && !bids.find((p: any) => p.pk === b.parent)).map((b: any) => b.parent),
      );
      if (parentIds.size) {
        dispatch(modelActions.loadModels('bid', { ids: [...parentIds.values()].join(',') }, true));
      }
    }
  }, [dispatch, bids]);
}
