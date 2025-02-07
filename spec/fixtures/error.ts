import { APIError } from '../../bundles/public/apiv2/reducers/trackerApi';

export function getFixtureError(overrides?: Partial<APIError>): APIError {
  return {
    status: 500,
    statusText: 'Internal Server Error',
    data: { detail: 'server blew up' },
    ...overrides,
  };
}
