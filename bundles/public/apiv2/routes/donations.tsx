import type { APIDonation, PaginationInfo } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

interface DonationsFilterOptions {
  after?: Date;
}

export async function getUnprocessedDonations(eventId: string, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS_UNPROCESSED(+eventId), {
    after: options.after?.toISOString(),
  });
  return response.data.results;
}

export async function getFlaggedDonations(eventId: string, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS_FLAGGED(+eventId), {
    after: options.after?.toISOString(),
  });
  return response.data.results;
}

export async function getUnreadDonations(eventId: string, options: DonationsFilterOptions = {}) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS_UNREAD(+eventId), {
    after: options.after?.toISOString(),
  });
  return response.data.results;
}

/**
 * Fetch specific donations from the API from the list of given IDs. Donations
 * that do not correspond to an existing donation will be omitted from the
 * returned list.
 */
export async function getDonations(donationIds: string[]) {
  const response = await HTTPUtils.get<PaginationInfo<APIDonation>>(Endpoints.DONATIONS(), {
    id: donationIds,
  });
  return response.data.results;
}

export async function unprocessDonation(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_UNPROCESS(donationId));
  return response.data;
}

export async function approveDonationComment(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_APPROVE_COMMENT(donationId));
  return response.data;
}

export async function denyDonationComment(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_DENY_COMMENT(donationId));
  return response.data;
}

export async function flagDonation(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_FLAG(donationId));
  return response.data;
}

export async function sendDonationToReader(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_SEND_TO_READER(donationId));
  return response.data;
}

export async function pinDonation(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_PIN(donationId));
  return response.data;
}

export async function unpinDonation(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_UNPIN(donationId));
  return response.data;
}

export async function readDonation(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_READ(donationId));
  return response.data;
}

export async function ignoreDonation(donationId: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_IGNORE(donationId));
  return response.data;
}

export async function editModComment(donationId: string, comment: string) {
  const response = await HTTPUtils.patch<APIDonation>(Endpoints.DONATIONS_COMMENT(donationId), { comment });
  return response.data;
}
