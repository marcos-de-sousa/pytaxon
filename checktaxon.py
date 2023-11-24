import pandas as pd
import numpy as np
import argparse
from approxmatch import process_taxonomic_data
from taxonclassification import taxonomic_classification


# Read the taxonomic data spreadsheet, modified to filter out invalid fields
def read_spreadsheet(file_name, taxon_fields):
    df = pd.read_excel(file_name)
    df = df[list(taxon_fields)].replace({np.nan: None})  # Replace NaN with None
    return df.to_dict(orient='records')


# Combine suggestions from approxmatch and taxonclassification modules with enumeration
def combine_suggestions(approxmatch_errors, taxonclassification_errors):
    combined_errors = {}
    for error in approxmatch_errors + taxonclassification_errors:
        key = (error['error_Line'], error['wrong_name'], error['field_with_error'])
        if key not in combined_errors:
            combined_errors[key] = []
        combined_errors[key].extend(error['suggestions'].split(' or '))

    # Remove duplicate suggestions and enumerate suggestions sequentially
    for key in combined_errors:
        unique_suggestions = list(dict.fromkeys(combined_errors[key]))
        numbered_suggestions = [f"{i+1}-{suggestion}" for i, suggestion in enumerate(unique_suggestions)]
        combined_errors[key] = numbered_suggestions

    return [
        {'Error Line': line, 'Wrong Name': name, 'Field with Error': field, 'Suggestions': ' or '.join(suggestions)}
        for (line, name, field), suggestions in combined_errors.items()
    ]


# Generate taxonomic error report with a specific column order
def generate_error_report(data, output_file, database=None):
    approxmatch_errors = process_taxonomic_data(data)
    taxonclassification_errors = taxonomic_classification(data, database)
    total_errors = combine_suggestions(approxmatch_errors, taxonclassification_errors)

    # Creating the DataFrame with an additional 'option' field
    df = pd.DataFrame(total_errors)
    df['option'] = 0  # Add the 'option' column with the value 0 for all rows

    # Reordering columns according to the new specified sequence
    df = df[['Error Line', 'Wrong Name', 'Field with Error', 'option', 'Suggestions']]

    df.to_excel(output_file, index=False)


# Main execution with CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check taxonomic data from a spreadsheet.')
    parser.add_argument('-i', '--input', required=True, help='Input spreadsheet file name')
    parser.add_argument('-r', '--fields', nargs='+', required=True, help='Taxonomic fields order: kingdom phylum class order family genus species')
    parser.add_argument('-o', '--output', required=True, help='Output spreadsheet file name')
    # Adding argument for the reference database
    parser.add_argument('-db', '--database', required=False, default=None, choices=['gbif', 'ncbi'], help='Reference database for taxonomic classification (GBIF, NCBI, or both if not specified)')

    args = parser.parse_args()

    # Reorganize the fields based on user input
    taxon_fields = args.fields
    file_name = args.input
    output_file = args.output
    database = args.database  # Argument for the database

    data = read_spreadsheet(file_name, taxon_fields)
    generate_error_report(data, output_file, database)
