import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.document_processing.batch_processor import process_pdfs_parallel

@pytest.fixture
def mock_extract_text():
    with patch("src.document_processing.batch_processor.extract_text_from_pdf") as mock:
        yield mock

def test_process_pdfs_parallel(mock_extract_text):
    # Setup mock
    mock_extract_text.side_effect = lambda p: {"text": f"Content of {p.name}", "method_used": "mock"}
    
    files = [Path(f"file_{i}.pdf") for i in range(5)]
    
    results = process_pdfs_parallel(files, max_workers=2)
    
    assert len(results) == 5
    assert mock_extract_text.call_count == 5
    
    # Check results content
    for res in results:
        assert "Content of file_" in res["text"]
        assert "source_file" in res

def test_process_pdfs_parallel_error_handling(mock_extract_text):
    # Setup mock to fail for one file
    def side_effect(p):
        if "fail" in p.name:
            raise Exception("Processing failed")
        return {"text": "Success", "method_used": "mock"}
    
    mock_extract_text.side_effect = side_effect
    
    files = [Path("good.pdf"), Path("fail.pdf")]
    
    results = process_pdfs_parallel(files)
    
    assert len(results) == 2
    
    success_res = next(r for r in results if r["source_file"] == "good.pdf")
    fail_res = next(r for r in results if r["source_file"] == "fail.pdf")
    
    assert success_res["text"] == "Success"
    assert fail_res["method_used"] == "error"
    assert "Processing failed" in fail_res["error"]
