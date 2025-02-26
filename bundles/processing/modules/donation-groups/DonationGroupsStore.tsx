import React from 'react';
import create from 'zustand';
import { persist } from 'zustand/middleware';
import { TagProps } from '@faulty/gdq-design';

/**
 * Either a design system token name to be resolved dynamically, or a static
 * value that can be used in a CSS `color` property.
 */
export type DonationGroupColor = NonNullable<TagProps['color']>;

import { Donation } from '@public/apiv2/Models';

export interface DonationGroup {
  id: string;
  name: string;
  color: DonationGroupColor;
  order: number[];
}

type DonationGroupProps = Omit<DonationGroup, 'order'>;

interface DonationGroupsStoreState {
  /**
   * Ordered list of donation groups maintained locally.
   */
  groups: DonationGroup[];
  /**
   * Ensure our local list matches what the server has, while preserving any existing order.
   */
  syncDonationGroupsWithServer(groups: string[]): void;
  /**
   * Change client-side properties of an existing donation group.
   */
  updateDonationGroup(props: DonationGroupProps): void;
}

const useDonationGroupsStore = create<DonationGroupsStoreState>()(
  persist(
    (set, get) => ({
      groups: [] as DonationGroup[],
      syncDonationGroupsWithServer(groups: string[]) {
        // deletes any that don't exist on the server any more, and adds sensible defaults for new ones
        set(state => ({
          groups: [
            ...state.groups.filter(g => groups.includes(g.id)),
            ...groups
              .filter(g => state.groups.find(o => o.id === g) == null)
              .map((g): DonationGroup => ({ id: g, name: g.replace(/_/g, ' '), color: 'default', order: [] })),
          ],
        }));
      },
      updateDonationGroup(props: DonationGroupProps) {
        const { groups } = get();
        const groupIndex = groups.findIndex(group => group.id === props.id);
        if (groupIndex >= 0) {
          const group = { ...groups[groupIndex], ...props };
          const newGroups = [...groups];
          newGroups.splice(groupIndex, 1, group);
          set({ groups: newGroups });
        } else {
          // server response has not been processed fully yet, but add it optimistically
          set({ groups: [...groups, { ...props, order: [] }] });
        }
      },
    }),
    {
      name: 'processing-donation-groups',
      partialize: state => ({
        groups: state.groups,
      }),
    },
  ),
);

export default useDonationGroupsStore;

export function useDonationGroup(id: string) {
  return useDonationGroupsStore(state => state.groups.find(group => group.id === id));
}

export function useGroupsForDonation(donation: Donation) {
  const groups = useDonationGroupsStore(state => state.groups);
  return React.useMemo(() => groups.filter(group => donation.groups?.includes(group.id)), [groups, donation.groups]);
}

/**
 * Change the position of a donation within a group.
 *
 * @param groupId The group to move the donation within.
 * @param movingDonationId The donation being moved to a new position
 * @param targetDonationId The donation around which the moving donation will be placed.
 * @param below When true, the moving donation will be placed below the target instead.
 */
export function moveDonationWithinGroup(
  groupId: string,
  movingDonationId: number,
  targetDonationId: number,
  below = false,
) {
  useDonationGroupsStore.setState(({ groups }) => {
    const groupIndex = groups.findIndex(group => group.id === groupId);
    const oldGroup = groups[groupIndex];
    const newOrder = [...oldGroup.order];
    // Remove the moving donation from the list first
    newOrder.splice(newOrder.indexOf(movingDonationId), 1);
    // Then find the index of the target and insert the moving donation above it.
    // If below is true, add one to the index to get the _following_ index.
    const offset = below ? 1 : 0;
    newOrder.splice(newOrder.indexOf(targetDonationId) + offset, 0, movingDonationId);

    const group = { ...oldGroup, order: newOrder };
    // Update the group in the state
    const newGroups = [...groups];
    newGroups.splice(groupIndex, 1, group);
    return { groups: newGroups };
  });
}

/**
 * Change the position of a group within the list of groups.
 *
 * @param movingGroupId The group being moved to a new position
 * @param targetGroupId The group around which the moving group will be placed.
 * @param below When true, the moving group will be placed below the target instead.
 */
export function moveDonationGroup(movingGroupId: string, targetGroupId: string, below = false) {
  useDonationGroupsStore.setState(({ groups }) => {
    const newGroups = [...groups];
    const movingGroupIndex = groups.findIndex(group => group.id === movingGroupId);
    const [movedGroup] = newGroups.splice(movingGroupIndex, 1);
    // Then find the index of the target and insert the moving donation above it.
    // If below is true, add one to the index to get the _following_ index.
    const offset = below ? 1 : 0;
    const targetGroupIndex = newGroups.findIndex(group => group.id === targetGroupId);
    newGroups.splice(targetGroupIndex + offset, 0, movedGroup);

    return { groups: newGroups };
  });
}
