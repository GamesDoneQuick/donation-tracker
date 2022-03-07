import _ from 'lodash';
import createCachedSelector from 're-reselect';
import { createSelector } from 'reselect';

import TimeUtils, { DateTime, Duration, Interval } from '@public/util/TimeUtils';

import { StoreState } from '@tracker/Store';

import { Prize } from './PrizeTypes';

const SOON_DURATION = Duration.fromMillis(7 * 60 * 60 * 1000); // 4 hours

const getPrizesState = (state: StoreState) => state.prizes;
const getPrizeId = (_state: StoreState, { prizeId }: { prizeId: string }) => prizeId;
const getTargetTime = (_state: StoreState, { targetTime }: { targetTime: DateTime }) => targetTime;

export const getPrizeIds = createSelector([getPrizesState], state => _.map(state.prizes, (_prize, id) => parseInt(id)));

export const getPrizes = createSelector([getPrizesState], state => Object.values(state.prizes));

export const getPrize = createCachedSelector(
  [getPrizesState, getPrizeId],
  (state, prizeId): Prize | undefined => state.prizes[prizeId],
)(getPrizeId);

export const getSortedPrizes = createSelector([getPrizes], prizes =>
  prizes.sort((prize1, prize2) => TimeUtils.compare(prize1.startDrawTime, prize2.startDrawTime)),
);

export const getPrizesOpeningSoon = createSelector([getPrizes, getTargetTime], (prizes, targetTime) => {
  const soonInterval = Interval.after(targetTime, SOON_DURATION);

  return prizes
    .filter(prize => {
      return prize.startDrawTime != null && soonInterval.contains(prize.startDrawTime);
    })
    .sort((prize1, prize2) => TimeUtils.compare(prize1.startDrawTime, prize2.startDrawTime));
});

export const getPrizesClosingSoon = createSelector([getPrizes, getTargetTime], (prizes, targetTime) => {
  const soonInterval = Interval.after(targetTime, SOON_DURATION);
  return prizes
    .filter(prize => {
      return prize.endDrawTime != null && soonInterval.contains(prize.endDrawTime);
    })
    .sort((prize1, prize2) => TimeUtils.compare(prize1.endDrawTime, prize2.endDrawTime));
});
