export function asCurrency(amount: string | number) {
  return `\xa5${Number(amount).toFixed()}`;
}

export function parseCurrency(amount?: string) {
  if (amount == null) return undefined;
  const parsed = parseFloat(amount);
  return Number.isNaN(parsed) ? undefined : parsed;
}

// Like `parseCurrency`, but enforces that the given amount exists, and that it
// is parsed into an actual number (and not NaN).
export function parseCurrencyForced(amount: string) {
  const parsed = parseFloat(amount);
  if (Number.isNaN(parsed)) {
    throw new TypeError(`String value "${amount}" could not be parsed as a currency`);
  }

  return parsed;
}
