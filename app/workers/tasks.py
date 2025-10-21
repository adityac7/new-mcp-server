"""
Background tasks for schema profiling and LLM metadata generation
Enhanced with weight column detection and NCCS awareness
"""
import os
from typing import List, Dict
from openai import OpenAI
from app.workers.celery_app import celery_app
from app.database import get_db_context, get_dataset_connection
from app.models import Dataset, DatasetSchema, Metadata
from app.encryption import get_encryption_manager
from app.services.weighting_service import weighting_service

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


@celery_app.task(name='app.workers.tasks.profile_dataset_schema')
def profile_dataset_schema(dataset_id: int) -> Dict:
    """
    Profile a dataset's schema and store in database
    
    Args:
        dataset_id: ID of the dataset to profile
    
    Returns:
        Dict with status and results
    """
    with get_db_context() as db:
        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return {'success': False, 'error': 'Dataset not found'}
        
        # Decrypt connection string
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)
        
        # Connect to dataset database
        try:
            conn = get_dataset_connection(connection_string)
            cur = conn.cursor()
            
            # Get all tables (skip internal tables)
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name NOT IN ('query_logs', 'datasets', 'dataset_schemas', 'metadata')
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            total_columns = 0
            weight_column_detected = None
            nccs_column_detected = None
            all_columns = []

            # For each table, get schema
            for table_name in tables:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))

                columns = cur.fetchall()
                table_column_names = [col[0] for col in columns]
                all_columns.extend(table_column_names)

                # Detect weight column in this table
                if not weight_column_detected:
                    detected_weight = weighting_service.detect_weight_column(table_column_names)
                    if detected_weight:
                        weight_column_detected = f"{table_name}.{detected_weight}"

                # Detect NCCS column in this table
                if not nccs_column_detected:
                    detected_nccs = weighting_service.detect_nccs_column(table_column_names)
                    if detected_nccs:
                        nccs_column_detected = f"{table_name}.{detected_nccs}"

                # Store schema information
                for column_name, data_type, is_nullable in columns:
                    # Check if schema entry already exists
                    existing = db.query(DatasetSchema).filter(
                        DatasetSchema.dataset_id == dataset_id,
                        DatasetSchema.table_name == table_name,
                        DatasetSchema.column_name == column_name
                    ).first()

                    if not existing:
                        schema_entry = DatasetSchema(
                            dataset_id=dataset_id,
                            table_name=table_name,
                            column_name=column_name,
                            data_type=data_type,
                            is_nullable=(is_nullable == 'YES')
                        )
                        db.add(schema_entry)
                        total_columns += 1

                db.commit()

            # Update dataset with detected columns
            if weight_column_detected:
                dataset.description = (dataset.description or "") + f"\n[Weight column: {weight_column_detected}]"
                db.commit()

            if nccs_column_detected:
                dataset.description = (dataset.description or "") + f"\n[NCCS column: {nccs_column_detected}]"
                db.commit()
            
            cur.close()
            conn.close()

            return {
                'success': True,
                'tables_found': len(tables),
                'columns_profiled': total_columns,
                'weight_column': weight_column_detected,
                'nccs_column': nccs_column_detected
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


@celery_app.task(name='app.workers.tasks.generate_llm_metadata')
def generate_llm_metadata(dataset_id: int, table_name: str) -> Dict:
    """
    Generate AI-powered metadata for a table's columns
    
    Args:
        dataset_id: ID of the dataset
        table_name: Name of the table to generate metadata for
    
    Returns:
        Dict with status and results
    """
    with get_db_context() as db:
        # Get dataset and schema
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return {'success': False, 'error': 'Dataset not found'}
        
        # Get all columns for this table
        columns = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id,
            DatasetSchema.table_name == table_name
        ).all()
        
        if not columns:
            return {'success': False, 'error': 'No columns found for table'}
        
        # Prepare column info for LLM
        column_info = []
        for col in columns:
            column_info.append({
                'name': col.column_name,
                'type': col.data_type,
                'nullable': col.is_nullable
            })
        
        # Generate metadata using OpenAI
        try:
            # Check if this is panel data with weighting
            has_weight_hint = "Weight column" in (dataset.description or "")
            has_nccs_hint = "NCCS column" in (dataset.description or "")

            weight_context = ""
            if has_weight_hint:
                weight_context = "\n\n**IMPORTANT**: This is panel data with weighting. Include notes about weight columns and proper usage."

            nccs_context = ""
            if has_nccs_hint:
                nccs_context = "\n**NCCS Merging**: A1→A, C/D/E→C/D/E (socioeconomic classes)"

            prompt = f"""You are a data analyst specializing in consumer panel data. Given this database table schema, provide a SHORT (max 10 words) description for each column.

Table: {table_name}
Dataset: {dataset.name}
{weight_context}
{nccs_context}

Columns:
{chr(10).join([f"- {col['name']} ({col['type']})" for col in column_info])}

Respond in JSON format:
{{
  "column_name": "short description",
  ...
}}

Keep descriptions crisp and technical. Focus on what the data represents. For weight columns, mention "Population weight" or similar."""

            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a data analyst providing concise column descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse response
            import json
            metadata_json = response.choices[0].message.content
            
            # Extract JSON from markdown code blocks if present
            if '```json' in metadata_json:
                metadata_json = metadata_json.split('```json')[1].split('```')[0].strip()
            elif '```' in metadata_json:
                metadata_json = metadata_json.split('```')[1].split('```')[0].strip()
            
            metadata_dict = json.loads(metadata_json)
            
            # Store metadata
            stored_count = 0
            for column_name, description in metadata_dict.items():
                # Check if metadata already exists
                existing = db.query(Metadata).filter(
                    Metadata.dataset_id == dataset_id,
                    Metadata.table_name == table_name,
                    Metadata.column_name == column_name
                ).first()
                
                if existing:
                    existing.description = description
                    existing.model_used = "gpt-4.1-mini"
                else:
                    metadata_entry = Metadata(
                        dataset_id=dataset_id,
                        table_name=table_name,
                        column_name=column_name,
                        description=description,
                        model_used="gpt-4.1-mini"
                    )
                    db.add(metadata_entry)
                
                stored_count += 1
            
            db.commit()
            
            return {
                'success': True,
                'columns_processed': stored_count,
                'table': table_name
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


@celery_app.task(name='app.workers.tasks.process_new_dataset')
def process_new_dataset(dataset_id: int) -> Dict:
    """
    Complete processing pipeline for a new dataset:
    1. Profile schema
    2. Generate LLM metadata for all tables
    
    Args:
        dataset_id: ID of the dataset to process
    
    Returns:
        Dict with status and results
    """
    # Step 1: Profile schema
    profile_result = profile_dataset_schema(dataset_id)
    
    if not profile_result.get('success'):
        return profile_result
    
    # Step 2: Generate metadata for each table
    with get_db_context() as db:
        # Get all unique tables for this dataset
        tables = db.query(DatasetSchema.table_name).filter(
            DatasetSchema.dataset_id == dataset_id
        ).distinct().all()
        
        metadata_results = []
        for (table_name,) in tables:
            result = generate_llm_metadata(dataset_id, table_name)
            metadata_results.append(result)
    
    return {
        'success': True,
        'profile': profile_result,
        'metadata': metadata_results
    }

