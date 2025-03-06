import { APIModel, PaginationInfo } from '@public/apiv2/APITypes';

export function getFixtureEmptyPage<T extends APIModel = APIModel>(): PaginationInfo<T> {
  return {
    count: 0,
    previous: null,
    next: null,
    results: [],
  };
}
