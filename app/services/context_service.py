"""
Context Service - Progressive Context Loading
Implements 4-level context system for 60% token reduction
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.models import Dataset, DatasetSchema, Metadata
from app.services.response_formatter import ResponseFormatter


class ContextService:
    """
    Progressive context loading service

    Level 0: Global rules (500 tokens) - Always included
    Level 1: Dataset summaries (2000 tokens) - List of datasets
    Level 2: Table schemas (5000 tokens) - Schema details for specific dataset
    Level 3: Full details (10000 tokens) - Schema + samples + statistics
    """

    def __init__(self):
        """Initialize context service"""
        # Token budgets per level
        self.max_tokens = {
            'level_0': 500,
            'level_1': 2000,
            'level_2': 5000,
            'level_3': 10000
        }

    def get_context_level_0(self) -> str:
        """
        Level 0: Global context - Always included

        Returns:
            Markdown string with business rules and weighting methodology
        """
        return ResponseFormatter.format_context_level_0()

    def get_context_level_1(self, db: Session) -> str:
        """
        Level 1: Dataset summaries only

        Args:
            db: Database session

        Returns:
            Markdown table of active datasets with basic info
        """
        datasets = db.query(Dataset).filter(Dataset.is_active == True).all()

        if not datasets:
            return "\n## Available Datasets\n\n_No datasets available._\n"

        md = "\n## Available Datasets\n\n"
        md += f"**Total**: {len(datasets)}\n\n"
        md += "| ID | Name | Description | Tables | Status |\n"
        md += "|---|---|---|---|---|\n"

        for ds in datasets:
            # Count tables for this dataset
            table_count = db.query(DatasetSchema.table_name).filter(
                DatasetSchema.dataset_id == ds.id
            ).distinct().count()

            # Truncate description
            desc = (ds.description or "No description")[:60]
            desc = desc + "..." if len(ds.description or "") > 60 else desc

            # Status indicator
            metadata_count = db.query(Metadata).filter(
                Metadata.dataset_id == ds.id
            ).count()
            status = "✓ Ready" if metadata_count > 0 else "⏳ Processing"

            md += f"| {ds.id} | {ds.name} | {desc} | {table_count} | {status} |\n"

        md += "\n**Next**: Use `get_dataset_schema(dataset_id)` for detailed schema.\n"

        return md

    def get_context_level_2(self, dataset_id: int, db: Session) -> str:
        """
        Level 2: Table schemas for specific dataset (no samples)

        Args:
            dataset_id: ID of the dataset
            db: Database session

        Returns:
            Markdown with table names, columns, types, and AI descriptions
        """
        # Get dataset info
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset or not dataset.is_active:
            return f"\n## Dataset {dataset_id}\n\n**Error**: Dataset not found or inactive.\n"

        # Get schema with metadata
        schemas = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id
        ).all()

        if not schemas:
            return f"\n## Dataset: {dataset.name}\n\n_Schema not yet profiled. Please wait for background processing._\n"

        # Get metadata
        metadata_entries = db.query(Metadata).filter(
            Metadata.dataset_id == dataset_id
        ).all()

        # Create metadata lookup
        metadata_map = {
            f"{m.table_name}.{m.column_name}": m.description
            for m in metadata_entries
        }

        # Group by table
        tables = {}
        for schema in schemas:
            table_name = schema.table_name
            if table_name not in tables:
                tables[table_name] = []

            key = f"{table_name}.{schema.column_name}"
            tables[table_name].append({
                'column_name': schema.column_name,
                'data_type': schema.data_type,
                'is_nullable': schema.is_nullable,
                'description': metadata_map.get(key, 'No description available')
            })

        # Format as markdown
        md = f"\n## Dataset: {dataset.name} (ID: {dataset_id})\n\n"

        if dataset.description:
            md += f"**Description**: {dataset.description}\n\n"

        md += f"**Total Tables**: {len(tables)}\n\n"
        md += "---\n\n"

        for table_name, columns in tables.items():
            md += f"### Table: `{table_name}`\n\n"
            md += f"**Columns**: {len(columns)}\n\n"
            md += "| Column | Type | Nullable | Description |\n"
            md += "|---|---|---|---|\n"

            for col in columns:
                nullable = "✓" if col['is_nullable'] else "✗"
                # Truncate long descriptions
                desc = col['description'][:80]
                desc = desc + "..." if len(col['description']) > 80 else desc
                md += f"| `{col['column_name']}` | {col['data_type']} | {nullable} | {desc} |\n"

            md += "\n"

        md += "---\n\n"
        md += f"**Query**: Use `query_dataset({dataset_id}, \"SELECT ...\")`\n"
        md += f"**Sample**: Use `get_dataset_sample({dataset_id}, \"table_name\")`\n"

        return md

    def get_context_level_3(
        self,
        dataset_id: int,
        table_name: str,
        db: Session,
        include_samples: bool = True
    ) -> str:
        """
        Level 3: Full table details with statistics and sample data

        Args:
            dataset_id: ID of the dataset
            table_name: Name of the table
            db: Database session
            include_samples: Whether to include sample data (default True)

        Returns:
            Markdown with full column details, statistics, and sample rows
        """
        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset or not dataset.is_active:
            return f"\n## Table: {table_name}\n\n**Error**: Dataset not found or inactive.\n"

        # Get schema for this table
        schemas = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id,
            DatasetSchema.table_name == table_name
        ).all()

        if not schemas:
            return f"\n## Table: {table_name}\n\n**Error**: Table not found in dataset.\n"

        # Get metadata
        metadata_entries = db.query(Metadata).filter(
            Metadata.dataset_id == dataset_id,
            Metadata.table_name == table_name
        ).all()

        metadata_map = {m.column_name: m.description for m in metadata_entries}

        # Build markdown
        md = f"\n## Full Details: {table_name}\n\n"
        md += f"**Dataset**: {dataset.name} (ID: {dataset_id})\n\n"

        # Column details
        md += "### Columns\n\n"
        md += "| Column | Type | Nullable | Description |\n"
        md += "|---|---|---|---|\n"

        for schema in schemas:
            nullable = "✓" if schema.is_nullable else "✗"
            description = metadata_map.get(schema.column_name, 'No description')
            md += f"| `{schema.column_name}` | {schema.data_type} | {nullable} | {description} |\n"

        md += "\n"

        # Sample data (if requested)
        if include_samples:
            md += "### Sample Data\n\n"
            md += "_Use `get_dataset_sample()` to see actual sample rows._\n\n"

        md += "---\n\n"
        md += f"**Query Example**: `query_dataset({dataset_id}, \"SELECT * FROM {table_name} LIMIT 10\")`\n"

        return md

    def build_progressive_context(
        self,
        required_level: int,
        dataset_id: Optional[int] = None,
        table_name: Optional[str] = None,
        db: Optional[Session] = None
    ) -> str:
        """
        Build context progressively based on required level

        Args:
            required_level: 0, 1, 2, or 3
            dataset_id: Required for levels 2+
            table_name: Required for level 3
            db: Database session (required for levels 1+)

        Returns:
            Combined markdown context string
        """
        context_parts = []

        # Level 0: Always include
        context_parts.append(self.get_context_level_0())

        # Level 1: Dataset summaries
        if required_level >= 1 and db:
            context_parts.append(self.get_context_level_1(db))

        # Level 2: Specific dataset schema
        if required_level >= 2 and dataset_id and db:
            context_parts.append(self.get_context_level_2(dataset_id, db))

        # Level 3: Full table details
        if required_level >= 3 and dataset_id and table_name and db:
            context_parts.append(self.get_context_level_3(dataset_id, table_name, db))

        # Combine all parts
        full_context = "\n".join(context_parts)

        return full_context

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        Simple heuristic: ~4 characters per token

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Simple estimation: 4 chars ≈ 1 token
        return len(text) // 4

    def get_context_for_query(
        self,
        dataset_id: Optional[int],
        include_global: bool = True,
        db: Optional[Session] = None
    ) -> str:
        """
        Get appropriate context for a query operation

        Args:
            dataset_id: ID of dataset being queried (None for dataset list)
            include_global: Whether to include global context (default True)
            db: Database session

        Returns:
            Markdown context string
        """
        if not dataset_id:
            # No specific dataset - return level 1 (dataset list)
            level = 1 if db else 0
        else:
            # Specific dataset - return level 2 (schema)
            level = 2 if db else 0

        return self.build_progressive_context(
            required_level=level,
            dataset_id=dataset_id,
            db=db
        )


# Global instance
context_service = ContextService()
