import hashlib
import shutil
import logging
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from src.data_management.models import UploadedDocument
from src.data_management.database import SessionLocal
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, storage_dir: Path = DATA_DIR / "storage"):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _calculate_hash(self, file_obj) -> str:
        """Calculate SHA256 hash of file content."""
        sha256_hash = hashlib.sha256()
        file_obj.seek(0)
        for byte_block in iter(lambda: file_obj.read(4096), b""):
            sha256_hash.update(byte_block)
        file_obj.seek(0)  # Reset pointer
        return sha256_hash.hexdigest()

    def _get_sharded_path(self, file_hash: str) -> Path:
        """Get sharded path: a1/b2/a1b2..."""
        shard1 = file_hash[:2]
        shard2 = file_hash[2:4]
        return self.storage_dir / shard1 / shard2

    def save_file(self, file_obj, original_filename: str, document_type: str = "other") -> Optional[int]:
        """
        Save file to storage with deduplication and sharding.
        Returns the database ID of the document.
        """
        session = SessionLocal()
        try:
            # 1. Calculate Hash
            file_hash = self._calculate_hash(file_obj)
            
            # 2. Check if exists in DB
            existing_doc = session.query(UploadedDocument).filter(UploadedDocument.file_hash == file_hash).first()
            if existing_doc:
                logger.info(f"File {original_filename} already exists (ID: {existing_doc.id})")
                return existing_doc.id
            
            # 3. Prepare Storage Path
            shard_dir = self._get_sharded_path(file_hash)
            shard_dir.mkdir(parents=True, exist_ok=True)
            
            file_ext = Path(original_filename).suffix
            storage_name = f"{file_hash}{file_ext}"
            storage_path = shard_dir / storage_name
            
            # 4. Save to Disk
            with open(storage_path, "wb") as f:
                file_obj.seek(0)
                shutil.copyfileobj(file_obj, f)
            
            # 5. Detect MIME Type
            mime_type, _ = mimetypes.guess_type(original_filename)
                
            # 6. Save to DB
            new_doc = UploadedDocument(
                file_hash=file_hash,
                original_filename=original_filename,
                file_path=str(storage_path),
                file_size=storage_path.stat().st_size,
                mime_type=mime_type,
                document_type=document_type,
                uploaded_at=datetime.now()
            )
            session.add(new_doc)
            session.commit()
            session.refresh(new_doc)
            
            logger.info(f"Saved new file {original_filename} as {storage_name}")
            return new_doc.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save file {original_filename}: {e}")
            return None
        finally:
            session.close()

    def get_file_path(self, document_id: int) -> Optional[Path]:
        """Get absolute path of a stored file by ID."""
        session = SessionLocal()
        try:
            doc = session.query(UploadedDocument).filter(UploadedDocument.id == document_id).first()
            if doc:
                return Path(doc.file_path)
            return None
        finally:
            session.close()

    def delete_file(self, document_id: int) -> bool:
        """Delete file from DB and disk (if no other refs - simplified for now)."""
        session = SessionLocal()
        try:
            doc = session.query(UploadedDocument).filter(UploadedDocument.id == document_id).first()
            if not doc:
                return False
            
            # In a full CAS system, we'd check ref counts. 
            # Here we assume 1:1 for simplicity or manual cleanup.
            # For now, just delete the DB record to "soft delete" or implement full cleanup later.
            # Actually, let's just delete the DB record. The file might be shared.
            # A proper cleanup_orphans method is safer for disk deletion.
            
            session.delete(doc)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
        finally:
            session.close()

    def cleanup_orphans(self):
        """Delete files on disk that are not referenced in the DB."""
        # Get all known file paths from DB
        session = SessionLocal()
        known_paths = set()
        try:
            docs = session.query(UploadedDocument).all()
            for doc in docs:
                known_paths.add(str(Path(doc.file_path).resolve()))
        finally:
            session.close()

        # Walk storage dir
        count = 0
        for path in self.storage_dir.rglob("*"):
            if path.is_file():
                if str(path.resolve()) not in known_paths:
                    try:
                        path.unlink()
                        count += 1
                        logger.info(f"Deleted orphan file: {path}")
                    except Exception as e:
                        logger.error(f"Failed to delete orphan {path}: {e}")
        return count
