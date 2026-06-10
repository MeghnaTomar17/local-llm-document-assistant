from datetime import datetime
import time

from pdf_processor import ask_llm, process_document


COMMANDS = {
    "summary": "Summarize the resume.",
    "contact": "Show contact information from the resume.",
    "skills": "Show skills from the resume.",
    "technical": "Show technical skills from the resume.",
    "education": "Show education from the resume.",
    "experience": "Show experience from the resume.",
    "projects": "Show projects from the resume.",
    "certifications": "Show certifications from the resume.",
    "achievements": "Show achievements from the resume.",
    "languages": "Show languages from the resume.",
    "highlights": "List the career highlights from the resume.",
    "recruiter": "Write a concise recruiter summary using only the resume.",
}


def main():
    document_path = input("Enter PDF/DOCX resume path: ").strip().strip('"')
    document = process_document(document_path)
    messages = []

    print("\n========== RESUME LOADED ==========")
    print(f"Name: {document['name']}")
    print(f"Pages: {document['page_count'] or 'N/A'}")
    print(f"Characters extracted: {document['character_count']}")
    print(f"Chunks created: {document['chunk_count']}")
    print("=====================================\n")

    print("Available commands:")
    print(", ".join(sorted(COMMANDS)))
    print("stats, chunks, help, exit")
    print("\nYou may also ask any natural-language question.")

    while True:
        question = input("\nAsk a question: ").strip()
        command = question.lower()

        if command == "exit":
            print("\nGoodbye!")
            break

        if command == "help":
            print(", ".join(sorted(COMMANDS)))
            print("stats, chunks, help, exit")
            continue

        if command == "stats":
            print("\n========== RESUME STATS ==========")
            print(f"Pages: {document['page_count'] or 'N/A'}")
            print(f"Characters: {document['character_count']}")
            print(f"Chunks: {document['chunk_count']}")
            continue

        if command == "chunks":
            print("\n========== CHUNK INFO ==========")
            for chunk in document["chunks"]:
                print(
                    f"Chunk {chunk['chunk_number']}: {chunk['size']} characters | "
                    f"{chunk['section']} | {chunk['title']} | Page {chunk['page'] or 'N/A'}"
                )
            continue

        question = COMMANDS.get(command, question)
        if not question:
            continue

        messages.append(
            {
                "role": "user",
                "content": question,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )

        start = time.time()
        result = ask_llm(question, document, messages)
        elapsed = time.time() - start

        messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "retrieval": result["retrieval"],
            }
        )

        print("\n========== ANSWER ==========\n")
        print(result["answer"])
        print("\n========== SOURCES ==========")
        print(f"Chunks used: {result['retrieval']['chunk_count']}")
        print(f"Context size: {result['retrieval']['context_size']} characters")
        for chunk in result["retrieval"]["chunks"]:
            similarity = chunk.get("similarity")
            score = f"{similarity:.3f}" if similarity is not None else "N/A"
            print(
                f"- {chunk['document_name']} chunk {chunk['chunk_number']} | "
                f"{chunk['section']} | {chunk.get('title') or chunk['section']} | "
                f"Page {chunk.get('page') or 'N/A'} | similarity {score}"
            )
        print(f"\nResponse generated in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
