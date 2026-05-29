const MUSEUM_SHORT_LABELS: Record<string, string> = {
  "National Gallery of Art": "NGA",
  "Smithsonian Open Access": "Smithsonian",
  "The Metropolitan Museum of Art": "Met",
  "Art Institute of Chicago": "Art Institute of Chicago",
};

export function museumShortLabel(collectionName: string | null | undefined): string | null {
  if (!collectionName) return null;
  return MUSEUM_SHORT_LABELS[collectionName] ?? collectionName;
}

export function museumCollectionSearchLabel(
  collectionName: string | null | undefined
): string | null {
  if (!collectionName) return null;
  return `Searching ${collectionName} collection`;
}
