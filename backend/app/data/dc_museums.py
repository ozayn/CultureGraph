from pydantic import BaseModel


class DCMuseum(BaseModel):
    name: str
    city: str
    neighborhood: str | None = None
    website: str | None = None
    type: str | None = None


DC_MUSEUMS: list[DCMuseum] = [
    DCMuseum(
        name="National Gallery of Art",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://www.nga.gov",
        type="Art museum",
    ),
    DCMuseum(
        name="Smithsonian American Art Museum",
        city="Washington, DC",
        neighborhood="Penn Quarter",
        website="https://americanart.si.edu",
        type="Art museum",
    ),
    DCMuseum(
        name="National Portrait Gallery",
        city="Washington, DC",
        neighborhood="Penn Quarter",
        website="https://npg.si.edu",
        type="Art museum",
    ),
    DCMuseum(
        name="Hirshhorn Museum and Sculpture Garden",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://hirshhorn.si.edu",
        type="Art museum",
    ),
    DCMuseum(
        name="National Museum of Asian Art",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://asia.si.edu",
        type="Art museum",
    ),
    DCMuseum(
        name="National Museum of African Art",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://africa.si.edu",
        type="Art museum",
    ),
    DCMuseum(
        name="National Museum of African American History and Culture",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://nmaahc.si.edu",
        type="History museum",
    ),
    DCMuseum(
        name="National Museum of American History",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://americanhistory.si.edu",
        type="History museum",
    ),
    DCMuseum(
        name="National Museum of Natural History",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://naturalhistory.si.edu",
        type="Natural history museum",
    ),
    DCMuseum(
        name="National Air and Space Museum",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://airandspace.si.edu",
        type="Science museum",
    ),
    DCMuseum(
        name="National Museum of the American Indian",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://americanindian.si.edu",
        type="History museum",
    ),
    DCMuseum(
        name="Renwick Gallery",
        city="Washington, DC",
        neighborhood="Penn Quarter",
        website="https://americanart.si.edu/visit/renwick",
        type="Art museum",
    ),
    DCMuseum(
        name="Phillips Collection",
        city="Washington, DC",
        neighborhood="Dupont Circle",
        website="https://www.phillipscollection.org",
        type="Art museum",
    ),
    DCMuseum(
        name="Kreeger Museum",
        city="Washington, DC",
        neighborhood="Foxhall",
        website="https://www.kreegermuseum.org",
        type="Art museum",
    ),
    DCMuseum(
        name="Hillwood Estate, Museum & Gardens",
        city="Washington, DC",
        neighborhood="Van Ness",
        website="https://www.hillwoodmuseum.org",
        type="Historic house museum",
    ),
    DCMuseum(
        name="Dumbarton Oaks",
        city="Washington, DC",
        neighborhood="Georgetown",
        website="https://www.doaks.org",
        type="Research museum",
    ),
    DCMuseum(
        name="Museum of the Bible",
        city="Washington, DC",
        neighborhood="Southwest",
        website="https://www.museumofthebible.org",
        type="Religious museum",
    ),
    DCMuseum(
        name="National Building Museum",
        city="Washington, DC",
        neighborhood="Penn Quarter",
        website="https://nbm.org",
        type="Design museum",
    ),
    DCMuseum(
        name="United States Holocaust Memorial Museum",
        city="Washington, DC",
        neighborhood="National Mall",
        website="https://www.ushmm.org",
        type="Memorial museum",
    ),
    DCMuseum(
        name="Library of Congress",
        city="Washington, DC",
        neighborhood="Capitol Hill",
        website="https://www.loc.gov",
        type="Library",
    ),
    DCMuseum(
        name="Folger Shakespeare Library",
        city="Washington, DC",
        neighborhood="Capitol Hill",
        website="https://www.folger.edu",
        type="Library",
    ),
]


def search_dc_museums(query: str, *, limit: int = 10) -> list[DCMuseum]:
    needle = query.strip().casefold()
    if not needle:
        return []

    matches = [museum for museum in DC_MUSEUMS if needle in museum.name.casefold()]
    return matches[:limit]
