# vCard to CSV Converter (Turkish phones only)

Lightweight Python tool that scans the current directory for a `.vcf` file, normalizes Turkish phone numbers, and exports a CSV that is easier to open in spreadsheets.

## Features

- automatically picks the first `*.vcf` file in the directory (user confirmation required)
- estimates size and vCard count before processing so you can cancel on large files
- normalizes phone numbers to the `0 (###) ### ## ##` format when the number is Turkish
- exports all names, organizations, phones, and emails to a CSV with enough columns for the widest card

## Requirements

- Python 3.11 or newer (uses `Path` union types and other modern features)

## Usage

1. Place your `.vcf` file in the same folder as `convert.py`.
2. Run `python convert.py`.
3. Confirm the prompt if the detected file is the one you want to convert.
4. The script writes a semicolon-delimited CSV next to the `.vcf` file (`example.csv`, `example_1.csv`, etc.).

```bash
python convert.py
```

Results look like this for every card:

| Order | Name | Fullname | Org | Tel1 | Email1 | …
| ----- | ---- | -------- | --- | ---- | ------ | --- |
| 1 | Ada Bell | Ada Bell | Example Consulting | 0 (532) 111 22 33 | ada.bell@example.com | … |

## Example data

The repo includes `example.vcf`, which contains Turkish contacts with mixed mobile/landline numbers that can be used to verify normalization and CSV output.

## Notes

- Only the first `.vcf` file is processed; move or rename additional files if needed.
- Malformed cards are skipped and reported at the end.
