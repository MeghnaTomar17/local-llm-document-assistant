from database.crud import get_resume_by_id

resume = get_resume_by_id(
    "450942ad-7491-48ea-9da4-27a043838ce5"
)

print(resume.candidate_name)
print(resume.email)