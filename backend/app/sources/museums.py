"""Museum name matching for collection lookup routing."""

from __future__ import annotations

from app.sources.matching import normalize

NGA_SOURCE_NAME = "National Gallery of Art"
SMITHSONIAN_SOURCE_NAME = "Smithsonian Open Access"
MET_SOURCE_NAME = "The Metropolitan Museum of Art"
AIC_SOURCE_NAME = "Art Institute of Chicago"
WIKIMEDIA_SOURCE_NAME = "Wikimedia Commons"

NGA_MUSEUM_ALIASES = (
    "national gallery of art",
    "national gallery of art, washington",
    "nga",
)

SMITHSONIAN_MUSEUM_ALIASES = (
    "smithsonian",
    "smithsonian american art museum",
    "saam",
    "national portrait gallery",
    "hirshhorn",
    "hirshhorn museum",
    "national museum of asian art",
    "freer gallery",
    "arthur m sackler gallery",
    "sackler gallery",
    "national museum of african art",
    "renwick gallery",
)

SMITHSONIAN_EXPLICIT_SOURCES = {
    "smithsonian",
    "si",
    "saam",
    "npg",
    "hmsg",
    "fsg",
    "nmafa",
}

MET_MUSEUM_ALIASES = (
    "the met",
    "metropolitan museum of art",
    "met museum",
    "metropolitan museum",
)

AIC_MUSEUM_ALIASES = (
    "art institute of chicago",
    "aic",
    "art institute chicago",
)


def is_nga_museum(museum_name: str | None) -> bool:
    if not museum_name:
        return False
    normalized = normalize(museum_name)
    return any(alias in normalized or normalized in alias for alias in NGA_MUSEUM_ALIASES)


def is_smithsonian_museum(museum_name: str | None) -> bool:
    if not museum_name:
        return False
    normalized = normalize(museum_name)
    return any(alias in normalized or normalized in alias for alias in SMITHSONIAN_MUSEUM_ALIASES)


def is_met_museum(museum_name: str | None) -> bool:
    if not museum_name:
        return False
    normalized = normalize(museum_name)
    return any(alias in normalized or normalized in alias for alias in MET_MUSEUM_ALIASES)


def is_aic_museum(museum_name: str | None) -> bool:
    if not museum_name:
        return False
    normalized = normalize(museum_name)
    return any(alias in normalized or normalized in alias for alias in AIC_MUSEUM_ALIASES)
