import _ from 'lodash';

import { Prize } from '@public/apiv2/Models';

/**
 * Returns the URL of an image to use when showing a Prize individually.
 */
export function getPrimaryImage(prize?: Prize): string | null | undefined {
  return prize && _.find([prize.imagefile, prize.image, prize.altimage]);
}

/**
 * Returns the URL of an image to use when showing a Prize as part of a group.
 */
export function getSummaryImage(prize?: Prize): string | null | undefined {
  return prize && _.find([prize.imagefile, prize.altimage, prize.image]);
}
