from database.crud import list_resumes

resumes = list_resumes()

for resume in resumes:

    print()

    print(resume.id)

    print(resume.candidate_name)

    print(resume.email)