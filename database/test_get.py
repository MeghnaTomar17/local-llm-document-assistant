import hashlib

from database.crud import get_resume_by_hash

resume_hash = hashlib.sha256(
    b"dummy resume"
).hexdigest()

resume = get_resume_by_hash(resume_hash)

if resume:

    print("Resume Found!\n")

    print("Candidate :", resume.candidate_name)

    print("Email :", resume.email)

    print("UUID :", resume.id)

else:

    print("Resume not found.")