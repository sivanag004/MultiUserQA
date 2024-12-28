import os,re,sys
import json
import faiss
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load model globally
model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')#("all-mpnet-base-v2")

# def extract_text_from_pdf(pdf_path):
#     reader = PdfReader(pdf_path)
#     text = ""
#     for page in reader.pages:
#         text += page.extract_text()
#     return text
def extract_text_from_pdf(pdf_file):
    extracted_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            try:
                extracted_text += page.extract_text()
            except UnicodeDecodeError:
                extracted_text += page.extract_text(encoding="latin1")
    return extracted_text

def preprocess_document(pdf_text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=5)
    chunks = text_splitter.split_text(pdf_text)
    return chunks

def clean_extracted_text(text):
    # Remove common metadata patterns or invalid characters
    clean_text = re.sub(r"/[A-Za-z0-9]+ [0-9]+ [0-9]+ R", "", text)  # Remove object references
    clean_text = re.sub(r"[\n\r]+", " ", clean_text)  # Replace newlines with space
    clean_text = re.sub(r"[^a-zA-Z0-9\s.,;:?!()%-]", "", clean_text)  # Keep alphanumeric and punctuation
    return clean_text.strip()
def create_embeddings(documents_dir, metadata_path, index_path):
    metadata = []
    corpus = []
    filenames = []

    for filename in os.listdir(documents_dir):
        if filename.endswith(".pdf"):
            filepath = os.path.join(documents_dir, filename)
            text = extract_text_from_pdf(filepath)
            corpus.append(text)
            filenames.append(filename)

    # Generate embeddings
    embeddings = model.encode(corpus, convert_to_tensor=False)

    # Save metadata
    metadata = [{"filename": filenames[i], "content": corpus[i]} for i in range(len(filenames))]
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

    # Save FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    faiss.write_index(index, index_path)

def search(query, index_path, metadata_path, user_files):
    # Load index and metadata
    index = faiss.read_index(index_path)
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    # Validate index and metadata alignment
    if len(metadata) != index.ntotal:
        raise ValueError("Index and metadata sizes do not match!")
    
    # Generate query embedding
    query_vector = model.encode([query], convert_to_tensor=False)

    # Search in FAISS
    distances, indices = index.search(query_vector, k=20)
    results = []
    # for idx in indices[0]:
    #     if idx < len(metadata):  # Check index bounds
    #         doc_metadata = metadata[idx]
    #         if doc_metadata["filename"] in user_files:  # Filter by authorized files
    #             results.append(doc_metadata)
    for i in indices[0]:
        if i < len(metadata) and metadata[i]["filename"] in user_files:
            results.append(metadata[i])

    return results
