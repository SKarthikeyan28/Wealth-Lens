export const DISCLAIMER =
  "Wealth-Lens is an educational and simulation tool only. It does not constitute " +
  "financial advice, investment advice, or any regulated financial service. All " +
  "projections and analyses are simulations based on stated assumptions and historical " +
  "data — they are not forecasts or guarantees of future performance. No real money is " +
  "involved. Users are responsible for their own financial decisions. This tool is not " +
  "licensed by the Monetary Authority of Singapore (MAS).";

export function Disclaimer() {
  return (
    <footer className="border-t border-zinc-200 bg-zinc-50 px-4 py-3 text-xs text-zinc-600">
      <p>{DISCLAIMER}</p>
    </footer>
  );
}
