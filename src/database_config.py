#!/usr/bin/env python3
"""
Database Configuration for PostgreSQL Analyzer MCP Server.

This module provides convenient preset configurations for different databases,
enabling local development without requiring AWS credentials.

Configuration values are loaded from environment variables via the Config class.
"""

from config import Config

# Database connection presets - using environment variables for local development
DATABASE_PRESETS = {
    # Local database (configurable via environment variables)
    "local": {
        "host": Config.LOCAL_DB_HOST,
        "port": Config.LOCAL_DB_PORT,
        "dbname": Config.LOCAL_DB_NAME,
        "username": Config.LOCAL_DB_USERNAME, 
        "password": Config.LOCAL_DB_PASSWORD,
        "description": "Local PostgreSQL database (configured via environment variables)"
    },
    
    # Development database (configurable via environment variables)
    "development": {
        "host": Config.DEV_DB_HOST,
        "port": Config.DEV_DB_PORT,
        "dbname": Config.DEV_DB_NAME,
        "username": Config.DEV_DB_USERNAME,
        "password": Config.DEV_DB_PASSWORD,
        "description": "Development database (configured via environment variables)"
    },
    
    # Production database (using AWS Secrets Manager - existing functionality)
    "production": {
        "secret_name": Config.PROD_DB_SECRET_NAME,
        "region_name": Config.PROD_DB_REGION,
        "description": "Production database using AWS Secrets Manager"
    },
    
    # Staging environment (using AWS Secrets Manager - existing functionality)
    "staging": {
        "secret_name": Config.STAGING_DB_SECRET_NAME,
        "region_name": Config.STAGING_DB_REGION,
        "description": "Staging database using AWS Secrets Manager"
    }
}

def get_database_config(preset_name: str) -> dict:
    """
    Get database configuration by preset name.
    
    Args:
        preset_name: Name of the database preset (e.g., 'local', 'development', 'production')
        
    Returns:
        Dictionary containing database connection parameters
        
    Raises:
        KeyError: If preset_name is not found
    """
    if preset_name not in DATABASE_PRESETS:
        available_presets = ', '.join(DATABASE_PRESETS.keys())
        raise KeyError(f"Database preset '{preset_name}' not found. Available presets: {available_presets}")
    
    return DATABASE_PRESETS[preset_name].copy()

def list_database_presets() -> None:
    """Print all available database presets with their descriptions."""
    print("Available Database Presets:")
    print("=" * 50)
    
    for name, config in DATABASE_PRESETS.items():
        print(f"\n{name}:")
        print(f"  Description: {config.get('description', 'No description')}")
        
        if 'host' in config:
            print(f"  Type: Direct credentials")
            print(f"  Host: {config['host']}:{config.get('port', 5432)}")
            print(f"  Database: {config['dbname']}")
        elif 'secret_name' in config:
            print(f"  Type: AWS Secrets Manager")
            print(f"  Secret: {config['secret_name']}")
            print(f"  Region: {config.get('region_name', 'us-west-2')}")

def validate_preset(preset_name: str) -> bool:
    """
    Validate that a preset has all required parameters.
    
    Args:
        preset_name: Name of the database preset
        
    Returns:
        True if valid, False otherwise
    """
    try:
        config = get_database_config(preset_name)
        
        # Check for direct credentials
        if 'host' in config:
            required_fields = ['host', 'dbname', 'username', 'password']
            return all(field in config for field in required_fields)
        
        # Check for AWS Secrets Manager
        elif 'secret_name' in config:
            return 'secret_name' in config
        
        return False
    except KeyError:
        return False

def get_environment_info() -> dict:
    """Get information about current environment configuration."""
    return {
        "local_db": {
            "host": Config.LOCAL_DB_HOST,
            "port": Config.LOCAL_DB_PORT,
            "database": Config.LOCAL_DB_NAME,
            "username": Config.LOCAL_DB_USERNAME
        },
        "dev_db": {
            "host": Config.DEV_DB_HOST,
            "port": Config.DEV_DB_PORT,
            "database": Config.DEV_DB_NAME,
            "username": Config.DEV_DB_USERNAME
        },
        "aws_config": {
            "default_region": Config.AWS_DEFAULT_REGION,
            "prod_secret": Config.PROD_DB_SECRET_NAME,
            "staging_secret": Config.STAGING_DB_SECRET_NAME
        }
    }

if __name__ == "__main__":
    # When run directly, show available presets and environment info
    list_database_presets()
    
    print(f"\n\nEnvironment Configuration:")
    print("=" * 50)
    env_info = get_environment_info()
    
    print(f"Local Database Configuration:")
    print(f"  Host: {env_info['local_db']['host']}:{env_info['local_db']['port']}")
    print(f"  Database: {env_info['local_db']['database']}")
    print(f"  Username: {env_info['local_db']['username']}")
    
    print(f"\nDevelopment Database Configuration:")
    print(f"  Host: {env_info['dev_db']['host']}:{env_info['dev_db']['port']}")
    print(f"  Database: {env_info['dev_db']['database']}")
    print(f"  Username: {env_info['dev_db']['username']}")
    
    print(f"\nAWS Configuration:")
    print(f"  Default Region: {env_info['aws_config']['default_region']}")
    print(f"  Production Secret: {env_info['aws_config']['prod_secret']}")
    print(f"  Staging Secret: {env_info['aws_config']['staging_secret']}")
    
    print(f"\nExample usage:")
    print(f"  from database_config import get_database_config")
    print(f"  config = get_database_config('local')")
    print(f"  # Use config in your MCP tools")
