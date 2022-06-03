import type { Donation } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

export async function getUnprocessedDonations(eventId: string) {
  const response = await HTTPUtils.get<Donation[]>(Endpoints.DONATIONS_UNPROCESSED, { event_id: eventId });
  return response.data;
}

export async function unprocessDonation(donationId: string) {
  const response = await HTTPUtils.post<Donation>(Endpoints.DONATIONS_APPROVE_COMMENT(donationId));
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
