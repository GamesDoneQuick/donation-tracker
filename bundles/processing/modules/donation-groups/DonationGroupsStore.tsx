import * as React from 'react';
import create from 'zustand';
import { persist } from 'zustand/middleware';
import { TagProps } from '@faulty/gdq-design';

/**
 * Either a design system token name to be resolved dynamically, or a static
 * value that can be used in a CSS `color` property.
 */
export type DonationGroupColor = NonNullable<TagProps['color']>;

export interface DonationGroup {
  id: string;
  name: string;
  color: DonationGroupColor;
  donationIds: number[];
}

type DonationGroupProps = Omit<DonationGroup, 'donationIds'>;

interface DonationGroupsStoreState {
  /**
   * Ordered list of donation groups maintained locally.
   */
  groups: DonationGroup[];
  /**
   * Create a new group for donations to be filtered into.
   */
  createDonationGroup(props: DonationGroupProps): void;
  /**
   * Change properties of an existing donation group.
   */
  updateDonationGroup(props: DonationGroupProps): void;
  /**
   * Permanently delete the group.
   */
  deleteDonationGroup(groupId: string): void;
  /**
   * Adds the donation to the given group.
   */
  addDonationToGroup(groupId: string, donationId: number): void;
  /**
   * Removes the donation to the given group.
   */
  removeDonationFromGroup(groupId: string, donationId: number): void;
  /**
   * Removes the donation from all groups, such as when the donation has been
   * read or ignored and should no longer be shown to readers.
   */
  removeDonationFromAllGroups(donationId: number): void;
}

const useDonationGroupsStore = create<DonationGroupsStoreState>()(
  persist(
    (set, get) => ({
      groups: [] as DonationGroup[],
      createDonationGroup(props: DonationGroupProps) {
        const newGroup: DonationGroup = { ...props, donationIds: [] };
        set(state => ({ groups: [...state.groups, newGroup] }));
      },
      updateDonationGroup(props: DonationGroupProps) {
        const { groups } = get();
        const groupIndex = groups.findIndex(group => group.id === props.id);
        if (groupIndex < 0) return;

        const group = { ...groups[groupIndex], ...props };
        const newGroups = [...groups];
        newGroups.splice(groupIndex, 1, group);
        set({ groups: newGroups });
      },
      deleteDonationGroup(groupId: string) {
        const { groups } = get();
        set({ groups: groups.filter(group => group.id !== groupId) });
      },
      addDonationToGroup(groupId: string, donationId: number) {
        const { groups } = get();
        const groupIndex = groups.findIndex(group => group.id === groupId);
        const oldGroup = groups[groupIndex];
        const group = { ...oldGroup, donationIds: [...oldGroup.donationIds, donationId] };
        const newGroups = [...groups];
        newGroups.splice(groupIndex, 1, group);
        set({ groups: newGroups });
      },
      removeDonationFromGroup(groupId: string, donationId: number) {
        const { groups } = get();
        const groupIndex = groups.findIndex(group => group.id === groupId);
        const oldGroup = groups[groupIndex];

        const group = { ...oldGroup, donationIds: oldGroup.donationIds.filter(id => id !== donationId) };
        const newGroups = [...groups];
        newGroups.splice(groupIndex, 1, group);
        set({ groups: newGroups });
      },
      removeDonationFromAllGroups(donationId: number) {
        const filteredGroups = get().groups.map(
          (group): DonationGroup => ({
            ...group,
            donationIds: group.donationIds.filter(id => id !== donationId),
          }),
        );
        set({ groups: filteredGroups });
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

export function useGroupsForDonation(donationId: number) {
  const groups = useDonationGroupsStore(state => state.groups);
  return React.useMemo(() => groups.filter(group => group.donationIds.includes(donationId)), [groups, donationId]);
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
    const newDonationIds = [...oldGroup.donationIds];
    // Remove the moving donation from the list first
    newDonationIds.splice(newDonationIds.indexOf(movingDonationId), 1);
    // Then find the index of the target and insert the moving donation above it.
    // If below is true, add one to the index to get the _following_ index.
    const offset = below ? 1 : 0;
    newDonationIds.splice(newDonationIds.indexOf(targetDonationId) + offset, 0, movingDonationId);

    const group = { ...oldGroup, donationIds: newDonationIds };
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
