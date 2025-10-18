#!/usr/bin/env python3
"""
Load sample data into cloud PostgreSQL database
"""
import os
import sys
import psycopg2

def load_data_from_local():
    """Export data from local PostgreSQL and load to cloud"""
    
    # Get cloud database URL from environment
    cloud_db_url = os.getenv('DATABASE_URL')
    if not cloud_db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Fix postgres:// to postgresql://
    if cloud_db_url.startswith('postgres://'):
        cloud_db_url = cloud_db_url.replace('postgres://', 'postgresql://', 1)
    
    print("Connecting to local database...")
    local_conn = psycopg2.connect(
        dbname='analytics_db',
        user='analytics_user',
        password='analytics_pass',
        host='localhost',
        port='5432'
    )
    
    print("Connecting to cloud database...")
    cloud_conn = psycopg2.connect(cloud_db_url)
    
    local_cur = local_conn.cursor()
    cloud_cur = cloud_conn.cursor()
    
    # Create table in cloud database
    print("Creating table in cloud database...")
    create_table_query = """
    CREATE TABLE IF NOT EXISTS digital_insights (
        id SERIAL PRIMARY KEY,
        vtionid VARCHAR(255),
        package VARCHAR(255),
        duration_sum INTEGER,
        event_count INTEGER,
        event_time_range VARCHAR(255),
        day_of_week VARCHAR(255),
        app_name VARCHAR(255),
        cat VARCHAR(255),
        genre VARCHAR(255),
        date DATE,
        population VARCHAR(255),
        age_bucket VARCHAR(255),
        nccs_class VARCHAR(255),
        gender VARCHAR(255),
        state_grp VARCHAR(255),
        weights FLOAT,
        type VARCHAR(255)
    );
    """
    cloud_cur.execute(create_table_query)
    cloud_conn.commit()
    print("Table created successfully")
    
    # Fetch data from local database
    print("Fetching data from local database...")
    local_cur.execute("""
        SELECT vtionid, package, duration_sum, event_count, event_time_range,
               day_of_week, app_name, cat, genre, date, population, age_bucket,
               nccs_class, gender, state_grp, weights, type
        FROM digital_insights
    """)
    
    # Insert data in batches
    print("Inserting data into cloud database...")
    batch_size = 10000
    total_rows = 0
    
    insert_query = """
    INSERT INTO digital_insights (
        vtionid, package, duration_sum, event_count, event_time_range,
        day_of_week, app_name, cat, genre, date, population, age_bucket,
        nccs_class, gender, state_grp, weights, type
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    batch = []
    for row in local_cur:
        batch.append(row)
        
        if len(batch) >= batch_size:
            cloud_cur.executemany(insert_query, batch)
            cloud_conn.commit()
            total_rows += len(batch)
            print(f"Inserted {total_rows} rows...")
            batch = []
    
    # Insert remaining rows
    if batch:
        cloud_cur.executemany(insert_query, batch)
        cloud_conn.commit()
        total_rows += len(batch)
        print(f"Inserted {total_rows} rows...")
    
    # Create indexes
    print("Creating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_date ON digital_insights(date);",
        "CREATE INDEX IF NOT EXISTS idx_type ON digital_insights(type);",
        "CREATE INDEX IF NOT EXISTS idx_cat ON digital_insights(cat);",
        "CREATE INDEX IF NOT EXISTS idx_age_bucket ON digital_insights(age_bucket);",
        "CREATE INDEX IF NOT EXISTS idx_gender ON digital_insights(gender);",
        "CREATE INDEX IF NOT EXISTS idx_state_grp ON digital_insights(state_grp);",
    ]
    
    for index_query in indexes:
        cloud_cur.execute(index_query)
    cloud_conn.commit()
    print("Indexes created successfully")
    
    # Verify the data
    cloud_cur.execute("SELECT COUNT(*) FROM digital_insights;")
    count = cloud_cur.fetchone()[0]
    print(f"\nData migration complete! Total rows in cloud database: {count}")
    
    # Close connections
    local_cur.close()
    local_conn.close()
    cloud_cur.close()
    cloud_conn.close()

if __name__ == "__main__":
    try:
        load_data_from_local()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

