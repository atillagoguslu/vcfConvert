import csv
from pathlib import Path


def find_first_vcf(directory: Path) -> Path | None:
    vcfs = sorted(directory.glob("*.vcf"))
    for path in vcfs:
        if path.is_file():
            return path
    return None


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(num_bytes)} B"


def estimate_vcard_count(file_path: Path) -> int:
    count = 0
    with file_path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip().upper() == "BEGIN:VCARD":
                count += 1
    return count


def prompt_to_proceed(file_path: Path, size_bytes: int, card_count: int) -> bool:
    human_size = format_size(size_bytes)
    prompt = (
        f"Found {file_path.name}. Size: {size_bytes} bytes ({human_size}). "
        f"Estimated vCards: {card_count}. Process this file? (y/n) [y]: "
    )
    response = input(prompt).strip().lower()
    return response in {"y", "yes"} or response == ""


def clean_value(value: str) -> str:
    return value.replace("\r", "").replace("\n", "").strip()


def format_name_from_n(n_value: str) -> str:
    parts = n_value.split(";")
    family = parts[0].strip() if len(parts) > 0 else ""
    given = parts[1].strip() if len(parts) > 1 else ""
    name_parts = [part for part in [given, family] if part]
    return " ".join(name_parts)


TURKISH_MOBILE_AREA_CODES = {str(code) for code in range(501, 561)}

TURKISH_LANDLINE_AREA_CODES = {str(code) for code in range(212, 491, 2)}


def extract_digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def remove_turkish_country_code(digits: str) -> str:
    if digits.startswith("90") and len(digits) >= 12:
        return digits[2:]
    return digits


def is_turkish_mobile_area_code(area_code: str) -> bool:
    return area_code in TURKISH_MOBILE_AREA_CODES


def is_turkish_landline_area_code(area_code: str) -> bool:
    return area_code in TURKISH_LANDLINE_AREA_CODES


def is_turkish_phone(digits: str) -> bool:
    if len(digits) == 11 and digits.startswith("0"):
        area_code = digits[1:4]
    elif len(digits) == 10:
        area_code = digits[:3]
    else:
        return False
    return is_turkish_mobile_area_code(area_code) or is_turkish_landline_area_code(
        area_code
    )


def format_turkish_phone(digits: str) -> str:
    if not digits:
        return ""
    candidate = remove_turkish_country_code(digits)
    if candidate.startswith("0"):
        normalized = candidate
    else:
        normalized = f"0{candidate}"
    if len(normalized) != 11:
        return ""
    area_code = normalized[1:4]
    if not (
        is_turkish_mobile_area_code(area_code)
        or is_turkish_landline_area_code(area_code)
    ):
        return ""
    return (
        f"0 ({normalized[1:4]}) "
        f"{normalized[4:7]} {normalized[7:9]} {normalized[9:11]}"
    )


def normalize_and_format_tel(value: str) -> str:
    original = value
    digits = extract_digits(value)
    if not digits:
        return original
    candidate = remove_turkish_country_code(digits)
    if not is_turkish_phone(candidate):
        return original
    formatted = format_turkish_phone(candidate)
    return formatted or original


def is_tel_key(key_upper: str) -> bool:
    return key_upper == "TEL" or key_upper.endswith(".TEL")


def is_email_key(key_upper: str) -> bool:
    return key_upper == "EMAIL" or key_upper.endswith(".EMAIL")


def parse_card_lines(lines: list[str]) -> dict | None:
    card = {"name": "", "fullname": "", "org": "", "tels": [], "emails": []}
    for line in lines:
        if ":" not in line:
            continue
        key_part, value = line.split(":", 1)
        value = clean_value(value)
        key_base = key_part.split(";", 1)[0]
        key_upper = key_base.upper()

        if key_upper == "FN":
            card["fullname"] = value
        elif key_upper == "N":
            card["name"] = format_name_from_n(value)
        elif key_upper == "ORG":
            card["org"] = value.replace("\\,", ",")
        elif is_tel_key(key_upper):
            card["tels"].append(normalize_and_format_tel(value))
        elif is_email_key(key_upper):
            card["emails"].append(value)

    return card


def parse_vcards(file_path: Path) -> tuple[list[dict], int]:
    cards: list[dict] = []
    skipped = 0
    in_card = False
    current_lines: list[str] = []

    with file_path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue

            if line.startswith((" ", "\t")):
                if current_lines:
                    current_lines[-1] += line.lstrip(" \t")
                else:
                    current_lines.append(line.lstrip(" \t"))
                continue

            normalized = line.strip()
            if normalized.upper() == "BEGIN:VCARD":
                if in_card:
                    skipped += 1
                    current_lines = []
                in_card = True
                current_lines = []
                continue
            if normalized.upper() == "END:VCARD":
                if in_card:
                    card = parse_card_lines(current_lines)
                    if card is None:
                        skipped += 1
                    else:
                        cards.append(card)
                else:
                    skipped += 1
                in_card = False
                current_lines = []
                continue

            if in_card:
                current_lines.append(line)

    if in_card:
        skipped += 1

    return cards, skipped


def unique_output_path(input_path: Path) -> Path:
    base_path = input_path.with_suffix(".csv")
    if not base_path.exists():
        return base_path
    counter = 1
    while True:
        candidate = base_path.with_name(f"{base_path.stem}_{counter}{base_path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def write_csv(output_path: Path, cards: list[dict]) -> None:
    max_tel = max((len(card["tels"]) for card in cards), default=0)
    max_email = max((len(card["emails"]) for card in cards), default=0)

    header = ["Order", "Name", "Fullname", "Org"]
    header.extend([f"Tel{i}" for i in range(1, max_tel + 1)])
    header.extend([f"Email{i}" for i in range(1, max_email + 1)])

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)

        for index, card in enumerate(cards, start=1):
            row = [index, card["name"], card["fullname"], card["org"]]
            row.extend(
                card["tels"][i] if i < len(card["tels"]) else ""
                for i in range(max_tel)
            )
            row.extend(
                card["emails"][i] if i < len(card["emails"]) else ""
                for i in range(max_email)
            )
            writer.writerow(row)


def main() -> None:
    directory = Path.cwd()
    vcf_path = find_first_vcf(directory)
    if not vcf_path:
        print("No .vcf files found in the current directory.")
        return

    size_bytes = vcf_path.stat().st_size
    estimated_cards = estimate_vcard_count(vcf_path)

    if not prompt_to_proceed(vcf_path, size_bytes, estimated_cards):
        print("Conversion cancelled.")
        return

    cards, skipped = parse_vcards(vcf_path)
    output_path = unique_output_path(vcf_path)
    write_csv(output_path, cards)

    print(
        f"CSV written to {output_path.name}. "
        f"Processed {len(cards)} vCards, skipped {skipped} malformed vCards."
    )


if __name__ == "__main__":
    main()
