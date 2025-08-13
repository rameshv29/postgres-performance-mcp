# PostgreSQL Analyzer MCP

A Model Context Protocol (MCP) server for PostgreSQL database performance analysis and optimization.

## Overview

PostgreSQL Analyzer MCP is a powerful tool that leverages AI to help database administrators and developers optimize their PostgreSQL databases. It provides comprehensive analysis of database structure, query performance, index usage, and configuration settings, along with actionable recommendations for improvement.

This tool runs as a remote MCP server using Streamable HTTP transport, allowing it to be deployed centrally and accessed by any MCP-compatible client, including AI assistants that support the MCP protocol.

## ⚠️ Disclaimer

**EXPERIMENTAL**: This project is experimental and provided as a demonstration of what's possible with MCP and PostgreSQL. All recommendations and code should be carefully reviewed before implementation in any production environment.

**NOT OFFICIAL**: This is a personal project and not affiliated with, endorsed by, or representative of any organization I work for or contribute to. All opinions and approaches are my own.

**NO LIABILITY**: This tool is provided "as is" without warranty of any kind. Use at your own risk. The author is not liable for any damages or issues arising from the use of this software.

## Features

- **Database Structure Analysis**: Analyze tables, columns, indexes, and foreign keys
- **Query Performance Analysis**: Analyze execution plans and identify bottlenecks
- **Index Recommendations**: Get suggestions for new indexes based on query patterns
- **Query Optimization**: Receive suggestions for query rewrites to improve performance
- **Slow Query Identification**: Find and analyze slow-running queries
- **Database Health Dashboard**: Get a comprehensive overview of database health metrics
- **Index Usage Analysis**: Identify unused, duplicate, or bloated indexes
- **Read-Only Query Execution**: Safely execute read-only queries for verification
- **Environment Configuration**: Flexible configuration via environment variables
- **AWS Secrets Manager**: Secure credential management for production environments
- **Local Database Support**: Connect to local PostgreSQL databases without AWS credentials

## Security

This tool operates in **read-only mode** by default. All database connections are established with `SET TRANSACTION READ ONLY` to prevent any accidental modifications to your database. The query execution functionality is strictly limited to SELECT, EXPLAIN, and SHOW commands.

## Installation

### Prerequisites

- Python 3.12+ (or Docker)
- PostgreSQL database
- AWS account (for Secrets Manager, optional)

### Setup

#### Option 1: Local Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/postgres-performance-mcp.git
   cd postgres-performance-mcp
   ```

2. Create virtual environment and Install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure environment:

   ```bash
   # Copy environment template
   cp env.example .env

   # Edit with your database settings
   nano .env
   ```

#### Option 2: Docker Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/postgres-performance-mcp.git
   cd postgres-performance-mcp
   ```

2. Build the Docker image:

   ```bash
   docker build -t postgres-analyzer-mcp -f Dockerfile .
   ```

3. Run the Docker container:

   ```bash
   docker run -p 8000:8000 \
     -e LOCAL_DB_HOST=your_host \
     -e LOCAL_DB_PORT=5432 \
     -e LOCAL_DB_NAME=your_db \
     -e LOCAL_DB_USERNAME=your_user \
     -e LOCAL_DB_PASSWORD=your_password \
     postgres-analyzer-mcp
   ```

## Configuration

### Environment Variables

The application uses environment variables for configuration. Copy `env.example` to `.env` and customize:

```bash
# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO

# Local Database Configuration (NEW - for local development)
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=postgres
LOCAL_DB_USERNAME=postgres
LOCAL_DB_PASSWORD=your_password

# AWS Configuration (optional)
AWS_DEFAULT_REGION=us-west-2
PROD_DB_SECRET_NAME=prod-postgres-credentials
```

### Database Connection Methods

The tool supports three ways to connect to databases:

1. **Database Presets** (Recommended for local development):

   ```bash
   # Use 'local' preset for local database
   analyze_database_structure(preset="local")
   ```

2. **Direct Credentials**:

   ```bash
   # Provide credentials directly
   analyze_database_structure(
       host="localhost",
       port=5432,
       dbname="mydb",
       username="postgres",
       password="password"
   )
   ```

3. **AWS Secrets Manager** (for production):
   ```bash
   # Use AWS secrets
   analyze_database_structure(secret_name="prod-db-credentials")
   ```

## Usage

### Starting the Server

#### Local:

```bash
python src/main.py --host 0.0.0.0 --port 8000
```

#### Docker:

```bash
# The server starts automatically when running the container
docker run -p 8000:8000 postgres-analyzer-mcp
```

### Configuring MCP Clients

To connect to your remote MCP server, configure your MCP client with:

```
Server URL: http://your-server-address:8000/mcp
Transport: Streamable HTTP
```

### Using with an MCP Client

Connect to the server using any MCP-compatible client and use the available tools:

```
# Local database analysis (easiest)
analyze_database_structure(preset="local")

# Direct credentials
analyze_database_structure(host="localhost", port=5432, dbname="mydb", username="postgres", password="password")

# AWS Secrets Manager
analyze_database_structure(secret_name="prod-db-credentials")
```

### Available Tools

- `analyze_database_structure`: Analyze database schema and provide optimization recommendations
- `get_slow_queries`: Identify slow-running queries in the database
- `analyze_query`: Analyze a SQL query and provide optimization recommendations
- `recommend_indexes`: Recommend indexes for a given SQL query
- `suggest_query_rewrite`: Suggest optimized rewrites for a SQL query
- `execute_read_only_query`: Execute a read-only SQL query and return the results
- `show_postgresql_settings`: Show PostgreSQL configuration settings with optional filtering
- `health_check`: Check if the server is running and responsive

## Database Presets

The system provides several preconfigured database presets:

- **`local`** - Local development database (uses LOCAL*DB*\* environment variables)
- **`development`** - Development database (uses DEV*DB*\* environment variables)
- **`production`** - Production database (uses AWS Secrets Manager)
- **`staging`** - Staging database (uses AWS Secrets Manager)

## Local Development Quick Start

1. **Configure your local database**:

   ```bash
   cp env.example .env
   # Edit .env with your local PostgreSQL credentials
   ```

2. **Start the MCP server**:

   ```bash
   python src/main.py
   ```

3. **Use the tools with local preset**:

   ```bash
   # Analyze your local database
   analyze_database_structure(preset="local")

   # Check for slow queries
   get_slow_queries(preset="local")

   # Analyze a specific query
   analyze_query("SELECT * FROM users", preset="local")
   ```

## AWS Secrets Manager Setup

To use AWS Secrets Manager for storing database credentials:

1. Create a secret in AWS Secrets Manager with the following keys:

   - `host`: Database hostname
   - `port`: Database port (usually 5432)
   - `dbname`: Database name
   - `username`: Database username
   - `password`: Database password

2. Ensure your AWS credentials are configured with appropriate permissions to access the secret.

3. Use the secret name when calling the tools:
   ```
   analyze_query(query="SELECT * FROM users WHERE user_id = 123", preset="production")
   ```

## Deploying to a Remote Server

To deploy the MCP server to a remote machine:

1. Install Docker on your remote server
2. Copy the project files to the server or clone from your repository
3. Build and run the Docker container:
   ```bash
   docker build -t postgres-analyzer-mcp -f Dockerfile .
   docker run -d -p 8000:8000 postgres-analyzer-mcp
   ```
4. Consider using a process manager like `docker-compose` or `systemd` to ensure the container restarts if the server reboots

For secure access, consider setting up:

- A reverse proxy with SSL/TLS (like Nginx or Traefik)
- Authentication middleware
- Firewall rules to restrict access

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- PostgreSQL community for their documentation
- MCP protocol developers for enabling AI-powered tools
- This project was created using vibe coding - an AI-assisted development approach that combines human expertise with AI capabilities to create robust, maintainable software solutions.
