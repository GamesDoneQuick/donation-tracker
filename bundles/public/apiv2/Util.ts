import { PaginationInfo } from '@public/apiv2/APITypes';

export function compressInfinitePages<T>(pages: PaginationInfo<T>[], limit: number) {
  if (limit < 1) {
    throw new Error('limit must be at least 1');
  }
  if (Math.floor(limit) !== limit) {
    throw new Error('limit must be an integer');
  }
  // reslices all pages so that they have exactly <limit> items, unless there are none left
  // since this might result in a different number of pages, forEach is not suitable
  let n = 0;

  let page = pages.at(0);
  while (page) {
    const leftovers = page.results.splice(limit);
    let next = pages.at(n + 1);
    if (next == null && leftovers.length) {
      pages.push({
        count: 0,
        previous: '__FAKE__VALUE__',
        next: null,
        results: [],
      });
      page.next = '__FAKE__VALUE__';
      next = pages[n + 1];
    }
    if (next) {
      next.results.splice(0, 0, ...leftovers);
    }
    while (page.results.length < limit && next) {
      const tail = next.results.splice(0, limit - page.results.length);
      page.results.splice(page.results.length, 0, ...tail);
      if (next.results.length === 0) {
        pages.splice(n + 1, 1);
      }
      next = pages.at(n + 1);
      if (next == null) {
        page.next = null;
      }
    }
    page.count = page.results.length;
    ++n;
    page = pages.at(n);
  }
}
