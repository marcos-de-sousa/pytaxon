import pandas as pd
import requests
import json


# Function to suggest correct names
def suggest_correct_names(species_name, limit=3):
    data = json.dumps({
        "names": [species_name],
        "do_approximate_matching": True
    })
    response = requests.post("https://api.opentreeoflife.org/v3/tnrs/match_names", data=data)
    if response.status_code == 200:
        match_results = response.json()
        suggestions = []
        for match in match_results.get("results", []):
            for match_entry in match.get("matches", []):
                suggestion = match_entry.get("taxon", {})
                suggestion['score'] = round(match_entry.get('score', 0), 3)
                suggestion['ott_id'] = match_entry.get('taxon', {}).get('ott_id', 'No ID')
                suggestions.append(suggestion)
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:limit]
    else:
        raise Exception(f"Error while getting name suggestions: {response.status_code}")


# Function to get taxon information including synonyms
def get_taxon_info_with_synonyms(ott_id):
    data = json.dumps({
        "ott_id": ott_id,
        "include_lineage": False,
        "include_children": False,
        "include_synonyms": True
    })
    response = requests.post(
        "https://api.opentreeoflife.org/v3/taxonomy/taxon_info",
        data=data
    )
    if response.status_code == 200:
        taxon_info = response.json()
        synonyms = taxon_info.get('synonyms', [])
        return synonyms
    else:
        raise Exception(f"Error while getting taxon info: {response.status_code}")


# Helper function to format suggestions for output
def format_suggestions(suggestions):
    formatted_suggestions = []
    for sug in suggestions:
        synonyms_list = get_taxon_info_with_synonyms(sug['ott_id']) if sug['ott_id'] != 'No ID' else []
        synonyms_str = f", synonym: {', '.join(synonyms_list)}" if synonyms_list else ""
        formatted_suggestion = f"Approximate matching [name: {sug['unique_name']}{synonyms_str}] score: {sug['score']:.3f} | ott_id: {sug['ott_id']} | tax_sources: {' | '.join(sug['tax_sources'])}"
        formatted_suggestions.append(formatted_suggestion)
    return ' or '.join(formatted_suggestions)


# Function to check taxon names
def check_taxon_names(row, taxon_fields):
    corrections = []
    for field in taxon_fields:
        taxon_name = row.get(field)
        if taxon_name and taxon_name not in ['NaN', 'nan', '']:  # Check if the field is valid
            suggestions = suggest_correct_names(taxon_name)
            if suggestions and suggestions[0]['score'] < 1:  # If the match is not exact
                formatted_suggestions = format_suggestions(suggestions)
                correction = {
                    "error_Line": row.get('line_number'),  # Line number
                    "wrong_name": taxon_name,
                    "field_with_error": field,
                    "suggestions": formatted_suggestions
                }
                corrections.append(correction)
    return corrections


# Function to process the list of taxonomic data
def process_taxonomic_data(data_list):
    taxon_fields = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
    corrections_report = []

    for index, row in enumerate(data_list, start=2):  # Adjusts line numbering to start from 2
        row['line_number'] = index
        corrections = check_taxon_names(row, taxon_fields)
        corrections_report.extend(corrections)

    return corrections_report


