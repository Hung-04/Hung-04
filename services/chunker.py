from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_text(text)

    # Lọc chunk quá ngắn (ít hơn 50 ký tự — thường là header, số trang)
    chunks = [c.strip() for c in chunks if len(c.strip()) >= 50]
    return chunks