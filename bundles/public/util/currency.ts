export function asCurrency(amount: string | number) {
  return `$${Number(amount).toFixed(2)}`;
}

export function parseCurrency(amount: string) {
  const parsed = parseFloat(amount);
  return parsed === NaN ? undefined : parsed;
}
