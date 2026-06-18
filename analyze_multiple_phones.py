import re
from pathlib import Path

from pdf_processor import extract_text, ALLOWED_EXTENSIONS

RESUME_FOLDER = Path("training_data/resumes")

phone_pattern = re.compile(
    r'(?:\+?\d[\d\s\-()]{8,}\d)'
)

multi_phone_count = 0

for resume in RESUME_FOLDER.iterdir():

    if resume.suffix.lower() not in ALLOWED_EXTENSIONS:
        continue

    try:
        result = extract_text(resume)

        text = result.get("text", "")

        phones = phone_pattern.findall(text)

        cleaned = []

        for phone in phones:
            digits = re.sub(r"\D", "", phone)

            if re.search(r"20\d{2}", phone):
                continue

            # reject decimal values

            if "." in phone:
                continue

            if 10 <= len(digits) <= 15:
                cleaned.append(phone.strip())

            

        cleaned = list(dict.fromkeys(cleaned))

        if len(cleaned) > 1:
            multi_phone_count += 1

            print("\n" + "=" * 80)
            print(resume.name)
            print("PHONE COUNT:", len(cleaned))

            for p in cleaned:
                print("  ", p)

    except Exception as e:
        print(f"ERROR: {resume.name} -> {e}")

print("\n" + "=" * 80)
print("TOTAL RESUMES WITH MULTIPLE PHONES:", multi_phone_count)