import type { Donation } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

interface DonationsFilterOptions {
  after?: Date;
}

export async function getUnprocessedDonations(eventId: string, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<Donation[]>(Endpoints.DONATIONS_UNPROCESSED, {
    event_id: eventId,
    after: options.after?.toISOString(),
  });
  return response.data;
}

export async function getFlaggedDonations(eventId: string, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<Donation[]>(Endpoints.DONATIONS_FLAGGED, {
    event_id: eventId,
    after: options.after?.toISOString(),
  });
  return response.data;
}

export interface DonationCountsResponse extends Record<string, number> {
  pending: number;
  flagged: number;
  ready: number;
  read: number;
  approved: number;
  denied: number;
}

export async function getDonationCounts(eventId: string) {
  const response = await HTTPUtils.get<DonationCountsResponse>(Endpoints.DONATIONS_COUNTS, { event_id: eventId });
  return response.data;
}

export async function unprocessDonation(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_UNPROCESS(donationId));
  return response.data;
}

export async function approveDonationComment(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_APPROVE_COMMENT(donationId));
  return response.data;
}

export async function denyDonationComment(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_DENY_COMMENT(donationId));
  return response.data;
}

export async function flagDonation(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_FLAG(donationId));
  return response.data;
}

export async function sendDonationToReader(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_SEND_TO_READER(donationId));
  return response.data;
}

export async function pinDonation(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_PIN(donationId));
  return response.data;
}

export async function unpinDonation(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_UNPIN(donationId));
  return response.data;
}
