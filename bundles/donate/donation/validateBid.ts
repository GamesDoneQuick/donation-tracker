export default function validateBid({ amount, total, selected, choice, newChoice }: any) {
  if (amount <= 0) {
    return [false, 'Amount must be greater than 0.'];
  }

  if (amount > total) {
    return [false, `Amount cannot be greater than $${total}.`];
  }

  if (!selected || selected.goal) {
    return [true, null];
  }

  return [true, null];
}
