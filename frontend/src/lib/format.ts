export function formatMoney(amount: string, currency: string): string {
  // amount arrives as a Decimal string from the API; Number() is for display only.
  return new Intl.NumberFormat("en-SG", { style: "currency", currency }).format(Number(amount));
}

export function formatPercent(weight: string): string {
  return `${(Number(weight) * 100).toFixed(1)}%`;
}
