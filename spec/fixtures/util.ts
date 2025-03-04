import { Model, PaginationInfo } from '@gamesdonequick/donation-tracker-api-types';

import { APIError } from '@public/apiv2/reducers/trackerApi';

export function getFixtureValue<T extends Model>(
  code: () => number,
  success: PaginationInfo<T>,
  error: APIError,
): () => [number, PaginationInfo<T> | APIError] {
  return () => [code(), code() >= 200 && code() < 300 ? success : error];
}
