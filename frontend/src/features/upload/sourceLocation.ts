export function sourceContainsCell(
  source: string | null,
  selected: string,
): boolean {
  if (!selected) return true;
  if (!source) return false;
  if (source.toUpperCase() === selected.toUpperCase()) return true;
  const range = /^([A-Z]+)([1-9]\d*):([A-Z]+)([1-9]\d*)$/i.exec(source);
  const cell = /^([A-Z]+)([1-9]\d*)$/i.exec(selected);
  if (!range || !cell) return false;
  const column = (letters: string) =>
    [...letters.toUpperCase()].reduce(
      (value, letter) => value * 26 + letter.charCodeAt(0) - 64,
      0,
    );
  return (
    column(cell[1]) >= column(range[1]) &&
    column(cell[1]) <= column(range[3]) &&
    Number(cell[2]) >= Number(range[2]) &&
    Number(cell[2]) <= Number(range[4])
  );
}
