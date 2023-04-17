import type { Me } from '../APITypes';
import Endpoints from '../Endpoints';
import HTTPUtils from '../HTTPUtils';

export async function getMe() {
  const response = await HTTPUtils.get<Me>(Endpoints.ME);
  return response.data;
}
