import type { DonationProcessAction } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

export async function getProcessActionHistory() {
  const response = await HTTPUtils.get<DonationProcessAction[]>(Endpoints.PROCESS_ACTIONS);
  return response.data;
}

export async function undoProcessAction(actionId: number) {
  const response = await HTTPUtils.post<DonationProcessAction>(Endpoints.PROCESS_ACTIONS_UNDO(actionId));
  return response.data;
}
