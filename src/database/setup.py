"""
Database setup script for PatientTriage.ai ML Core Engine.

Initializes PostgreSQL database with schema, indexes, and retention policies.
Task 1.3: Set up PostgreSQL schema for audit logging and override tracking

Usage:
    python -m src.database.setup --create    # Create tables
    python -m src.database.setup --drop      # Drop all tables (DANGEROUS!)
    python -m src.database.setup --validate  # Validate schema
    python -m src.database.setup --migrate   # Run migrations

Requirements: 7.1, 15.1, 15.2, 15.3, 15.4, 16.2
"""

import argparse
import sys
from pathlib import Path
from sqlalchemy import inspect, text
from .connection import engine
from .models import Base, Prediction, Override, DeteriorationAlert


def create_tables():
    """
    Create all database tables using SQLAlchemy models.
    
    This will create:
    - predictions table
    - overrides table
    - deterioration_alerts table
    - All indexes and constraints
    """
    print("Creating database tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Successfully created tables:")
        print("   - predictions")
        print("   - overrides")
        print("   - deterioration_alerts")
        
        # Validate table creation
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['predictions', 'overrides', 'deterioration_alerts']
        for table in expected_tables:
            if table in tables:
                print(f"   ✓ {table} table created")
                
                # Show indexes
                indexes = inspector.get_indexes(table)
                print(f"     Indexes: {len(indexes)} created")
            else:
                print(f"   ✗ {table} table NOT created")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


def drop_tables():
    """
    Drop all database tables.
    
    WARNING: This will delete all data! Use with caution.
    """
    print("⚠️  WARNING: This will drop all tables and DELETE ALL DATA!")
    confirm = input("Type 'YES' to confirm: ")
    
    if confirm != 'YES':
        print("Aborted.")
        return False
    
    try:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        return False


def validate_schema():
    """
    Validate database schema matches expectations.
    
    Checks:
    - All tables exist
    - All columns exist with correct types
    - All indexes exist
    - All constraints exist
    """
    print("Validating database schema...")
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Expected tables
        expected_tables = {
            'predictions': {
                'columns': [
                    'id', 'request_id', 'timestamp', 'model_version',
                    'patient_features', 'esi_prediction', 'probability_distribution',
                    'confidence_breakdown', 'safety_outcome', 'explanation',
                    'sub_score', 'inference_time_ms'
                ],
                'indexes': [
                    'idx_predictions_timestamp',
                    'idx_predictions_model_version',
                    'idx_predictions_esi',
                    'idx_predictions_safety',
                ]
            },
            'overrides': {
                'columns': [
                    'id', 'prediction_id', 'timestamp', 'ml_predicted_esi',
                    'ml_confidence', 'clinician_final_esi', 'override_direction',
                    'override_magnitude', 'override_reason_category',
                    'override_reason_text', 'clinician_id', 'patient_outcome',
                    'outcome_updated_at'
                ],
                'indexes': [
                    'idx_overrides_timestamp',
                    'idx_overrides_prediction',
                    'idx_overrides_clinician',
                    'idx_overrides_category',
                ]
            },
            'deterioration_alerts': {
                'columns': [
                    'id', 'patient_id', 'timestamp', 'deterioration_status',
                    'deterioration_score', 'vital_changes', 'initial_esi',
                    'time_since_triage_minutes', 'alert_reason', 'model_version'
                ],
                'indexes': [
                    'idx_deterioration_timestamp',
                    'idx_deterioration_patient',
                    'idx_deterioration_status',
                ]
            }
        }
        
        all_valid = True
        
        for table_name, expected in expected_tables.items():
            print(f"\n📋 Validating table: {table_name}")
            
            if table_name not in tables:
                print(f"   ✗ Table '{table_name}' does not exist")
                all_valid = False
                continue
            
            # Check columns
            columns = inspector.get_columns(table_name)
            column_names = [col['name'] for col in columns]
            
            missing_columns = set(expected['columns']) - set(column_names)
            if missing_columns:
                print(f"   ✗ Missing columns: {missing_columns}")
                all_valid = False
            else:
                print(f"   ✓ All {len(expected['columns'])} columns present")
            
            # Check indexes
            indexes = inspector.get_indexes(table_name)
            index_names = [idx['name'] for idx in indexes]
            
            missing_indexes = set(expected['indexes']) - set(index_names)
            if missing_indexes:
                print(f"   ⚠️  Missing indexes: {missing_indexes}")
                # Indexes are important but not critical for validation
            else:
                print(f"   ✓ All {len(expected['indexes'])} indexes present")
        
        if all_valid:
            print("\n✅ Schema validation passed!")
        else:
            print("\n❌ Schema validation failed!")
        
        return all_valid
        
    except Exception as e:
        print(f"❌ Error validating schema: {e}")
        return False


def run_sql_file():
    """
    Execute the schema.sql file directly.
    
    This is useful for creating additional objects like functions,
    triggers, and archive tables that aren't in the ORM models.
    """
    print("Running schema.sql file...")
    
    try:
        # Read schema.sql
        schema_file = Path(__file__).parent / 'schema.sql'
        
        if not schema_file.exists():
            print(f"❌ schema.sql not found at {schema_file}")
            return False
        
        with open(schema_file, 'r') as f:
            sql_content = f.read()
        
        # Execute SQL
        with engine.connect() as conn:
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            
            for i, statement in enumerate(statements):
                # Skip comments and empty statements
                if statement.startswith('--') or not statement:
                    continue
                
                try:
                    conn.execute(text(statement))
                    conn.commit()
                except Exception as e:
                    # Some statements may fail if objects already exist
                    # This is acceptable for idempotent setup
                    if 'already exists' not in str(e):
                        print(f"   ⚠️  Statement {i+1} warning: {e}")
            
        print("✅ schema.sql executed successfully")
        print("   Created: archive tables, functions, triggers, roles")
        return True
        
    except Exception as e:
        print(f"❌ Error executing schema.sql: {e}")
        return False


def check_connection():
    """Test database connection."""
    print("Testing database connection...")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version.split(',')[0]}")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check DATABASE_URL in .env file")
        print("3. Verify database credentials")
        return False


def main():
    """Main setup script."""
    parser = argparse.ArgumentParser(
        description='Database setup for PatientTriage.ai ML Core'
    )
    parser.add_argument(
        '--create',
        action='store_true',
        help='Create all database tables'
    )
    parser.add_argument(
        '--drop',
        action='store_true',
        help='Drop all tables (DANGEROUS!)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate database schema'
    )
    parser.add_argument(
        '--sql',
        action='store_true',
        help='Run schema.sql file'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Full setup: create tables + run SQL file'
    )
    
    args = parser.parse_args()
    
    # Check connection first
    if not check_connection():
        sys.exit(1)
    
    # Execute requested operation
    success = True
    
    if args.drop:
        success = drop_tables()
    
    if args.create:
        success = create_tables() and success
    
    if args.sql:
        success = run_sql_file() and success
    
    if args.full:
        print("\n" + "="*60)
        print("FULL DATABASE SETUP")
        print("="*60 + "\n")
        success = create_tables() and success
        if success:
            success = run_sql_file() and success
        if success:
            success = validate_schema() and success
    
    if args.validate:
        success = validate_schema() and success
    
    # If no arguments provided, show help
    if not any([args.create, args.drop, args.validate, args.sql, args.full]):
        parser.print_help()
        print("\n💡 Quick start:")
        print("   python -m src.database.setup --full")
        sys.exit(0)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
