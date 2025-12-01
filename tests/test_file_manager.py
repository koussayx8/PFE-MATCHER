import pytest
import shutil
from pathlib import Path
from io import BytesIO
from src.data_management.file_manager import FileManager
from src.data_management.models import UploadedDocument
from src.data_management.database import SessionLocal, init_database

# Setup test environment
TEST_DATA_DIR = Path("tests/data_storage")

@pytest.fixture(scope="module")
def file_manager():
    # Use a separate test directory
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)
    
    manager = FileManager(storage_dir=TEST_DATA_DIR)
    
    # Ensure DB is init
    init_database()
    
    yield manager
    
    # Cleanup
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)

def test_save_and_deduplication(file_manager):
    content = b"Hello World PDF Content"
    file_obj = BytesIO(content)
    filename = "test_doc.pdf"
    
    # 1. Save First Time
    doc_id1 = file_manager.save_file(file_obj, filename, document_type="cv")
    assert doc_id1 is not None
    
    # Verify DB
    session = SessionLocal()
    doc1 = session.query(UploadedDocument).get(doc_id1)
    assert doc1.original_filename == filename
    assert doc1.mime_type == "application/pdf" # mimetypes.guess_type works on extension
    assert doc1.document_type == "cv"
    
    # Verify Disk
    path1 = Path(doc1.file_path)
    assert path1.exists()
    assert path1.read_bytes() == content
    
    # Verify Sharding (simple check that it's not in root)
    assert path1.parent != TEST_DATA_DIR
    
    session.close()
    
    # 2. Save Duplicate
    file_obj.seek(0)
    doc_id2 = file_manager.save_file(file_obj, "duplicate_name.pdf", document_type="other")
    
    assert doc_id2 == doc_id1 # Should return same ID
    
def test_cleanup_orphans(file_manager):
    # Create a dummy file in storage that isn't in DB
    orphan_path = TEST_DATA_DIR / "orphan.txt"
    orphan_path.write_text("I am lost")
    
    count = file_manager.cleanup_orphans()
    assert count >= 1
    assert not orphan_path.exists()
