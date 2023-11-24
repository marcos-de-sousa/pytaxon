import requests
from pygbif import species
from Bio import Entrez


def get_ott_lineage(taxon_name):
    # Request to obtain the OTT ID of the taxon
    data = {"names": [taxon_name]}
    response = requests.post("https://api.opentreeoflife.org/v3/tnrs/match_names", json=data)
    if response.status_code != 200:
        raise Exception(f"Error while getting OTT ID: {response.status_code}")

    results = response.json()
    if not results["results"] or not results["results"][0]["matches"]:
        print(f"No matches found for {taxon_name}")
        return None, [], {}, []

    ott_id = results["results"][0]["matches"][0]["taxon"]["ott_id"]

    # Request to get information about the taxon
    data = {
        "ott_id": ott_id,
        "include_lineage": True,
        "include_children": False,
        "include_synonyms": True
    }
    response = requests.post("https://api.opentreeoflife.org/v3/taxonomy/taxon_info", json=data)
    if response.status_code != 200:
        raise Exception(f"Error while getting taxon info: {response.status_code}")

    taxon_info = response.json()
    synonyms = taxon_info.get('synonyms', [])
    tax_sources = taxon_info.get('tax_sources', [])

    lineage = taxon_info.get('lineage', [])
    lineage_dict = {item['rank']: item['name'] for item in lineage if 'rank' in item}

    ranks = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
    formatted_lineage = {rank: lineage_dict.get(rank, None) for rank in ranks}

    return ott_id, synonyms, formatted_lineage, tax_sources


def get_gbif_lineage(gbif_id):
    try:
        species_info = species.name_usage(key=gbif_id, data='all')
    except Exception as e:
        print(f"Error occurred while fetching GBIF data: {e}")
        return None

    if species_info:
        lineage_dict = {
            'kingdom': species_info.get('kingdom'),
            'phylum': species_info.get('phylum'),
            'class': species_info.get('class'),
            'order': species_info.get('order'),
            'family': species_info.get('family'),
            'genus': species_info.get('genus'),
            'species': species_info.get('species')
        }
        return lineage_dict
    else:
        return None


def get_ncbi_lineage(ncbi_id):
    Entrez.email = "YourEmail@example.com"  # Replace with your email
    try:
        handle = Entrez.efetch(db="taxonomy", id=ncbi_id, retmode="xml")
        records = Entrez.read(handle)
    except Exception as e:
        print(f"Error occurred while fetching NCBI data: {e}")
        return None

    if records:
        lineage = records[0]['LineageEx'] + [records[0]]  # Includes the taxon's own level
        lineage_dict = {item['Rank']: item['ScientificName'] for item in lineage if 'Rank' in item}

        ranks = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
        filled_lineage = {rank: lineage_dict.get(rank, None) for rank in ranks}

        return filled_lineage
    else:
        return None


def taxonomic_classification(taxonomic_data, database=None):
    error_records = []

    for index, row in enumerate(taxonomic_data, start=2):  # Starts line numbering from 2
        taxon_name = None
        for taxon_level in ['species', 'genus', 'family', 'order', 'class', 'phylum', 'kingdom']:
            if row.get(taxon_level) and row[taxon_level] not in ['NaN', 'nan', '']:
                taxon_name = row[taxon_level]
                break
        if taxon_name:
            ott_id, synonyms, detailed_lineage, tax_sources = get_ott_lineage(taxon_name)
            if ott_id is None:
                continue  # Skip to the next line if no match is found

            gbif_id = None
            ncbi_id = None
            if database is None or database == 'gbif':
                gbif_id = next((source.split(':')[-1] for source in tax_sources if source.startswith('gbif:')), None)
            if database is None or database == 'ncbi':
                ncbi_id = next((source.split(':')[-1] for source in tax_sources if source.startswith('ncbi:')), None)

            for field in ['kingdom', 'phylum', 'class', 'order', 'family', 'genus']:
                if row.get(field) and row[field] not in ['NaN', 'nan', '']:
                    wrong_name = row[field]

                    if gbif_id:
                        gbif_lineage = get_gbif_lineage(gbif_id)
                        if gbif_lineage and gbif_lineage[field] and gbif_lineage[field] != wrong_name:
                            suggestion = f"Taxonomic classification of {taxon_name} [name: {gbif_lineage[field]}] ott_id: {ott_id} | tax_sources: gbif:{gbif_id}"
                            error_records.append({
                                'error_Line': index,
                                'wrong_name': wrong_name,
                                'field_with_error': field,
                                'suggestions': suggestion
                            })

                    if ncbi_id:
                        ncbi_lineage = get_ncbi_lineage(ncbi_id)
                        if ncbi_lineage and ncbi_lineage[field] and ncbi_lineage[field] != wrong_name:
                            suggestion = f"Taxonomic classification of {taxon_name} [name: {ncbi_lineage[field]}] ott_id: {ott_id} | tax_sources: ncbi:{ncbi_id}"
                            error_records.append({
                                'error_Line': index,
                                'wrong_name': wrong_name,
                                'field_with_error': field,
                                'suggestions': suggestion
                            })

    return error_records
