export function asCurrency(amount: string | number) {
  return `$${Number(amount).toFixed(2)}`;
}

export function parseCurrency(amount?: string) {
  if (amount == null) return undefined;
  const parsed = parseFloat(amount);
  return Number.isNaN(parsed) ? undefined : parsed;
}
