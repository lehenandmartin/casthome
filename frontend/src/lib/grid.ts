// Grids that show only full rows: how many columns a CSS grid has right now.

/** Number of columns of a grid (auto-fill keeps empty tracks, so this works with few items). */
export function columnCount(grid: HTMLElement): number {
  return getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length;
}

/** Calls `onchange` with the column count now and whenever the grid is resized. */
export function observeColumns(grid: HTMLElement, onchange: (columns: number) => void): () => void {
  const observer = new ResizeObserver(() => onchange(columnCount(grid)));
  observer.observe(grid);
  onchange(columnCount(grid));
  return () => observer.disconnect();
}

/** Only full rows of `items`, unless there is less than one row. */
export function fullRows<T>(items: T[], columns: number): T[] {
  if (columns <= 0 || items.length < columns) return items;
  return items.slice(0, items.length - (items.length % columns));
}
