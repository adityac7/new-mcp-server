"""
Generate AI-powered metadata for dataset columns
Uses OpenAI GPT-4.1-mini to create meaningful descriptions
"""

import sys
import os
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session
from app.database import get_db, get_dataset_connection
from app.models import Dataset, DatasetSchema, Metadata
from app.encryption import get_encryption_manager
import psycopg2

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_sample_values(connection_string: str, table_name: str, column_name: str, limit: int = 10):
    """Get sample values from a column"""
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        
        # Get sample values (non-null, distinct)
        cur.execute(f"""
            SELECT DISTINCT "{column_name}" 
            FROM {table_name} 
            WHERE "{column_name}" IS NOT NULL 
            LIMIT {limit}
        """)
        
        samples = [str(row[0]) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return samples
    except Exception as e:
        print(f"  Warning: Could not get samples for {column_name}: {e}")
        return []


def generate_column_description(table_name: str, column_name: str, data_type: str, sample_values: list) -> str:
    """Generate AI description for a column"""
    
    # Create prompt for GPT
    prompt = f"""You are analyzing a dataset for senior brand managers at large companies who make strategic decisions about media spend allocation and ecommerce strategy.

Table: {table_name}
Column: {column_name}
Data Type: {data_type}
Sample Values: {', '.join(sample_values[:5]) if sample_values else 'No samples available'}

Generate a concise, business-focused description (1-2 sentences) that:
1. Explains what this column represents
2. Highlights its relevance for strategic analysis
3. Uses professional, executive-level language

Description:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data analyst helping executives understand analytics datasets. Be concise and strategic."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        description = response.choices[0].message.content.strip()
        return description
    
    except Exception as e:
        print(f"  Error generating description: {e}")
        return f"Column storing {data_type} data"


def generate_dataset_summary(dataset_name: str, tables: dict) -> str:
    """Generate overall dataset summary using AI"""
    
    # Build context about the dataset
    table_info = []
    for table_name, columns in tables.items():
        col_names = [col['column_name'] for col in columns[:10]]  # First 10 columns
        table_info.append(f"- {table_name}: {len(columns)} columns ({', '.join(col_names[:5])}...)")
    
    prompt = f"""You are analyzing a dataset for senior brand managers at large companies.

Dataset: {dataset_name}
Tables and Columns:
{chr(10).join(table_info)}

Generate a brief, strategic overview (2-3 sentences) that:
1. Describes what this dataset contains
2. Explains its value for media planning and ecommerce strategy
3. Highlights key metrics available for analysis

Overview:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data strategist helping executives understand the business value of datasets."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    
    except Exception as e:
        print(f"  Error generating summary: {e}")
        return f"Analytics dataset with {len(tables)} tables for strategic analysis."


def generate_metadata(dataset_id: int):
    """Generate AI metadata for all columns in a dataset"""
    
    db = next(get_db())
    
    try:
        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            print(f"❌ Dataset {dataset_id} not found")
            return
        
        print(f"\n{'='*80}")
        print(f"📊 Generating AI Metadata for: {dataset.name}")
        print(f"{'='*80}\n")
        
        # Get connection string
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)
        if connection_string.startswith('postgres://'):
            connection_string = connection_string.replace('postgres://', 'postgresql://', 1)
        
        # Get all schemas grouped by table
        schemas = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id
        ).order_by(DatasetSchema.table_name, DatasetSchema.column_name).all()
        
        # Group by table
        tables = {}
        for schema in schemas:
            if schema.table_name not in tables:
                tables[schema.table_name] = []
            tables[schema.table_name].append({
                'column_name': schema.column_name,
                'data_type': schema.data_type,
                'is_nullable': schema.is_nullable
            })
        
        # Filter out metadata tables
        metadata_tables = ['datasets', 'dataset_schemas', 'metadata', 'query_logs']
        filtered_tables = {k: v for k, v in tables.items() if k not in metadata_tables}
        
        if not filtered_tables:
            print("⚠️  No user data tables found")
            return
        
        print(f"Found {len(filtered_tables)} tables with {sum(len(cols) for cols in filtered_tables.values())} columns\n")
        
        # Generate dataset summary
        print("🤖 Generating dataset summary...")
        dataset_summary = generate_dataset_summary(dataset.name, filtered_tables)
        print(f"✅ Summary: {dataset_summary}\n")
        
        # Update dataset description if empty
        if not dataset.description or dataset.description == "No description":
            dataset.description = dataset_summary
            db.commit()
            print("✅ Updated dataset description\n")
        
        # Generate metadata for each column
        total_columns = sum(len(cols) for cols in filtered_tables.values())
        current = 0
        
        for table_name, columns in filtered_tables.items():
            print(f"\n📋 Processing table: {table_name} ({len(columns)} columns)")
            print("-" * 80)
            
            for col in columns:
                current += 1
                column_name = col['column_name']
                data_type = col['data_type']
                
                print(f"  [{current}/{total_columns}] {column_name} ({data_type})...", end=" ")
                
                # Check if metadata already exists
                existing = db.query(Metadata).filter(
                    Metadata.dataset_id == dataset_id,
                    Metadata.table_name == table_name,
                    Metadata.column_name == column_name
                ).first()
                
                if existing and existing.description:
                    print("⏭️  (already exists)")
                    continue
                
                # Get sample values
                sample_values = get_sample_values(connection_string, table_name, column_name)
                
                # Generate description
                description = generate_column_description(table_name, column_name, data_type, sample_values)
                
                # Save to database
                if existing:
                    existing.description = description
                    existing.model_used = "gpt-4o-mini"
                else:
                    metadata = Metadata(
                        dataset_id=dataset_id,
                        table_name=table_name,
                        column_name=column_name,
                        description=description,
                        model_used="gpt-4o-mini"
                    )
                    db.add(metadata)
                
                db.commit()
                print("✅")
        
        print(f"\n{'='*80}")
        print(f"✅ Metadata generation complete!")
        print(f"{'='*80}\n")
        
        # Generate metadata_text for the dataset
        print("📝 Generating metadata_text summary...")
        
        md_lines = [
            f"# {dataset.name}\n",
            f"{dataset.description}\n",
            "---\n"
        ]
        
        for table_name, columns in filtered_tables.items():
            md_lines.append(f"\n## Table: {table_name}\n")
            md_lines.append(f"**Columns**: {len(columns)}\n\n")
            md_lines.append("| Column | Type | Description |\n")
            md_lines.append("|--------|------|-------------|\n")
            
            for col in columns:
                # Get metadata
                meta = db.query(Metadata).filter(
                    Metadata.dataset_id == dataset_id,
                    Metadata.table_name == table_name,
                    Metadata.column_name == col['column_name']
                ).first()
                
                desc = meta.description if meta else "No description"
                md_lines.append(f"| `{col['column_name']}` | {col['data_type']} | {desc} |\n")
        
        metadata_text = "".join(md_lines)
        dataset.metadata_text = metadata_text
        db.commit()
        
        print("✅ metadata_text saved to dataset\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_ai_metadata.py <dataset_id>")
        sys.exit(1)
    
    dataset_id = int(sys.argv[1])
    generate_metadata(dataset_id)

