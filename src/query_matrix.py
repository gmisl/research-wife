"""Generate country/language/product search queries for the research runner."""

from __future__ import annotations

from dataclasses import dataclass


COUNTRIES = {
    'AT': ('Austria', ['de']), 'BE': ('Belgium', ['nl', 'fr']), 'BG': ('Bulgaria', ['bg']),
    'HR': ('Croatia', ['hr']), 'CY': ('Cyprus', ['el']), 'CZ': ('Czechia', ['cs']),
    'DK': ('Denmark', ['da']), 'EE': ('Estonia', ['et']), 'FI': ('Finland', ['fi']),
    'FR': ('France', ['fr']), 'DE': ('Germany', ['de']), 'GR': ('Greece', ['el']),
    'HU': ('Hungary', ['hu']), 'IE': ('Ireland', ['en']), 'IT': ('Italy', ['it']),
    'LV': ('Latvia', ['lv']), 'LT': ('Lithuania', ['lt']), 'LU': ('Luxembourg', ['fr', 'de']),
    'MT': ('Malta', ['en']), 'NL': ('Netherlands', ['nl']), 'PL': ('Poland', ['pl']),
    'PT': ('Portugal', ['pt']), 'RO': ('Romania', ['ro']), 'SK': ('Slovakia', ['sk']),
    'SI': ('Slovenia', ['sl']), 'ES': ('Spain', ['es']), 'SE': ('Sweden', ['sv']),
}

TERMS = {
    'en': ('organic', 'frozen minced {meat}', 'producer wholesale bulk pallet'),
    'de': ('bio', 'tiefgekühltes Hackfleisch {meat}', 'Hersteller Großhandel Bulk Palette'),
    'fr': ('bio', 'viande hachée {meat} surgelée', 'producteur grossiste vrac palette'),
    'nl': ('biologisch', 'diepgevroren gehakt {meat}', 'producent groothandel bulk pallet'),
    'bg': ('био', 'замразена кайма {meat}', 'производител едро палет'),
    'hr': ('ekološko', 'smrznuto mljeveno meso {meat}', 'proizvođač veleprodaja paleta'),
    'el': ('βιολογικό', 'κατεψυγμένος κιμάς {meat}', 'παραγωγός χονδρική παλέτα'),
    'cs': ('bio', 'mražené mleté maso {meat}', 'výrobce velkoobchod paleta'),
    'da': ('økologisk', 'frosset hakket {meat}', 'producent engros palle'),
    'et': ('mahe', 'külmutatud hakkliha {meat}', 'tootja hulgimüük alus'),
    'fi': ('luomu', 'pakastettu jauheliha {meat}', 'tuottaja tukkumyynti lava'),
    'hu': ('bio', 'fagyasztott darált {meat}', 'gyártó nagykereskedelem raklap'),
    'it': ('biologico', 'carne {meat} macinata surgelata', 'produttore ingrosso pallet'),
    'lv': ('bioloģiska', 'saldēta malta {meat} gaļa', 'ražotājs vairumtirdzniecība palete'),
    'lt': ('ekologiška', 'šaldyta malta {meat} mėsa', 'gamintojas didmeninė prekyba paletė'),
    'pl': ('ekologiczna', 'mrożone mięso mielone {meat}', 'producent hurt paleta'),
    'pt': ('biológica', 'carne {meat} picada congelada', 'produtor grossista palete'),
    'ro': ('ecologică', 'carne tocată {meat} congelată', 'producător en-gros palet'),
    'sk': ('bio', 'mrazené mleté mäso {meat}', 'výrobca veľkoobchod paleta'),
    'sl': ('ekološko', 'zamrznjeno mleto meso {meat}', 'proizvajalec veleprodaja paleta'),
    'es': ('ecológica', 'carne picada {meat} congelada', 'productor mayorista palé'),
    'sv': ('ekologisk', 'fryst färs {meat}', 'producent grossist pall'),
}


@dataclass(frozen=True)
class SearchQuery:
    country_code: str
    country_name: str
    language_code: str
    product_family: str
    query: str


def generate_queries() -> list[SearchQuery]:
    queries = []
    for code, (country, languages) in COUNTRIES.items():
        for language in [*languages, 'en']:
            organic, product, wholesale = TERMS.get(language, TERMS['en'])
            for family, meat in [('beef', 'beef'), ('chicken', 'chicken')]:
                queries.append(SearchQuery(code, country, language, family, f'{organic} {product.format(meat=meat)} {wholesale} {country}'))
    return queries


if __name__ == '__main__':
    for item in generate_queries():
        print(f'{item.country_code}\t{item.language_code}\t{item.product_family}\t{item.query}')
