import { APIError } from '@public/apiv2/reducers/trackerBaseApi';

export function getFixtureError(overrides?: Partial<APIError>): APIError {
  return {
    status: 500,
    statusText: 'Internal Server Error',
    data: { detail: 'server blew up' },
    ...overrides,
  };
}
