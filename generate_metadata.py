"""
Generate metadata_text for datasets
This creates a markdown summary of the schema that gets returned to LLM in ONE call
"""

import sys
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Dataset, DatasetSchema

def generate_metadata_text(dataset_id: int):
    """Generate markdown metadata for a dataset"""

    db = next(get_db())

    # Get dataset
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        print(f"❌ Dataset {dataset_id} not found")
        return

    print(f"📝 Generating metadata for: {dataset.name}")

    # Get all schemas grouped by table
    schemas = db.query(DatasetSchema).filter(
        DatasetSchema.dataset_id == dataset_id
    ).order_by(DatasetSchema.table_name, DatasetSchema.column_name).all()

    # Group by table
    tables = {}
    for schema in schemas:
        if schema.table_name not in tables:
            tables[schema.table_name] = []
        tables[schema.table_name].append(schema)

    # Filter out metadata tables
    metadata_tables = ['datasets', 'dataset_schemas', 'metadata', 'query_logs']
    filtered_tables = {k: v for k, v in tables.items() if k not in metadata_tables}

    if not filtered_tables:
        print("⚠️  Warning: No user data tables found (all tables are metadata tables)")
        print("   This means you connected to the metadata database instead of your data database")
        return

    # Build markdown
    md_lines = [
        f"# {dataset.name}\n",
        f"{dataset.description or 'No description provided'}\n",
        f"---\n"
    ]

    for table_name, columns in filtered_tables.items():
        md_lines.append(f"\n## Table: `{table_name}`\n")
        md_lines.append(f"**{len(columns)} columns**\n")
        md_lines.append("\n| Column | Type | Nullable | Description |")
        md_lines.append("\n|--------|------|----------|-------------|")

        for col in columns:
            nullable = "Yes" if col.is_nullable else "No"
            # TODO: Add column descriptions (user can manually edit or add via UI)
            description = "Add description here"
            md_lines.append(f"\n| `{col.column_name}` | {col.data_type} | {nullable} | {description} |")

        md_lines.append("\n")

    metadata_text = "".join(md_lines)

    # Update dataset
    dataset.metadata_text = metadata_text
    db.commit()

    print(f"✅ Metadata generated ({len(metadata_text)} characters)")
    print(f"\nPreview:\n")
    print(metadata_text[:500] + "..." if len(metadata_text) > 500 else metadata_text)
    print(f"\n🎉 Dataset '{dataset.name}' metadata ready!")
    print(f"   - {len(filtered_tables)} tables (metadata tables filtered out)")
    print(f"   - {sum(len(cols) for cols in filtered_tables.values())} columns")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_metadata.py <dataset_id>")
        print("\nAvailable datasets:")
        db = next(get_db())
        datasets = db.query(Dataset).all()
        for d in datasets:
            print(f"  ID {d.id}: {d.name}")
        sys.exit(1)

    dataset_id = int(sys.argv[1])
    generate_metadata_text(dataset_id)
