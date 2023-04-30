import type { DonationProcessAction } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

export async function getProcessActionHistory() {
  const response = await HTTPUtils.get<DonationProcessAction[]>(Endpoints.PROCESS_ACTIONS);
  return response.data;
}
