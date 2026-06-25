import hashlib

from database.crud import save_resume

resume = {

    "resume_hash": hashlib.sha256(
        b"dummy resume"
    ).hexdigest(),

    "original_file_name": "Ajay.pdf",

    "stored_file_name": "abc123.pdf",

    "file_path": "uploads/pdf/abc123.pdf",

    "mime_type": "application/pdf",

    "candidate_name": "Ajay Gopan G",

    "email": "UPDATED_EMAIL@gmail.com",

    "phone_number": "9999999999",

    "skills": [
        "Python",
        "React",
        "FastAPI"
    ],

    "cities": [
        "Bengaluru"
    ],

    "fresher": False,

    "processing_status": "COMPLETED",

    "is_verified": True,

    "extraction_status": "SUCCESS",

    "notes": "Updated by save_resume()"
}

saved = save_resume(resume)

print()

print(saved.id)

print(saved.email)

print(saved.notes)