import * as React from 'react';
import create from 'zustand';

import { DonationProcessAction } from '@public/apiv2/APITypes';

export type DonationState = 'unprocessed' | 'flagged' | 'ready' | 'done';

interface ProcessActionStoreState {
  /**
   * Ordered list of all actions known by the client, sorted by `occurred_at`
   * from oldest to newest.
   */
  actions: Record<number, DonationProcessAction>;
}

const useProcessActionsStore = create<ProcessActionStoreState>()(() => ({
  actions: {},
}));

export default useProcessActionsStore;

export function loadProcessActions(actions: DonationProcessAction[]) {
  useProcessActionsStore.setState(state => {
    const newActions = { ...state.actions };
    for (const action of actions) {
      newActions[action.id] = action;
    }
    return { actions: newActions };
  });
}

export function useProcessAction(actionId: number) {
  const actions = useProcessActionsStore(state => state.actions);
  return actions[actionId];
}

export function useOwnProcessActions(userId: number) {
  const actions = useProcessActionsStore(state => state.actions);
  return React.useMemo(
    () =>
      Object.values(actions)
        .filter(action => action.actor.id === userId)
        .sort((a, b) => b.occurred_at.localeCompare(a.occurred_at)),
    [actions, userId],
  );
}
