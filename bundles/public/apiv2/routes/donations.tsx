import type { APIDonation, PaginationInfo } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

interface DonationsFilterOptions {
  after?: Date;
}

export async function getUnprocessedDonations(eventId: number, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS_UNPROCESSED(eventId), {
    after: options.after?.toISOString(),
  });
  return response.data.results;
}

export async function getFlaggedDonations(eventId: number, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS_FLAGGED(eventId), {
    after: options.after?.toISOString(),
  });
  return response.data.results;
}

export async function getUnreadDonations(eventId: number, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS_UNREAD(eventId), {
    after: options.after?.toISOString(),
  });
  return response.data.results;
}

/**
 * Fetch specific donations from the API from the list of given IDs. Donations
 * that do not correspond to an existing donation will be omitted from the
 * returned list.
 */
export async function getDonations(donationIds: number[]) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS, {
    id: donationIds,
  });
  return response.data.results;
}

export async function unprocessDonation(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_UNPROCESS(donationId));
  return response.data;
}

export async function approveDonationComment(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_APPROVE_COMMENT(donationId));
  return response.data;
}

export async function denyDonationComment(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_DENY_COMMENT(donationId));
  return response.data;
}

export async function flagDonation(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_FLAG(donationId));
  return response.data;
}

export async function sendDonationToReader(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_SEND_TO_READER(donationId));
  return response.data;
}

export async function pinDonation(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_PIN(donationId));
  return response.data;
}

export async function unpinDonation(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_UNPIN(donationId));
  return response.data;
}

export async function readDonation(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_READ(donationId));
  return response.data;
}

export async function ignoreDonation(donationId: number) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_IGNORE(donationId));
  return response.data;
}

export async function editModComment(donationId: number, comment: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_COMMENT(donationId), { comment });
  return response.data;
}
