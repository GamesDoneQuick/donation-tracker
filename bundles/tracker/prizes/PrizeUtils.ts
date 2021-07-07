import { Prize } from './PrizeTypes';
import _ from 'lodash';

/**
 * Returns the URL of an image to use when showing a Prize individually.
 */
export function getPrimaryImage(prize: Prize): string | undefined {
  return _.find([prize.imageFile, prize.image, prize.altImage]);
}

/**
 * Returns the URL of an image to use when showing a Prize as part of a group.
 */
export function getSummaryImage(prize: Prize): string | undefined {
  return _.find([prize.imageFile, prize.altImage, prize.image]);
}
