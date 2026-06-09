from datetime import datetime
import time

from pdf_processor import ask_llm, process_document


COMMANDS = {
    "summary": "Provide a detailed summary of this document.",
    "overview": "Give a high level overview of this document.",
    "purpose": "What is the main purpose and objective of this document?",
    "features": "List all key features and capabilities described.",
    "architecture": "Explain the system architecture described in the document.",
    "techstack": "List all technologies, frameworks, APIs, databases and tools mentioned.",
    "usecases": "List all use cases and applications mentioned.",
    "benefits": "List the benefits and advantages of the proposed solution.",
    "future": "List future enhancements and future scope discussed.",
    "keywords": "Extract the most important keywords from the document.",
}


def main():
    document_path = input("Enter PDF/DOC/DOCX path: ").strip().strip('"')
    document = process_document(document_path)
    messages = []

    print("\n========== DOCUMENT LOADED ==========")
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
            print("\n========== DOCUMENT STATS ==========")
            print(f"Pages: {document['page_count'] or 'N/A'}")
            print(f"Characters: {document['character_count']}")
            print(f"Chunks: {document['chunk_count']}")
            continue

        if command == "chunks":
            print("\n========== CHUNK INFO ==========")
            for chunk in document["chunks"]:
                print(f"Chunk {chunk['chunk_number']}: {chunk['size']} characters | {chunk['section']}")
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
            similarity = chunk["similarity"]
            score = f"{similarity:.3f}" if similarity is not None else "N/A"
            print(f"- {chunk['document_name']} chunk {chunk['chunk_number']} | {chunk['section']} | similarity {score}")
        print(f"\nResponse generated in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
