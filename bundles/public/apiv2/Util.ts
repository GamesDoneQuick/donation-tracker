import { PageOrInfinite } from '@public/apiv2/reducers/trackerBaseApi';

/**
 * Will take the provided InfiniteData structure and resize each page to the desired limit
 * @param data either a bare array (for convenience with standard queries), or InfiniteData
 * @param limit the new size of the desired pages
 */

export function compressInfinitePages(data: PageOrInfinite<unknown>, limit: number) {
  // if it's just a bare array then don't do anything, for convenience
  if (Array.isArray(data)) {
    return;
  }
  const { pages } = data;
  if (limit < 1) {
    throw new Error('limit must be at least 1');
  }
  if (Math.floor(limit) !== limit) {
    throw new Error('limit must be an integer');
  }
  // reslices all pages so that they have exactly <limit> items, unless there are none left
  // since this might result in a different number of pages, forEach is not suitable
  for (let n = 0, page = pages.at(n); page; page = pages.at(++n)) {
    // chop off the tail and push it into the next page, creating one if necessary
    const tail = page.results.splice(limit);
    let next = pages.at(n + 1);
    if (next == null && tail.length) {
      pages.push({
        count: 0,
        previous: '__FAKE__VALUE__',
        next: null,
        results: [],
      });
      page.next = '__FAKE__VALUE__';
      next = pages.at(n + 1);
    }
    if (next) {
      next.results.splice(0, 0, ...tail);
    }
    // pull stuff from the next page into this one, if it has room
    while (page.results.length < limit && next) {
      const head = next.results.splice(0, limit - page.results.length);
      page.results.splice(page.results.length, 0, ...head);
      // delete the next page if it's now empty
      if (next.results.length === 0) {
        pages.splice(n + 1, 1);
      }
      next = pages.at(n + 1);
      // this page is now the last page
      if (next == null) {
        page.next = null;
      }
    }
    page.count = page.results.length;
  }
}
