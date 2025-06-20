import { Prize } from '@public/apiv2/Models';

/**
 * Returns the URL of an image to use when showing a Prize individually.
 */
export function getPrimaryImage(prize?: Prize) {
  return [prize?.imagefile, prize?.image, prize?.altimage].find(d => d != null) ?? null;
}

/**
 * Returns the URL of an image to use when showing a Prize as part of a group.
 */
export function getSummaryImage(prize?: Prize) {
  return [prize?.imagefile, prize?.altimage, prize?.image].find(d => d != null) ?? null;
}
