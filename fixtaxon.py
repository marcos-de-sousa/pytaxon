import pandas as pd
import argparse
import re


def fix_taxonomic_data(input_file, suggestions_file, output_file):
    # Load the spreadsheets
    taxonomic_data = pd.read_excel(input_file)
    suggestions = pd.read_excel(suggestions_file)

    # Check if the 'option' column exists and if it is numeric
    if 'option' not in suggestions.columns or not pd.api.types.is_numeric_dtype(suggestions['option']):
        raise ValueError("The 'option' column does not exist or is not numeric in the suggestions spreadsheet.")

    # Iterate over each row of suggestions
    for _, suggestion in suggestions.iterrows():
        if suggestion['option'] != 0:
            # Extract the number of the chosen suggestion
            suggestion_number = int(suggestion['option'])

            # Find the corresponding suggestion
            # The regular expression was updated to capture "Approximate matching" and "Taxonomic classification"
            suggestion_pattern = rf"{suggestion_number}-(Approximate matching|Taxonomic classification of .*?) \[name: (.*?)\].*"
            matches = re.findall(suggestion_pattern, suggestion['Suggestions'])

            if matches:
                # We choose the last group which should be the scientific name
                chosen_suggestion = matches[0][-1]

                # Update the taxonomic data spreadsheet in the correct cell
                taxonomic_data.loc[suggestion['Error Line'] - 2, suggestion['Field with Error']] = chosen_suggestion

    # Save the new corrected spreadsheet
    taxonomic_data.to_excel(output_file, index=False)


# Command line parser
def main():
    parser = argparse.ArgumentParser(description='Fix Taxonomic Data')
    parser.add_argument('-i', '--input', required=True, help='Input Excel file with taxonomic data')
    parser.add_argument('-s', '--suggestions', required=True, help='Excel file with taxonomic name suggestions')
    parser.add_argument('-o', '--output', required=True, help='Output Excel file for corrected data')
    args = parser.parse_args()

    fix_taxonomic_data(args.input, args.suggestions, args.output)


if __name__ == "__main__":
    main()

