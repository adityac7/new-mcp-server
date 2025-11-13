#!/usr/bin/env python3
"""
Fix Existing Dataset - Profile all unprocessed datasets
"""
from dotenv import load_dotenv
load_dotenv()

from app.database import get_db
from app.models import Dataset, DatasetSchema
from profile_dataset import profile_dataset_sync


def fix_all_datasets():
    """Profile all datasets that have no schema"""
    db = next(get_db())

    try:
        # Get all datasets
        datasets = db.query(Dataset).filter(Dataset.is_active == True).all()

        if not datasets:
            print("❌ No datasets found")
            return

        print(f"Found {len(datasets)} active dataset(s)")
        print("=" * 60)

        for dataset in datasets:
            # Check if dataset has schema
            schema_count = db.query(DatasetSchema).filter(
                DatasetSchema.dataset_id == dataset.id
            ).count()

            if schema_count == 0:
                print(f"\n📊 Dataset {dataset.id}: {dataset.name}")
                print(f"   Status: No schema found, profiling...")

                result = profile_dataset_sync(dataset.id)

                if result["success"]:
                    print(f"   ✅ Profiled: {result['tables']} tables, {result['columns']} columns")
                else:
                    print(f"   ❌ Failed: {result['error']}")
            else:
                print(f"\n✓ Dataset {dataset.id}: {dataset.name}")
                print(f"   Already profiled: {schema_count} columns")

        print()
        print("=" * 60)
        print("✅ Done!")

    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Fixing existing datasets...")
    print()
    fix_all_datasets()
