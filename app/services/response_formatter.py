"""
Response Formatter Service
Converts query results from JSON to Markdown for 50% token savings
"""
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, date


class ResponseFormatter:
    """Format query results as Markdown for better LLM token efficiency"""

    @staticmethod
    def format_dataset_list(datasets: List[Dict[str, Any]]) -> str:
        """
        Format dataset list as Markdown table with rich information

        Args:
            datasets: List of dataset dicts with id, name, description, stats, metadata status

        Returns:
            Markdown formatted string optimized for executive decision-making
        """
        if not datasets:
            return "_No datasets available._"

        md = "# 📊 Available Datasets\n\n"
        md += f"**Total Datasets**: {len(datasets)}\n\n"
        
        # Add executive-level context
        md += "## Overview\n\n"
        md += "These datasets contain analytics data for strategic decision-making. "
        md += "Each dataset includes CTV, mobile, and digital platform metrics for media planning and ecommerce strategy.\n\n"
        
        md += "| ID | Dataset Name | Records | Tables | Metadata | Description |\n"
        md += "|:---:|---|---:|:---:|:---:|---|\n"

        for ds in datasets:
            name = ds.get('name', 'Unknown')
            desc = ds.get('description', 'No description')[:80]
            row_count = f"{ds.get('row_count', 0):,}" if ds.get('row_count') else "N/A"
            table_count = ds.get('table_count', 0)
            has_metadata = "✅" if ds.get('has_metadata') else "⚠️"
            
            md += f"| {ds['id']} | **{name}** | {row_count} | {table_count} | {has_metadata} | {desc} |\n"

        md += "\n## Legend\n\n"
        md += "- **Metadata**: ✅ = AI-generated descriptions available, ⚠️ = Schema only\n"
        md += "- **Records**: Total number of data points in primary table\n\n"
        
        md += "## Next Steps\n\n"
        md += "1. **Identify relevant dataset(s)** based on your analysis needs\n"
        md += "2. **Get detailed schema**: Use `get_dataset_schema(dataset_id)` for column details\n"
        md += "3. **Review sample data**: Use `get_dataset_sample(dataset_id, table_name)` to see actual data\n"
        md += "4. **Execute analysis**: Use `query_dataset()` or `execute_multi_query()` for insights\n\n"
        
        md += "---\n\n"
        md += "**🎯 Analysis Guidelines**: Your audience consists of senior brand managers and executives. "
        md += "Provide PhD-level analysis with actionable insights. Use tables and visualizations. "
        md += "Focus on strategic implications for media spend allocation and ecommerce planning.\n"

        return md

    @staticmethod
    def format_dataset_schema(
        dataset_id: int,
        dataset_name: str,
        dataset_description: Optional[str],
        tables: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Format dataset schema as Markdown

        Args:
            dataset_id: Dataset ID
            dataset_name: Dataset name
            dataset_description: Dataset description
            tables: Dict mapping table_name -> list of column dicts

        Returns:
            Markdown formatted schema
        """
        md = f"# Dataset: {dataset_name} (ID: {dataset_id})\n\n"

        if dataset_description:
            md += f"**Description**: {dataset_description}\n\n"

        md += f"**Total Tables**: {len(tables)}\n\n"
        md += "---\n\n"

        for table_name, columns in tables.items():
            md += f"## Table: `{table_name}`\n\n"
            md += f"**Columns**: {len(columns)}\n\n"
            md += "| Column | Type | Nullable | Description |\n"
            md += "|---|---|---|---|\n"

            for col in columns:
                nullable = "✓" if col.get('is_nullable', False) else "✗"
                description = col.get('description', 'No description available')[:80]
                md += f"| `{col['column_name']}` | {col['data_type']} | {nullable} | {description} |\n"

            md += "\n"

        md += "---\n\n"
        md += "## 📋 Analysis & Query Guidelines\n\n"
        md += "**User Persona**: CMI team for large brands - provide insights like a seasoned brand manager\n\n"
        md += "**Critical Rules**:\n"
        md += "1. **Weighting**: ALWAYS use weighted aggregation (`SUM(weights)`) - weight users, not events\n"
        md += "2. **Raw Data**: Limit to 5 rows maximum - use aggregation (GROUP BY) for larger datasets\n"
        md += "3. **Panel Data**: Report for personas (e.g., \"average per female user/day\", not absolute totals)\n"
        md += "4. **NCCS**: A+A1→A, C/D/E→C/D/E (auto-merged by system)\n"
        md += "5. **Context**: Keep queries specific to avoid token overflow\n\n"
        md += "**Response Style**:\n"
        md += "- Detailed, actionable insights for brand managers\n"
        md += "- Focus on media planning and ecommerce strategy\n"
        md += "- Use tables/visualizations, less verbose, more analysis\n"
        md += "- Provide comparative analysis and trends\n\n"
        md += "**PostgreSQL Syntax**:\n"
        md += "- ROUND: `ROUND(value::numeric, 2)`\n"
        md += "- NULL: `COALESCE(column, 0)`\n"
        md += "- String agg: `STRING_AGG(column, ', ')`\n"
        md += "- Date math: `date + INTERVAL '7 days'`\n\n"
        md += "---\n\n"
        md += f"**Usage**: Use `query_dataset({dataset_id}, \"SELECT ...\")` to query this dataset.\n"

        return md

    @staticmethod
    def format_query_result(
        result: Dict[str, Any],
        query: str = "",
        is_raw_data: bool = False,
        row_limit_applied: bool = False
    ) -> str:
        """
        Format query results as Markdown table

        Args:
            result: Query result dict with 'rows', 'columns', 'row_count'
            query: Original SQL query (optional)
            is_raw_data: Whether this is raw data (no aggregation)
            row_limit_applied: Whether 5-row limit was applied

        Returns:
            Markdown formatted results
        """
        if not result.get('success', True):
            return f"**Error**: {result.get('error', 'Unknown error')}"

        rows = result.get('rows', [])
        columns = result.get('columns', [])
        row_count = result.get('row_count', 0)

        md = "# Query Results\n\n"

        # Warning for raw data limit
        if row_limit_applied and is_raw_data:
            md += "⚠️ **Note**: Raw data limited to 5 rows. For larger datasets, use aggregation (GROUP BY).\n\n"

        # Metadata
        md += f"**Rows Returned**: {row_count}\n"
        if query:
            md += f"**Query**: `{query[:100]}{'...' if len(query) > 100 else ''}`\n"
        md += "\n"

        # No results case
        if row_count == 0:
            return md + "_No results found._\n"

        # Format as table
        md += ResponseFormatter._format_table(rows, columns)
        
        # No repetitive reminders - keep response clean

        return md

    @staticmethod
    def format_sample_data(
        dataset_id: int,
        table_name: str,
        sample_size: int,
        columns: List[str],
        data: List[Dict[str, Any]]
    ) -> str:
        """
        Format sample data as Markdown

        Args:
            dataset_id: Dataset ID
            table_name: Table name
            sample_size: Number of rows sampled
            columns: Column names
            data: Sample data rows

        Returns:
            Markdown formatted sample
        """
        md = f"# Sample Data: {table_name}\n\n"
        md += f"**Dataset ID**: {dataset_id}\n"
        md += f"**Sample Size**: {sample_size} rows\n\n"

        if not data:
            return md + "_No data available._\n"

        md += ResponseFormatter._format_table(data, columns)

        md += "\n**Usage**: This is sample data. Use `query_dataset()` for custom queries.\n"

        return md

    @staticmethod
    def _format_table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
        """
        Format data rows as Markdown table

        Args:
            rows: List of row dicts
            columns: List of column names

        Returns:
            Markdown table string
        """
        if not rows or not columns:
            return "_No data to display._\n"

        # Table header
        md = "| " + " | ".join(columns) + " |\n"
        md += "|" + "|".join(["---"] * len(columns)) + "|\n"

        # Table rows
        for row in rows:
            values = []
            for col in columns:
                value = row.get(col)
                formatted_value = ResponseFormatter._format_value(value)
                values.append(formatted_value)
            md += "| " + " | ".join(values) + " |\n"

        return md + "\n"

    @staticmethod
    def _format_value(value: Any) -> str:
        """
        Format a single cell value for Markdown table

        Args:
            value: Cell value

        Returns:
            Formatted string
        """
        if value is None:
            return "_null_"
        elif isinstance(value, (datetime, date)):
            return value.strftime('%Y-%m-%d %H:%M:%S') if isinstance(value, datetime) else value.strftime('%Y-%m-%d')
        elif isinstance(value, float):
            # Round floats to 2 decimal places
            return f"{value:.2f}"
        elif isinstance(value, bool):
            return "✓" if value else "✗"
        elif isinstance(value, (list, dict)):
            # Truncate complex types
            return str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        else:
            # Convert to string and truncate if too long
            str_value = str(value)
            return str_value[:100] + "..." if len(str_value) > 100 else str_value

    @staticmethod
    def format_error(error_message: str, context: str = "") -> str:
        """
        Format error message as Markdown

        Args:
            error_message: Error message
            context: Additional context (optional)

        Returns:
            Markdown formatted error
        """
        md = "# Error\n\n"
        md += f"**Error**: {error_message}\n\n"

        if context:
            md += f"**Context**: {context}\n\n"

        md += "**Tip**: Check the query syntax and dataset availability.\n"

        return md

    @staticmethod
    def format_multi_query_results(
        results: List[Dict[str, Any]],
        queries: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Format multiple query results as single Markdown document

        Args:
            results: List of query result dicts
            queries: List of query dicts with 'label' field
            metadata: Overall execution metadata (total_queries, successful, failed, etc.)

        Returns:
            Markdown formatted multi-query results
        """
        md = "# Multi-Query Results\n\n"

        # Summary statistics
        md += f"**Total Queries**: {metadata.get('total_queries', len(results))}\n"
        md += f"**Successful**: {metadata.get('successful', 0)} ✅\n"

        if metadata.get('failed', 0) > 0:
            md += f"**Failed**: {metadata.get('failed', 0)} ❌\n"

        md += f"**Total Execution Time**: {metadata.get('total_execution_time_ms', 0)}ms\n\n"

        # Performance note if parallel execution worked
        if metadata.get('total_queries', 0) > 1:
            avg_time = metadata.get('total_execution_time_ms', 0)
            md += f"_⚡ Executed in parallel - {metadata.get('total_queries', 0)} queries in {avg_time}ms!_\n\n"

        md += "---\n\n"

        # Individual query results
        for i, result in enumerate(results):
            query_def = queries[i] if i < len(queries) else {}
            label = result.get('label') or query_def.get('label', f'Query {i+1}')

            md += f"## {i+1}. {label}\n\n"

            if result.get('success', False):
                # Format individual result
                rows = result.get('rows', [])
                columns = result.get('columns', [])
                row_count = result.get('row_count', 0)

                # Metadata line
                md += f"**Rows**: {row_count}"
                if result.get('execution_time_ms'):
                    md += f" | **Time**: {result['execution_time_ms']}ms"
                if result.get('dataset_name'):
                    md += f" | **Dataset**: {result['dataset_name']}"
                md += "\n\n"

                # Warning for raw data limit
                if result.get('row_limit_applied') and not result.get('is_aggregated'):
                    md += "⚠️ **Note**: Raw data limited to 5 rows. Use aggregation for more.\n\n"

                # Data table
                if row_count > 0:
                    md += ResponseFormatter._format_table(rows, columns)
                else:
                    md += "_No results._\n\n"

                # Weight/NCCS info
                if result.get('weight_column'):
                    md += f"_Weight column detected: `{result['weight_column']}`_\n"
                if result.get('nccs_column'):
                    md += f"_NCCS merging applied: {result['nccs_column']}_\n"

            else:
                # Error case
                md += f"**Error**: {result.get('error', 'Unknown error')}\n\n"
                if result.get('query'):
                    md += f"**Query**: `{result['query'][:100]}{'...' if len(result.get('query', '')) > 100 else ''}`\n\n"

            md += "---\n\n"

        # Footer with tips
        md += "**Tips**:\n"
        md += "- Raw queries are limited to 5 rows\n"
        md += "- Use GROUP BY for aggregated data (no row limit)\n"
        md += "- Include weight columns for accurate population estimates\n"

        return md

    @staticmethod
    def format_context_level_0() -> str:
        """
        Format Level 0 global context (always included)

        Returns:
            Markdown with global rules
        """
        return """# MCP Analytics Server - Global Context

## Data Source
- **Sample representative population** from smartphones/CTV
- Collected **consentfully** using proprietary technology
- Panel data with **weighting methodology**

## Weighting Rules (CRITICAL)
- Each user carries a **weight** (e.g., 0.456 = represents 456 individuals in population)
- **Cell** = age/gender/NCCS/townclass/state combination
- **ALWAYS report at weighted level** (weigh users, NOT individual events)
- Only weigh users, not transactions/events

## Output Rules
- **Maximum 5 raw-level rows** in output
- For larger datasets, use **aggregation** (GROUP BY) or provide summaries
- Prefer **persona-level aggregations** (e.g., "avg for Female 25-34")

## NCCS Merging (Socioeconomic Classes)
- Merge **A + A1 → A**
- Merge **C + D + E → C/D/E**
- Apply automatically when NCCS column detected

## Data Types
- **Event-level**: Individual user events (large, granular)
- **Aggregated**: Pre-processed summaries (smaller, faster)

## Available Tools
- `list_available_datasets()` - Get all active datasets
- `get_dataset_schema(dataset_id)` - Get detailed schema with AI descriptions
- `query_dataset(dataset_id, query)` - Run SQL query with automatic weighting
- `get_dataset_sample(dataset_id, table_name)` - Get sample data

---
"""
