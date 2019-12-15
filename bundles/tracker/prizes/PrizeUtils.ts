import { Prize } from './PrizeTypes';
import _ from 'lodash';

export function getPrimaryImage(prize: Prize): string | undefined {
  return _.find([prize.imageFile, prize.image, prize.altImage]);
}
