from pathlib import Path
from app.core.container import Container

def main() -> None:
    container = Container()
    ingest_svc = container.get_ingestion_service()
    
    docs_dir = Path(__file__).resolve().parent / "data" / "sample_docs"
    md_files = sorted(docs_dir.glob("*.md"))
    
    if not md_files:
        print(f"No markdown files found in {docs_dir}")
        return
        
    print(f"Found {len(md_files)} markdown files in {docs_dir}:")
    for file in md_files:
        count = ingest_svc.ingest_file(str(file))
        print(f"  [+] Ingested {file.name}: {count} chunks indexed.")

if __name__ == "__main__":
    main()

