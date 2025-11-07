import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
from pypdf import PdfReader
from tqdm import tqdm

load_dotenv()

# --- Configuration ---
REPORTS_DIR = "reports"
DB_PATH = "db"
COLLECTION_NAME = "steel_reports_v2"
EMBEDDING_MODEL = "models/text-embedding-004"
CHUNK_SIZE = 2000 # Larger chunks for more context
CHUNK_OVERLAP = 300

# --- API Configuration ---
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")
genai.configure(api_key=GOOGLE_API_KEY)

def get_or_create_collection():
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection

def process_and_embed_pdfs():
    collection = get_or_create_collection()
    
    # Walk through the directory structure: reports/CompanyName/report.pdf
    all_files_to_process = []
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
    
    for company_name in os.listdir(REPORTS_DIR):
        company_path = os.path.join(REPORTS_DIR, company_name)
        if os.path.isdir(company_path):
            for pdf_file in os.listdir(company_path):
                if pdf_file.endswith(".pdf"):
                    all_files_to_process.append((company_name, pdf_file))

    if not all_files_to_process:
        print(f"No PDF files found in company subdirectories of '{REPORTS_DIR}'.")
        print("Please follow the 'reports/CompanyName/file.pdf' structure.")
        return

    print(f"Found {len(all_files_to_process)} PDF files to process.")

    for company_name, pdf_file in tqdm(all_files_to_process, desc="Processing PDFs"):
        pdf_path = os.path.join(REPORTS_DIR, company_name, pdf_file)
        
        try:
            reader = PdfReader(pdf_path)
            text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
            if not text:
                print(f"Warning: Could not extract text from {pdf_file}.")
                continue
        except Exception as e:
            print(f"Error reading {pdf_file}: {e}")
            continue

        chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP)]

        print(f"\nEmbedding {len(chunks)} chunks for {pdf_file}...")
        try:
            # Batch embedding for efficiency
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=chunks,
                task_type="RETRIEVAL_DOCUMENT"
            )
            embeddings = result['embedding']
            
            ids = [f"{company_name}_{pdf_file}_{i}" for i in range(len(chunks))]
            metadatas = [{"company": company_name, "source": pdf_file} for _ in chunks]
            
            collection.add(embeddings=embeddings, documents=chunks, metadatas=metadatas, ids=ids)
        except Exception as e:
            print(f"An error occurred during embedding for {pdf_file}: {e}")
            
    print("\nPDF processing and embedding complete.")
    print(f"Total documents in collection: {collection.count()}")

if __name__ == "__main__":
    process_and_embed_pdfs()