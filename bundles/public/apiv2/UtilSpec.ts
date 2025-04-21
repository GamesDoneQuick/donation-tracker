import { produce } from 'immer';

import { PaginationInfo } from '@public/apiv2/APITypes';
import { compressInfinitePages } from '@public/apiv2/Util';

describe('apiV2/Util', () => {
  describe('compressInfinitePages', () => {
    it('fixes overflow', () => {
      const numbers = Array.from(new Array(8)).map((_, n) => n);
      const pages: Array<PaginationInfo<number>> = [
        {
          count: 8,
          previous: null,
          next: null,
          results: numbers,
        },
      ];
      const newPages = produce({ pages, pageParams: [] }, data => {
        compressInfinitePages(data, 5);
      }).pages;
      expect(newPages.length).toBe(2);
      expect(newPages[0].count).toBe(5);
      expect(newPages[0].previous).toBeNull();
      expect(newPages[0].next).not.toBeNull();
      expect(newPages[0].results).toEqual(numbers.slice(0, 5));
      expect(newPages[1].count).toBe(3);
      expect(newPages[1].previous).not.toBeNull();
      expect(newPages[1].next).toBeNull();
      expect(newPages[1].results).toEqual(numbers.slice(5, 10));
      const smallPages = produce({ pages, pageParams: [] }, data => {
        compressInfinitePages(data, 1);
      }).pages;
      expect(smallPages.length).toBe(8);
      for (let n = 0; n < 8; ++n) {
        expect(smallPages[n].count).toBe(1);
        if (n === 0) {
          expect(smallPages[n].previous).toBeNull();
        } else {
          expect(smallPages[n].previous).not.toBeNull();
        }
        if (n !== 7) {
          expect(smallPages[n].next).not.toBeNull();
        } else {
          expect(smallPages[n].next).toBeNull();
        }
        expect(smallPages[n].results).toEqual(numbers.slice(n, n + 1));
      }
    });

    it('fixes underflow and trims empty pages', () => {
      const numbers = Array.from(new Array(10)).map((_, n) => n);
      const pages: Array<PaginationInfo<number>> = [
        {
          count: 3,
          previous: null,
          next: '__FAKE__',
          results: numbers.slice(0, 3),
        },
        {
          count: 3,
          previous: '__FAKE__',
          next: '__FAKE__',
          results: numbers.slice(3, 6),
        },
        {
          count: 3,
          previous: '__FAKE__',
          next: '__FAKE__',
          results: numbers.slice(6, 9),
        },
        {
          count: 1,
          previous: '__FAKE__',
          next: null,
          results: numbers.slice(9, 10),
        },
      ];
      const newPages = produce({ pages, pageParams: [] }, data => {
        compressInfinitePages(data, 5);
      }).pages;
      expect(newPages.length).toBe(2);
      expect(newPages[0].count).toBe(5);
      expect(newPages[0].previous).toBeNull();
      expect(newPages[0].next).not.toBeNull();
      expect(newPages[0].results).toEqual(numbers.slice(0, 5));
      expect(newPages[1].count).toBe(5);
      expect(newPages[1].previous).not.toBeNull();
      expect(newPages[1].next).toBeNull();
      expect(newPages[1].results).toEqual(numbers.slice(5, 10));
      const otherNewPages = produce({ pages, pageParams: [] }, data => {
        compressInfinitePages(data, 9);
      }).pages;
      expect(otherNewPages.length).toBe(2);
      expect(otherNewPages[0].count).toBe(9);
      expect(otherNewPages[0].previous).toBeNull();
      expect(otherNewPages[0].next).not.toBeNull();
      expect(otherNewPages[0].results).toEqual(numbers.slice(0, 9));
      expect(otherNewPages[1].count).toBe(1);
      expect(otherNewPages[1].previous).not.toBeNull();
      expect(otherNewPages[1].next).toBeNull();
      expect(otherNewPages[1].results).toEqual(numbers.slice(9, 10));
    });

    it('does not modify pages if it already fits', () => {
      const numbers = Array.from(new Array(8)).map((_, n) => n);
      const pages: Array<PaginationInfo<number>> = [
        {
          count: 8,
          previous: null,
          next: null,
          results: numbers,
        },
      ];
      const newPages = produce({ pages, pageParams: [] }, data => {
        compressInfinitePages(data, 8);
      }).pages;
      expect(pages).toBe(newPages);
    });

    it('returns plain arrays unmodified', () => {
      const numbers = Array.from(new Array(10)).map((_, n) => n);
      const newNumbers = produce(numbers, data => {
        compressInfinitePages(data, 2);
      });
      expect(numbers).toBe(newNumbers);
    });
  });
});
