import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from session_handler import SessionHandler

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration management using environment variables"""
    
    # Server Configuration
    MCP_HOST = os.getenv('MCP_HOST', '0.0.0.0')
    MCP_PORT = int(os.getenv('MCP_PORT', '8000'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '1800'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))
    
    # Local Database Configuration (NEW - for local development without AWS)
    LOCAL_DB_HOST = os.getenv('LOCAL_DB_HOST', 'localhost')
    LOCAL_DB_PORT = int(os.getenv('LOCAL_DB_PORT', '5432'))
    LOCAL_DB_NAME = os.getenv('LOCAL_DB_NAME', 'postgres')
    LOCAL_DB_USERNAME = os.getenv('LOCAL_DB_USERNAME', 'postgres')
    LOCAL_DB_PASSWORD = os.getenv('LOCAL_DB_PASSWORD', 'postgres')
    
    # Development Database Configuration (NEW - additional local preset)
    DEV_DB_HOST = os.getenv('DEV_DB_HOST', 'localhost')
    DEV_DB_PORT = int(os.getenv('DEV_DB_PORT', '5432'))
    DEV_DB_NAME = os.getenv('DEV_DB_NAME', 'myapp_dev')
    DEV_DB_USERNAME = os.getenv('DEV_DB_USERNAME', 'developer')
    DEV_DB_PASSWORD = os.getenv('DEV_DB_PASSWORD', 'dev_password')
    
    # AWS Configuration (existing - kept for production use)
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
    PROD_DB_SECRET_NAME = os.getenv('PROD_DB_SECRET_NAME', 'prod-postgres-readonly-credentials')
    PROD_DB_REGION = os.getenv('PROD_DB_REGION', 'us-east-1')
    STAGING_DB_SECRET_NAME = os.getenv('STAGING_DB_SECRET_NAME', 'staging-postgres-credentials')
    STAGING_DB_REGION = os.getenv('STAGING_DB_REGION', 'us-west-2')

    
    # Security Configuration
    DB_CONNECTION_TIMEOUT = int(os.getenv('DB_CONNECTION_TIMEOUT', '30'))
    DB_QUERY_TIMEOUT = int(os.getenv('DB_QUERY_TIMEOUT', '30'))
    DB_READ_ONLY = os.getenv('DB_READ_ONLY', 'true').lower() == 'true'
    
    # Feature Flags
    ENABLE_HEALTH_CHECK = os.getenv('ENABLE_HEALTH_CHECK', 'true').lower() == 'true'
    ENABLE_SESSION_STATUS = os.getenv('ENABLE_SESSION_STATUS', 'true').lower() == 'true'
    ENABLE_QUERY_LOGGING = os.getenv('ENABLE_QUERY_LOGGING', 'false').lower() == 'true'

# Create a global session handler
session_handler = SessionHandler(session_timeout=1800)

def configure_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("postgres-analyzer")

@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage application lifecycle for the MCP server"""
    try:
        print("Starting PostgreSQL Performance Analyzer MCP Server")
        # Start the session handler
        await session_handler.start()
        yield
    finally:
        # Stop the session handler
        await session_handler.stop()
        print("Shutting down PostgreSQL Performance Analyzer MCP Server")