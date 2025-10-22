"""
Edit column descriptions for metadata
"""

from app.database import get_db
from app.models import Dataset

# Your descriptions
DESCRIPTIONS = {
    "digital_insights": {
        "id": "Unique record identifier",
        "vtionid": "Vtion platform user ID",
        "package": "App package name (e.g., com.app.name)",
        "app_name": "Human-readable app name",
        "cat": "App category",
        "genre": "App genre/subcategory",
        "type": "Event type",
        "date": "Event date (YYYY-MM-DD)",
        "day_of_week": "Day of week (Monday, Tuesday, etc.)",
        "event_time_range": "Time range when event occurred",
        "event_count": "Number of events",
        "duration_sum": "Total duration in seconds",
        "age_bucket": "User age group (e.g., 18-24, 25-34)",
        "gender": "User gender",
        "state_grp": "State/region group",
        "population": "Population type (Urban/Rural)",
        "nccs_class": "NCCS socioeconomic classification (A, B, C, D, E)",
        "weights": "Statistical weight for population representation"
    }
}

def update_metadata():
    db = next(get_db())
    dataset = db.query(Dataset).filter(Dataset.id == 2).first()

    # Rebuild metadata text with descriptions
    md_lines = [
        f"# {dataset.name}\n",
        f"Consumer digital insights panel data with demographics and app usage metrics.\n",
        f"---\n"
    ]

    for table_name, columns_desc in DESCRIPTIONS.items():
        md_lines.append(f"\n## Table: `{table_name}`\n")
        md_lines.append(f"**{len(columns_desc)} columns**\n")
        md_lines.append("\n| Column | Type | Nullable | Description |")
        md_lines.append("\n|--------|------|----------|-------------|")

        # Get column info from database
        from app.models import DatasetSchema
        schemas = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == 2,
            DatasetSchema.table_name == table_name
        ).order_by(DatasetSchema.column_name).all()

        for col in schemas:
            nullable = "Yes" if col.is_nullable else "No"
            description = columns_desc.get(col.column_name, "No description")
            md_lines.append(f"\n| `{col.column_name}` | {col.data_type} | {nullable} | {description} |")

        md_lines.append("\n")

    dataset.metadata_text = "".join(md_lines)
    dataset.description = "Consumer digital insights panel data"
    db.commit()

    print("✅ Descriptions updated!")
    print(f"\nPreview:\n{dataset.metadata_text[:800]}...")

if __name__ == "__main__":
    update_metadata()
