import * as React from 'react';
import create from 'zustand';

import { Donation } from '@public/apiv2/APITypes';

type DonationId = Donation['id'];

export type DonationState = 'unprocessed' | 'flagged' | 'ready' | 'done';

/**
 * Return the state of the donation as inferred purely by its readstate, as in,
 * whether the donation should be shown to hosts or head donations, rather than
 * considered 'done' or 'unprocessed'. If the donation is not in one of those
 * middle states, return `defaultState` instead.
 */
function getDonationStateFromReadState(donation: Donation, defaultState: DonationState): DonationState {
  switch (donation.readstate) {
    case 'READY':
      return 'ready';
    case 'FLAGGED':
      return 'flagged';
    default:
      return defaultState;
  }
}

function getDonationState(donation: Donation): DonationState {
  switch (donation.commentstate) {
    case 'APPROVED':
      return getDonationStateFromReadState(donation, 'done');
    case 'ABSENT':
    case 'PENDING':
      return getDonationStateFromReadState(donation, 'unprocessed');
    // FLAGGED does not get used on commentstates (never assigned in code)
    case 'FLAGGED':
    case 'DENIED':
    default:
      return 'done';
  }
}

interface DonationsStoreState {
  /**
   * All donations the client is currently aware of, including donations that
   * have already been processed.
   */
  donations: Record<number, Donation>;
  /**
   * The set of donations that are completely unprocessed and should be handled
   * by the first tier of donation processors.
   */
  unprocessed: Set<DonationId>;
  /**
   * Donations that were flagged by the first tier of processors and are now
   * waiting to be handled by Head Donations.
   */
  flagged: Set<DonationId>;
  /**
   * Donations that have been approved and sent to readers.
   */
  ready: Set<DonationId>;
  /**
   * Donations that have been processed to completion, whether by being denied,
   * approved only, read, or ignored.
   */
  done: Set<DonationId>;
}

const useDonationsStore = create<DonationsStoreState>()(() => ({
  donations: {},
  unprocessed: new Set(),
  flagged: new Set(),
  ready: new Set(),
  done: new Set(),
}));

export default useDonationsStore;

/**
 * Add the given set of donations to the list of known donations, inserting
 * them as appropriate into the store's state. All donations loaded this way
 * will be considered "unprocessed".
 */
export function loadDonations(donations: Donation[]) {
  useDonationsStore.setState(state => {
    const newDonations = { ...state.donations };
    const unprocessed = new Set(state.unprocessed);
    const flagged = new Set(state.flagged);
    const ready = new Set(state.ready);
    const done = new Set(state.done);
    for (const donation of donations) {
      newDonations[donation.id] = donation;
      switch (getDonationState(donation)) {
        case 'unprocessed':
          unprocessed.add(donation.id);
          flagged.delete(donation.id);
          ready.delete(donation.id);
          done.delete(donation.id);
          break;
        case 'flagged':
          unprocessed.delete(donation.id);
          flagged.add(donation.id);
          ready.delete(donation.id);
          done.delete(donation.id);
          break;
        case 'ready':
          unprocessed.delete(donation.id);
          flagged.delete(donation.id);
          ready.add(donation.id);
          done.delete(donation.id);
          break;
        case 'done':
          unprocessed.delete(donation.id);
          flagged.delete(donation.id);
          ready.delete(donation.id);
          done.add(donation.id);
          break;
      }
    }

    return { donations: newDonations, unprocessed, flagged, ready, done };
  });
}

export function useDonation(donationId: number) {
  const donations = useDonationsStore(state => state.donations);
  return donations[donationId];
}

export function useDonations(donationIds: DonationId[] | Set<DonationId>) {
  const donations = useDonationsStore(state => state.donations);
  return React.useMemo(() => Array.from(donationIds).map(id => donations[id]), [donations, donationIds]);
}

// NOTE(faulty): This is a little bit gross, but the two use cases of filtering
// donations are either literal filtering with a predicate (filter tabs on the
// reading page), or filtering to a known set of ids (group tabs on the reading
// page). Unfortunately as it's written now, both need to be handled using the
// same code path, meaning this hook needs to know how to do both.
export function useFilteredDonations(
  donationState: DonationState,
  predicateOrIds: Array<Donation['id']> | ((donation: Donation) => boolean),
): Donation[] {
  const [donations, groupIds] = useDonationsStore(state => [state.donations, state[donationState]]);
  return React.useMemo(() => {
    if (typeof predicateOrIds === 'function') {
      return Array.from(groupIds)
        .map(id => donations[id])
        .filter(predicateOrIds);
    } else {
      return predicateOrIds.filter(id => groupIds.has(id)).map(id => donations[id]);
    }
  }, [donations, groupIds, predicateOrIds]);
}

function getAndSortDonations(donations: Record<string, Donation>, ids: Set<DonationId>) {
  return Array.from(ids)
    .map(id => donations[id])
    .sort((a, b) => a.timereceived.localeCompare(b.timereceived));
}

export function useDonationsInState(donationState: DonationState) {
  const [donations, ids] = useDonationsStore(state => [state.donations, state[donationState]]);
  return React.useMemo(() => getAndSortDonations(donations, ids), [donations, ids]);
}

export function useDonationIdsInState(donationState: DonationState) {
  return useDonationsStore(state => state[donationState]);
}
