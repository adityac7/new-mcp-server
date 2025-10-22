"""
Fix encryption - re-encrypt the connection string with the current ENCRYPTION_KEY
"""
import sys
sys.path.insert(0, '/home/ubuntu/new-mcp-server')

from app.database import get_db
from app.models import Dataset
from app.encryption import get_encryption_manager

# The actual connection string (not encrypted)
CONNECTION_STRING = "postgresql://analytics_db_clug_user:sa1jEkjEmuIKRxQu3x6Oa83Ep4AWGSAM@dpg-d3pmmtali9vc73bn81i0-a.singapore-postgres.render.com/analytics_db_clug"

def fix_encryption():
    db = next(get_db())
    try:
        dataset = db.query(Dataset).filter(Dataset.id == 1).first()
        
        if not dataset:
            print("ERROR: Dataset ID 1 not found")
            return False
        
        print(f"Found dataset: {dataset.name}")
        
        # Encrypt with current key
        encryption_manager = get_encryption_manager()
        encrypted = encryption_manager.encrypt(CONNECTION_STRING)
        
        print(f"Encrypted connection string (first 50 chars): {encrypted[:50]}...")
        
        # Update the dataset
        dataset.connection_string_encrypted = encrypted
        db.commit()
        
        print("✓ Successfully updated encrypted connection string")
        
        # Test decryption
        decrypted = encryption_manager.decrypt(encrypted)
        if decrypted == CONNECTION_STRING:
            print("✓ Decryption test passed")
            return True
        else:
            print("✗ Decryption test failed")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = fix_encryption()
    exit(0 if success else 1)

