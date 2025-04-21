// This type enforces that consumers pass in the `currency` they want to display.
import { useEventFromRoute } from '@public/apiv2/hooks';

interface CurrencyOptions extends Omit<Intl.NumberFormatOptions, 'style'> {
  currency: string;
}

export function asCurrency(amount: string | number, options: CurrencyOptions) {
  const formatOptions = {
    style: 'currency' as const,
    minimumIntegerDigits: 1,
    minimumFractionDigits: 2,
    ...options,
  };

  // We need to set minimumFractionDigits to 0 when the max is 0
  if (formatOptions.maximumFractionDigits === 0) {
    formatOptions.minimumFractionDigits = 0;
  }

  // `en-US` is hardcoded here because we don't actually localize the frontend currently.
  const formatter = new Intl.NumberFormat('en-US', formatOptions);

  return formatter.format(Number(amount));
}

/*
 * returns a function that will format the provided number as the routed event currency
 */

export function useEventCurrency() {
  const { data: event } = useEventFromRoute();
  return (amount: number | string, options?: Omit<CurrencyOptions, 'currency'>) =>
    event ? asCurrency(amount, { ...options, currency: event.paypalcurrency }) : '';
}

export function getCurrencySymbol(currency: string): string {
  try {
    const formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency, currencyDisplay: 'narrowSymbol' });

    for (const part of formatter.formatToParts(0)) {
      if (part.type === 'currency') return part.value;
    }
  } catch {
    // Ignored: RangeError: invalid currency code in NumberFormat()
  }

  // If there was no currency symbol in the formatted string, then we can assume that
  // the language does not expect there to be a symbol around the currency value.
  return '';
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
