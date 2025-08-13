"""
MCP tool definitions for PostgreSQL Performance Analyzer.
This file contains all the tool functions that are registered with the MCP server.
"""
import json
import time
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import Context, FastMCP

from db.connector import PostgresConnector
from analysis.structure import (
    get_database_structure, 
    organize_db_structure_by_table,
    analyze_database_structure_for_response
)
from analysis.query import (
    extract_tables_from_query, 
    get_table_statistics, 
    get_schema_information, 
    get_index_information,
    format_query_analysis_response
)
from analysis.patterns import (
    detect_query_patterns, 
    detect_query_anti_patterns, 
    validate_read_only_query
)
from analysis.indexes import (
    extract_potential_indexes,
    get_table_structure_for_index,
    check_existing_indexes,
    format_index_recommendations_response
)

def get_database_connector(preset=None, secret_name=None, region_name="us-west-2", 
                          host=None, port=None, dbname=None, username=None, password=None):
    """
    Create a PostgresConnector using database presets, direct credentials, or AWS Secrets Manager.
    
    Priority: Direct credentials > Database presets > AWS Secrets Manager.
    
    Args:
        preset: Database preset name (e.g., 'local', 'production') - from database_config.py
        secret_name: AWS Secrets Manager secret name
        region_name: AWS region for Secrets Manager
        host: Database host (direct credential)
        port: Database port (direct credential) 
        dbname: Database name (direct credential)
        username: Database username (direct credential)
        password: Database password (direct credential)
    
    Returns:
        PostgresConnector instance or None if no valid credentials provided
    """
    # If direct credentials are provided, use them (highest priority)
    if host and dbname and username and password:
        return PostgresConnector(
            host=host,
            port=port or 5432,
            dbname=dbname,
            user=username,
            password=password
        )
    
    # Try database preset (medium priority)
    elif preset:
        try:
            from database_config import get_database_config
            config = get_database_config(preset)
            
            # If preset uses direct credentials
            if 'host' in config:
                return PostgresConnector(
                    host=config['host'],
                    port=config.get('port', 5432),
                    dbname=config['dbname'],
                    user=config['username'],
                    password=config['password']
                )
            # If preset uses AWS Secrets Manager
            elif 'secret_name' in config:
                return PostgresConnector(
                    secret_name=config['secret_name'],
                    region_name=config.get('region_name', region_name)
                )
        except (ImportError, KeyError) as e:
            print(f"Error loading database preset '{preset}': {e}")
            return None
    
    # Otherwise, try AWS Secrets Manager (lowest priority)
    elif secret_name:
        return PostgresConnector(
            secret_name=secret_name,
            region_name=region_name
        )
    
    # If none are provided, return None
    else:
        return None

def register_all_tools(mcp: FastMCP):
    """Register all tools with the MCP server"""
    
    @mcp.tool()
    async def analyze_database_structure(
        preset: str = None,
        secret_name: str = None, 
        region_name: str = "us-west-2",
        host: str = None,
        port: int = None, 
        dbname: str = None,
        username: str = None,
        password: str = None,
        ctx: Context = None
    ) -> str:
        """
        Analyze the database structure and provide insights on schema design, indexes, and potential optimizations.
        
        Args:
            preset: Database preset name (e.g., 'local', 'production') - easiest option
            secret_name: AWS Secrets Manager secret name containing database credentials
            region_name: AWS region where the secret is stored (default: us-west-2)
            host: Database host (alternative to preset/secret_name)
            port: Database port (alternative to preset/secret_name, default: 5432)
            dbname: Database name (alternative to preset/secret_name) 
            username: Database username (alternative to preset/secret_name)
            password: Database password (alternative to preset/secret_name)
        
        Returns:
            A comprehensive analysis of the database structure with optimization recommendations
            
        Examples:
            # Using database preset (easiest):
            analyze_database_structure(preset="local")
            
            # Using direct credentials:
            analyze_database_structure(host="localhost", port=5432, dbname="mydb", username="postgres", password="password")
            
            # Using AWS Secrets Manager:
            analyze_database_structure(secret_name="my-db-credentials", region_name="us-west-2")
        """
        # Create connector using helper function
        connector = get_database_connector(
            preset=preset,
            secret_name=secret_name,
            region_name=region_name,
            host=host,
            port=port,
            dbname=dbname, 
            username=username,
            password=password
        )
        
        if not connector:
            return "Error: Please provide database credentials using one of these methods:\n1. preset='local' (or other preset name)\n2. AWS Secrets Manager (secret_name)\n3. Direct credentials (host, dbname, username, password)"
        
        try:
            if not connector.connect():
                cred_type = "direct credentials" if host else f"secret '{secret_name}'"
                return f"Failed to connect to database using {cred_type}. Please check your credentials."
            
            # Get comprehensive database structure
            db_structure = get_database_structure(connector)
            
            # Organize and analyze the structure
            organized_structure = organize_db_structure_by_table(db_structure)
            analysis_response = analyze_database_structure_for_response(organized_structure)
            
            return analysis_response
            
        except Exception as e:
            return f"Error analyzing database structure: {str(e)}"
        finally:
            connector.disconnect()
    
    @mcp.tool()
    async def get_slow_queries(
        secret_name: str = None, 
        region_name: str = "us-west-2",
        host: str = None,
        port: int = None,
        dbname: str = None,
        username: str = None,
        password: str = None,
        min_execution_time: int = 100, 
        limit: int = 10, 
        ctx: Context = None
    ) -> str:
        """
        Identify slow-running queries in the database.
        
        Args:
            secret_name: AWS Secrets Manager secret name containing database credentials
            region_name: AWS region where the secret is stored (default: us-west-2)
            host: Database host (alternative to secret_name)
            port: Database port (alternative to secret_name, default: 5432)
            dbname: Database name (alternative to secret_name)
            username: Database username (alternative to secret_name)
            password: Database password (alternative to secret_name)
            min_execution_time: Minimum execution time in milliseconds (default: 100ms)
            limit: Maximum number of queries to return (default: 10)
        
        Returns:
            A list of slow queries with their execution statistics and analysis
            
        Examples:
            # Using direct credentials:
            get_slow_queries(host="localhost", port=5432, dbname="mydb", username="postgres", password="password", limit=5)
            
            # Using AWS Secrets Manager:
            get_slow_queries(secret_name="my-db-credentials", min_execution_time=200)
        """
        # Create connector using helper function
        connector = get_database_connector(
            secret_name=secret_name,
            region_name=region_name,
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password
        )
        
        if not connector:
            return "Error: Please provide either AWS Secrets Manager credentials (secret_name) or direct database credentials (host, dbname, username, password)."
        
        try:
            if not connector.connect():
                cred_type = "direct credentials" if host else f"secret '{secret_name}'"
                return f"Failed to connect to database using {cred_type}. Please check your credentials."
            
            # First check if pg_stat_statements extension is installed
            check_extension_query = """
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                ) as has_pg_stat_statements;
            """
            
            result = connector.execute_query(check_extension_query)
            if not result or not result[0]['has_pg_stat_statements']:
                return "Error: pg_stat_statements extension is not installed. This extension is required for slow query analysis. Please install it first:\n\nCREATE EXTENSION pg_stat_statements;\n\nNote: You may need to restart PostgreSQL after installing this extension."
            
            # Get slow queries
            slow_queries_query = f"""
                SELECT 
                    LEFT(query, 100) || '...' as query_preview,
                    calls,
                    total_exec_time::numeric(10,2) as total_time_ms,
                    mean_exec_time::numeric(10,2) as avg_time_ms,
                    max_exec_time::numeric(10,2) as max_time_ms,
                    stddev_exec_time::numeric(10,2) as stddev_time_ms
                FROM pg_stat_statements 
                WHERE mean_exec_time >= {min_execution_time}
                AND query NOT LIKE '%pg_stat_statements%'
                ORDER BY mean_exec_time DESC 
                LIMIT {limit};
            """
            
            result = connector.execute_query(slow_queries_query)
            
            if not result:
                return f"No queries found with execution time >= {min_execution_time}ms."
            
            # Format the response
            response = f"Found {len(result)} slow queries (execution time >= {min_execution_time}ms):\n\n"
            
            for i, query in enumerate(result, 1):
                response += f"{i}. **Query Preview**: {query['query_preview']}\n"
                response += f"   **Calls**: {query['calls']}\n"
                response += f"   **Average Time**: {query['avg_time_ms']}ms\n"
                response += f"   **Total Time**: {query['total_time_ms']}ms\n"
                response += f"   **Max Time**: {query['max_time_ms']}ms\n"
                response += f"   **Std Dev**: {query['stddev_time_ms']}ms\n\n"
            
            return response
            
        except Exception as e:
            return f"Error getting slow queries: {str(e)}"
        finally:
            connector.disconnect()
    
    @mcp.tool()
    async def analyze_query(
        query: str, 
        secret_name: str = None, 
        region_name: str = "us-west-2",
        host: str = None,
        port: int = None,
        dbname: str = None,
        username: str = None,
        password: str = None,
        ctx: Context = None
    ) -> str:
        """
        Analyze a SQL query and provide optimization recommendations.
        
        Args:
            query: The SQL query to analyze
            secret_name: AWS Secrets Manager secret name containing database credentials
            region_name: AWS region where the secret is stored (default: us-west-2)
            host: Database host (alternative to secret_name)
            port: Database port (alternative to secret_name, default: 5432)
            dbname: Database name (alternative to secret_name)
            username: Database username (alternative to secret_name)
            password: Database password (alternative to secret_name)
        
        Returns:
            Analysis of the query execution plan and optimization suggestions
            
        Examples:
            # Using direct credentials:
            analyze_query("SELECT * FROM users WHERE age > 25", host="localhost", port=5432, dbname="mydb", username="postgres", password="password")
            
            # Using AWS Secrets Manager:
            analyze_query("SELECT * FROM users WHERE age > 25", secret_name="my-db-credentials")
        """
        # Create connector using helper function
        connector = get_database_connector(
            secret_name=secret_name,
            region_name=region_name,
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password
        )
        
        if not connector:
            return "Error: Please provide either AWS Secrets Manager credentials (secret_name) or direct database credentials (host, dbname, username, password)."
        
        try:
            if not connector.connect():
                cred_type = "direct credentials" if host else f"secret '{secret_name}'"
                return f"Failed to connect to database using {cred_type}. Please check your credentials."
            
            # Clean the query before analysis
            query = query.strip()
            if not query:
                return "Error: Please provide a valid SQL query to analyze."
            
            # Get the execution plan
            explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE) {query}"
            
            try:
                result = connector.execute_query(explain_query)
                if not result:
                    return "Error: Could not generate execution plan for the query."
                
                execution_plan = result[0]['QUERY PLAN']
                
                # Extract tables involved in the query
                tables_involved = extract_tables_from_query(query)
                
                # Get additional context about the tables
                table_stats = {}
                schema_info = {}
                index_info = {}
                
                for table in tables_involved:
                    if table:
                        table_stats[table] = get_table_statistics(connector, table)
                        schema_info[table] = get_schema_information(connector, table)
                        index_info[table] = get_index_information(connector, table)
                
                # Analyze query patterns
                patterns = detect_query_patterns(query)
                anti_patterns = detect_query_anti_patterns(query)
                
                # Format the response
                response = format_query_analysis_response(
                    query, execution_plan, table_stats, schema_info, 
                    index_info, patterns, anti_patterns
                )
                
                return response
                
            except Exception as e:
                # If EXPLAIN ANALYZE fails, try without ANALYZE
                try:
                    explain_query = f"EXPLAIN (FORMAT JSON) {query}"
                    result = connector.execute_query(explain_query)
                    if result:
                        execution_plan = result[0]['QUERY PLAN']
                        return f"Query Analysis (without execution):\n\n**Query**: {query}\n\n**Execution Plan**:\n```json\n{json.dumps(execution_plan, indent=2)}\n```\n\nNote: Could not analyze actual execution time. Consider running the query first to populate statistics."
                    else:
                        return f"Error: Could not generate execution plan for the query: {str(e)}"
                except Exception as e2:
                    return f"Error analyzing query: {str(e2)}"
            
        except Exception as e:
            return f"Error analyzing query: {str(e)}"
        finally:
            connector.disconnect()
    
    @mcp.tool()
    async def recommend_indexes(
        query: str, 
        secret_name: str = None, 
        region_name: str = "us-west-2",
        host: str = None,
        port: int = None,
        dbname: str = None,
        username: str = None,
        password: str = None,
        ctx: Context = None
    ) -> str:
        """
        Recommend indexes for a given SQL query.
        
        Args:
            query: The SQL query to analyze for index recommendations
            secret_name: AWS Secrets Manager secret name containing database credentials
            region_name: AWS region where the secret is stored (default: us-west-2)
            host: Database host (alternative to secret_name)
            port: Database port (alternative to secret_name, default: 5432)
            dbname: Database name (alternative to secret_name)
            username: Database username (alternative to secret_name)
            password: Database password (alternative to secret_name)
        
        Returns:
            Recommended indexes to improve query performance
            
        Examples:
            # Using direct credentials:
            recommend_indexes("SELECT * FROM users WHERE email = 'user@example.com'", host="localhost", port=5432, dbname="mydb", username="postgres", password="password")
            
            # Using AWS Secrets Manager:
            recommend_indexes("SELECT * FROM users WHERE email = 'user@example.com'", secret_name="my-db-credentials")
        """
        # Create connector using helper function
        connector = get_database_connector(
            secret_name=secret_name,
            region_name=region_name,
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password
        )
        
        if not connector:
            return "Error: Please provide either AWS Secrets Manager credentials (secret_name) or direct database credentials (host, dbname, username, password)."
        
        try:
            if not connector.connect():
                cred_type = "direct credentials" if host else f"secret '{secret_name}'"
                return f"Failed to connect to database using {cred_type}. Please check your credentials."
            
            # First, analyze the database structure to understand the context
            tables_involved = extract_tables_from_query(query)
            
            if not tables_involved:
                return "Error: Could not identify tables in the query."
            
            # Get potential indexes for each table
            recommendations = []
            
            for table in tables_involved:
                if table:
                    # Get table structure
                    table_structure = get_table_structure_for_index(connector, table)
                    
                    # Check existing indexes
                    existing_indexes = check_existing_indexes(connector, table)
                    
                    # Extract potential indexes from the query
                    potential_indexes = extract_potential_indexes(query, table, table_structure)
                    
                    if potential_indexes:
                        recommendations.append({
                            'table': table,
                            'potential_indexes': potential_indexes,
                            'existing_indexes': existing_indexes
                        })
            
            # Format the response
            response = format_index_recommendations_response(recommendations)
            
            return response
            
        except Exception as e:
            return f"Error recommending indexes: {str(e)}"
        finally:
            connector.disconnect()
    
    @mcp.tool()
    async def suggest_query_rewrite(
        query: str, 
        secret_name: str = None, 
        region_name: str = "us-west-2",
        host: str = None,
        port: int = None,
        dbname: str = None,
        username: str = None,
        password: str = None,
        ctx: Context = None
    ) -> str:
        """
        Suggest optimized rewrites for a SQL query.
        
        Args:
            query: The SQL query to optimize
            secret_name: AWS Secrets Manager secret name containing database credentials
            region_name: AWS region where the secret is stored (default: us-west-2)
            host: Database host (alternative to secret_name)
            port: Database port (alternative to secret_name, default: 5432)
            dbname: Database name (alternative to secret_name)
            username: Database username (alternative to secret_name)
            password: Database password (alternative to secret_name)
        
        Returns:
            Suggestions for query rewrites to improve performance
            
        Examples:
            # Using direct credentials:
            suggest_query_rewrite("SELECT * FROM users JOIN orders ON users.id = orders.user_id", host="localhost", port=5432, dbname="mydb", username="postgres", password="password")
            
            # Using AWS Secrets Manager:
            suggest_query_rewrite("SELECT * FROM users JOIN orders ON users.id = orders.user_id", secret_name="my-db-credentials")
        """
        # Create connector using helper function
        connector = get_database_connector(
            secret_name=secret_name,
            region_name=region_name,
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password
        )
        
        if not connector:
            return "Error: Please provide either AWS Secrets Manager credentials (secret_name) or direct database credentials (host, dbname, username, password)."
        
        try:
            if not connector.connect():
                cred_type = "direct credentials" if host else f"secret '{secret_name}'"
                return f"Failed to connect to database using {cred_type}. Please check your credentials."
            
            # Get the execution plan
            explain_query = f"EXPLAIN (FORMAT JSON) {query}"
            
            try:
                result = connector.execute_query(explain_query)
                if not result:
                    return "Error: Could not generate execution plan for the query."
                
                execution_plan = result[0]['QUERY PLAN']
                
                # Analyze the execution plan for optimization opportunities
                suggestions = []
                
                # Check for sequential scans
                if 'Seq Scan' in str(execution_plan):
                    suggestions.append("Consider adding indexes on columns used in WHERE, JOIN, or ORDER BY clauses to avoid sequential scans.")
                
                # Check for nested loops
                if 'Nested Loop' in str(execution_plan):
                    suggestions.append("Consider adding indexes on join columns to improve join performance.")
                
                # Check for sorting operations
                if 'Sort' in str(execution_plan):
                    suggestions.append("Consider adding indexes on ORDER BY columns to avoid sorting operations.")
                
                # Check for aggregation
                if 'Aggregate' in str(execution_plan):
                    suggestions.append("Consider adding indexes on GROUP BY columns to improve aggregation performance.")
                
                # General optimization suggestions
                suggestions.append("Consider using specific column names instead of SELECT * to reduce data transfer.")
                suggestions.append("Ensure WHERE clauses use indexed columns when possible.")
                suggestions.append("Consider using LIMIT to restrict result sets if you don't need all rows.")
                
                # Format the response
                response = f"Query Optimization Suggestions for: {query}\n\n"
                response += "**Execution Plan Analysis**:\n"
                response += f"```json\n{json.dumps(execution_plan, indent=2)}\n```\n\n"
                
                if suggestions:
                    response += "**Optimization Suggestions**:\n"
                    for i, suggestion in enumerate(suggestions, 1):
                        response += f"{i}. {suggestion}\n"
                else:
                    response += "**No specific optimization suggestions found.**\n"
                
                return response
                
            except Exception as e:
                return f"Error analyzing query for optimization: {str(e)}"
            
        except Exception as e:
            return f"Error suggesting query rewrite: {str(e)}"
        finally:
            connector.disconnect()
            
    @mcp.tool()
    async def show_postgresql_settings(
        pattern: str = None, 
        secret_name: str = None, 
        region_name: str = "us-west-2",
        host: str = None,
        port: int = None,
        dbname: str = None,
        username: str = None,
        password: str = None,
        ctx: Context = None
    ) -> str:
        """
        Show PostgreSQL configuration settings with optional filtering.
        
        Args:
            pattern: Optional pattern to filter settings (e.g., "wal" for all WAL-related settings)
            secret_name: AWS Secrets Manager secret name containing database credentials
            region_name: AWS region where the secret is stored (default: us-west-2)
            host: Database host (alternative to secret_name)
            port: Database port (alternative to secret_name, default: 5432)
            dbname: Database name (alternative to secret_name)
            username: Database username (alternative to secret_name)
            password: Database password (alternative to secret_name)
        
        Returns:
            Current PostgreSQL configuration settings in a formatted table
        
        Examples:
            # Using direct credentials:
            show_postgresql_settings(pattern="max_connections", host="localhost", port=5432, dbname="mydb", username="postgres", password="password")
            
            # Using AWS Secrets Manager:
            show_postgresql_settings(pattern="wal", secret_name="my-db-secret")
        """
        # Create connector using helper function
        connector = get_database_connector(
            secret_name=secret_name,
            region_name=region_name,
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password
        )
        
        if not connector:
            return "Error: Please provide either AWS Secrets Manager credentials (secret_name) or direct database credentials (host, dbname, username, password)."
        
        try:
            if not connector.connect():
                cred_type = "direct credentials" if host else f"secret '{secret_name}'"
                return f"Failed to connect to database using {cred_type}. Please check your credentials."
            
            # Build the query based on whether a pattern is provided
            if pattern:
                query = """
                    SELECT name, setting, unit, context, category
                    FROM pg_settings 
                    WHERE name ILIKE %s
                    ORDER BY name;
                """
                params = [f'%{pattern}%']
            else:
                query = """
                    SELECT name, setting, unit, context, category
                    FROM pg_settings 
                    ORDER BY name;
                """
                params = []
            
            result = connector.execute_query(query, params)
            
            if not result:
                if pattern:
                    return f"No PostgreSQL settings found matching pattern '{pattern}'."
                else:
                    return "No PostgreSQL settings found."
            
            # Format the response
            if pattern:
                response = f"PostgreSQL Settings matching '{pattern}':\n\n"
            else:
                response = "PostgreSQL Configuration Settings:\n\n"
            
            response += "| Setting | Value | Unit | Context | Category |\n"
            response += "|---------|-------|------|---------|----------|\n"
            
            for setting in result:
                name = setting['name']
                value = setting['setting']
                unit = setting['unit'] or ''
                context = setting['context']
                category = setting['category']
                
                response += f"| {name} | {value} | {unit} | {context} | {category} |\n"
            
            return response
            
        except Exception as e:
            return f"Error showing PostgreSQL settings: {str(e)}"
        finally:
            connector.disconnect()
    
    @mcp.tool()
    async def execute_read_only_query(
        query: str, 
        secret_name: str = None, 
        region_name: str = "us-west-2",
        host: str = None,
        port: int = None,
        dbname: str = None,
        username: str = None, 
        password: str = None,
        max_rows: int = 100, 
        ctx: Context = None
    ) -> str:
        """
        Execute a read-only SQL query and return the results.
        
        Args:
            query: The SQL query to execute (must be SELECT, EXPLAIN, or SHOW only)
            secret_name: AWS Secrets Manager secret name containing database credentials
            region_name: AWS region where the secret is stored (default: us-west-2)
            host: Database host (alternative to secret_name)
            port: Database port (alternative to secret_name, default: 5432)
            dbname: Database name (alternative to secret_name)
            username: Database username (alternative to secret_name)
            password: Database password (alternative to secret_name)
            max_rows: Maximum number of rows to return (default: 100)
        
        Returns:
            Query results in a formatted table
            
        Examples:
            # Using direct credentials:
            execute_read_only_query("SELECT version();", host="localhost", port=5432, dbname="mydb", username="postgres", password="password")
            
            # Using AWS Secrets Manager:
            execute_read_only_query("SELECT * FROM pg_stat_activity LIMIT 10", secret_name="my-db-secret")
        """
        # Create connector using helper function
        connector = get_database_connector(
            secret_name=secret_name,
            region_name=region_name,
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password
        )
        
        if not connector:
            return "Error: Please provide either AWS Secrets Manager credentials (secret_name) or direct database credentials (host, dbname, username, password)."
        
        # Validate that this is a read-only query
        is_valid, error_message = validate_read_only_query(query)
        if not is_valid:
            return f"Error: {error_message}"
        
        try:
            if not connector.connect():
                return f"Failed to connect to database using secret '{secret_name}'. Please check your credentials."
            
            # Execute the query
            result = connector.execute_query(query)
            
            if not result:
                return "Query executed successfully but returned no results."
            
            # Limit the number of rows if specified
            if max_rows and len(result) > max_rows:
                result = result[:max_rows]
                response = f"Query returned {len(result)} rows (showing first {max_rows}):\n\n"
            else:
                response = f"Query returned {len(result)} rows:\n\n"
            
            # Format the results
            if result:
                # Get column names from the first row
                columns = list(result[0].keys())
                
                # Create header
                response += "| " + " | ".join(columns) + " |\n"
                response += "|" + "|".join(["---"] * len(columns)) + "|\n"
                
                # Add data rows
                for row in result:
                    response += "| " + " | ".join(str(row.get(col, '')) for col in columns) + " |\n"
            
            return response
            
        except Exception as e:
            return f"Error executing query: {str(e)}"
        finally:
            connector.disconnect()
    
    @mcp.tool()
    async def health_check(ctx: Context = None) -> str:
        """Check if the server is running and responsive."""
        return "✅ PostgreSQL Analyzer MCP server is healthy and running!"