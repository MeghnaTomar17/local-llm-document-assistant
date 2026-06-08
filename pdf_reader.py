from pypdf import PdfReader
import requests
import time

# Load PDF

pdf_path = input("Enter PDF path: ")

try:
    reader = PdfReader(pdf_path)
except Exception as e:
    print(f"\nError opening PDF: {e}")
    exit()

text = ""

for page in reader.pages:
    page_text = page.extract_text()
    if page_text:
        text += page_text + "\n"

print("\n========== PDF LOADED ==========")
print(f"Pages: {len(reader.pages)}")
print(f"Characters extracted: {len(text)}")


# Chunking

chunk_size = 1000
chunks = []

for i in range(0, len(text), chunk_size):
    chunks.append(text[i:i + chunk_size])

print(f"Chunks created: {len(chunks)}")
print("================================\n")


# Simple Retrieval Function

def retrieve_relevant_chunks(question, chunks, top_k=3):
    question_words = question.lower().split()

    scored_chunks = []

    for chunk in chunks:
        score = 0

        chunk_lower = chunk.lower()

        for word in question_words:
            if word in chunk_lower:
                score += 1

        scored_chunks.append((score, chunk))

    scored_chunks.sort(reverse=True, key=lambda x: x[0])

    relevant_chunks = [
        chunk
        for score, chunk in scored_chunks[:top_k]
        if score > 0
    ]

    if not relevant_chunks:
        relevant_chunks = chunks[:2]

    return "\n".join(relevant_chunks)


# Interactive Q&A Loop

print("\nAvailable Commands:")
print(" summary      -> Summarize document")
print(" overview     -> High-level overview")
print(" purpose      -> Main objective of document")
print(" features     -> Extract key features")
print(" architecture -> System architecture")
print(" techstack    -> Technologies used")
print(" usecases     -> Business use cases")
print(" benefits     -> Benefits and advantages")
print(" future       -> Future enhancements")
print(" keywords     -> Important keywords")
print(" stats        -> Document statistics")
print(" chunks       -> Chunk information")
print(" help         -> Show commands")
print(" exit         -> Quit")
print("\nYou may also ask any natural-language question.")

while True:

    question = input("\nAsk a question: ")

    if question.lower() == "exit":
        print("\nGoodbye!")
        break

    # Built-in shortcuts

    if question.lower() == "summary":
        question = "Provide a detailed summary of this document."

    elif question.lower() == "overview":
        question = "Give a high level overview of this document."

    elif question.lower() == "purpose":
        question = "What is the main purpose and objective of this document?"

    elif question.lower() == "features":
        question = "List all key features and capabilities described."

    elif question.lower() == "architecture":
        question = "Explain the system architecture described in the document."

    elif question.lower() == "techstack":
        question = "List all technologies, frameworks, APIs, databases and tools mentioned."

    elif question.lower() == "usecases":
        question = "List all use cases and applications mentioned."

    elif question.lower() == "benefits":
        question = "List the benefits and advantages of the proposed solution."

    elif question.lower() == "future":
        question = "List future enhancements and future scope discussed."

    elif question.lower() == "keywords":
        question = "Extract the most important keywords from the document."

    elif question.lower() == "stats":
        print("\n========== DOCUMENT STATS ==========")
        print(f"Pages: {len(reader.pages)}")
        print(f"Characters: {len(text)}")
        print(f"Chunks: {len(chunks)}")
        continue

    elif question.lower() == "chunks":
        print("\n========== CHUNK INFO ==========")

        for i, chunk in enumerate(chunks):
            print(f"Chunk {i+1}: {len(chunk)} characters")

        continue

    elif question.lower() == "help":
        print("summary, overview, purpose, features, architecture")
        print("techstack, usecases, benefits, future, keywords")
        print("stats, chunks, help, exit")
        continue

    # Retrieve relevant chunks

    relevant_context = retrieve_relevant_chunks(question, chunks)

    print("\nRetrieved Context Size:", len(relevant_context))
    
    prompt = f"""
    You are a document assistant.

    Answer ONLY using the information present in the document.

    DOCUMENT:
    {relevant_context}

    QUESTION:
    {question}
    """

    start = time.time()

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2:3b",
            "prompt": prompt,
            "stream": False
        }
    )

    end = time.time()

    print("\n========== ANSWER ==========\n")
    print(response.json()["response"])

    print("\n============================")
    print(f"Response generated in {end - start:.2f} seconds")