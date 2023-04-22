const AVERAGE_SPEAKING_SPEED = 140;
// Rate at which average speaking speed decreases based on the word-length of the content.
const DURATION_DECAY = 0.008;
// Expected variation for average speaking rate.
const VARIANCE = 0.2;

/** Returns a human-optimized string representation of the given duration. If the
 * time is under 45 seconds, show a seconds value, otherwise, show a fractional
 * minutes value of at least 1 minute. Fractions beyond 2 minutes are rounded to
 * the nearest quarter of a minute for fast legibility.
 */
function getTimeString(time: number) {
  if (time < 0.75) return `${Math.floor(time * 60)}s`;

  if (time > 2) {
    time = Math.floor(time * 4) / 4;
  }

  return `${Math.max(time, 1).toFixed(1)}m`;
}

/**
 * Estimates and returns an expected time range for speaking the given content out loud.
 * The range is pre-formatted as a string to be most easily human readable.
 */
export default function getEstimatedReadingTime(content?: string) {
  if (content == null) return '0s';

  const wordCount = content.split(/\b[^\s]+\b/).length;
  const decay = wordCount * DURATION_DECAY;
  const spread = AVERAGE_SPEAKING_SPEED * VARIANCE;

  const min = wordCount / (AVERAGE_SPEAKING_SPEED + spread - decay);
  const max = wordCount / (AVERAGE_SPEAKING_SPEED - spread - decay);

  const minString = getTimeString(min);
  const maxString = getTimeString(max);

  if (max < 0.4) return `~${maxString}`;

  return `${minString}–${maxString}`;
}
