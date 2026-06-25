import hashlib

from database.crud import create_resume

dummy_resume = {
    "resume_hash": hashlib.sha256(b"dummy resume").hexdigest(),

    "original_file_name": "Ajay_Resume.pdf",

    "stored_file_name": "861bb1f1-c906-418d.pdf",

    "file_path": "uploads/pdf/861bb1f1-c906-418d.pdf",

    "mime_type": "application/pdf",

    "candidate_name": "Ajay Gopan G",

    "email": "ajaygops320@gmail.com",

    "phone_number": "9495464131",

    "skills": [
        "Python",
        "React",
        "PostgreSQL"
    ],

    "cities": [
        "Bengaluru",
        "Trivandrum"
    ],

    "fresher": False,

    "processing_status": "COMPLETED",

    "is_verified": False,

    "extraction_status": "SUCCESS",

    "notes": None,
}

resume = create_resume(dummy_resume)

print("\nResume inserted successfully!\n")

print("UUID :", resume.id)
print("Candidate :", resume.candidate_name)
print("Email :", resume.email)