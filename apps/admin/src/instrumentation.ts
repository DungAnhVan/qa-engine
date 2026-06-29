/**
 * Next.js instrumentation hook — runs once before the server starts.
 *
 * Node.js 22+ ships a built-in global `localStorage` (Web Storage API).
 * Without the `--localstorage-file` CLI flag, the object exists but its
 * methods (getItem, setItem, …) are NOT functions. Next.js internal SSR
 * code calls `localStorage.getItem(…)` and receives
 *   TypeError: localStorage.getItem is not a function
 *
 * We detect this broken stub and remove it so Next.js treats the server
 * environment as having no localStorage — which is the correct behaviour
 * for a Node.js SSR context.
 */
export async function register() {
  const ls = (globalThis as Record<string, unknown>).localStorage

  if (
    ls !== null &&
    typeof ls === 'object' &&
    typeof (ls as Record<string, unknown>).getItem !== 'function'
  ) {
    delete (globalThis as Record<string, unknown>).localStorage
  }
}
