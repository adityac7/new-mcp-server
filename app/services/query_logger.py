"""
Query Logger Service
Logs all MCP queries to database for tracking and analytics
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import QueryLog


class QueryLoggerService:
    """Service for logging query execution to database"""

    @staticmethod
    def detect_client_tool(user_agent: str = "", headers: Dict[str, str] = None) -> str:
        """
        Detect which MCP client tool is being used

        Args:
            user_agent: User-Agent header value
            headers: Full request headers dict

        Returns:
            Client tool name (chatgpt, claude, cursor, api, unknown)
        """
        if headers is None:
            headers = {}

        user_agent_lower = user_agent.lower()

        # Check user agent
        if 'claude' in user_agent_lower:
            return 'claude'
        elif 'chatgpt' in user_agent_lower or 'openai' in user_agent_lower:
            return 'chatgpt'
        elif 'cursor' in user_agent_lower:
            return 'cursor'
        elif 'cline' in user_agent_lower:
            return 'cline'
        elif 'manus' in user_agent_lower:
            return 'manus'

        # Check custom headers
        mcp_client = headers.get('x-mcp-client', '').lower()
        if mcp_client:
            return mcp_client

        # Check if from API
        if 'python' in user_agent_lower or 'requests' in user_agent_lower:
            return 'api'

        return 'unknown'

    @staticmethod
    def log_query(
        db: Session,
        query_text: str,
        dataset_id: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        row_count: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        tool_used: str = 'unknown',
        user_agent: str = '',
        client_info: Optional[Dict[str, Any]] = None
    ) -> QueryLog:
        """
        Log a query execution to database

        Args:
            db: Database session
            query_text: SQL query or tool invocation
            dataset_id: ID of dataset queried (if applicable)
            execution_time_ms: Execution time in milliseconds
            row_count: Number of rows returned
            success: Whether query succeeded
            error_message: Error message if failed
            tool_used: Client tool name
            user_agent: User-Agent header
            client_info: Additional client metadata

        Returns:
            Created QueryLog object
        """
        log_entry = QueryLog(
            dataset_id=dataset_id,
            query=query_text,
            executed_at=datetime.utcnow(),
            execution_time_ms=execution_time_ms,
            row_count=row_count,
            success=success,
            error_message=error_message,
            client_info=client_info or {}
        )

        # Store tool_used in client_info if not already there
        if 'tool' not in log_entry.client_info:
            log_entry.client_info['tool'] = tool_used

        # Store user agent
        if user_agent and 'user_agent' not in log_entry.client_info:
            log_entry.client_info['user_agent'] = user_agent

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        return log_entry

    @staticmethod
    def log_mcp_tool_call(
        db: Session,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        execution_time_ms: int,
        tool_used: str = 'unknown'
    ) -> QueryLog:
        """
        Log an MCP tool invocation

        Args:
            db: Database session
            tool_name: Name of MCP tool called
            parameters: Tool parameters
            result: Tool result
            execution_time_ms: Execution time
            tool_used: Client tool name

        Returns:
            Created QueryLog object
        """
        # Format query text
        query_text = f"MCP Tool: {tool_name}"
        if parameters:
            query_text += f" | Params: {parameters}"

        # Extract dataset_id if present
        dataset_id = parameters.get('dataset_id')

        # Extract row count if present in result
        row_count = None
        if isinstance(result, dict):
            row_count = result.get('row_count') or result.get('rows', 0)

        # Check success
        success = result.get('success', True) if isinstance(result, dict) else True
        error_message = result.get('error') if isinstance(result, dict) else None

        return QueryLoggerService.log_query(
            db=db,
            query_text=query_text,
            dataset_id=dataset_id,
            execution_time_ms=execution_time_ms,
            row_count=row_count,
            success=success,
            error_message=error_message,
            tool_used=tool_used,
            client_info={
                'tool_name': tool_name,
                'parameters': parameters
            }
        )

    @staticmethod
    def get_query_stats(db: Session, days: int = 7) -> Dict[str, Any]:
        """
        Get query statistics for the last N days

        Args:
            db: Database session
            days: Number of days to look back

        Returns:
            Statistics dict
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all logs since cutoff
        logs = db.query(QueryLog).filter(
            QueryLog.executed_at >= cutoff_date
        ).all()

        if not logs:
            return {
                'total_queries': 0,
                'successful_queries': 0,
                'failed_queries': 0,
                'avg_execution_time_ms': 0,
                'queries_by_tool': {},
                'queries_by_dataset': {}
            }

        # Calculate stats
        total = len(logs)
        successful = sum(1 for log in logs if log.success)
        failed = total - successful

        # Average execution time
        exec_times = [log.execution_time_ms for log in logs if log.execution_time_ms]
        avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0

        # Queries by tool
        queries_by_tool = {}
        for log in logs:
            tool = log.client_info.get('tool', 'unknown') if log.client_info else 'unknown'
            queries_by_tool[tool] = queries_by_tool.get(tool, 0) + 1

        # Queries by dataset
        queries_by_dataset = {}
        for log in logs:
            if log.dataset_id:
                queries_by_dataset[log.dataset_id] = queries_by_dataset.get(log.dataset_id, 0) + 1

        return {
            'total_queries': total,
            'successful_queries': successful,
            'failed_queries': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'avg_execution_time_ms': round(avg_exec_time, 2),
            'queries_by_tool': queries_by_tool,
            'queries_by_dataset': queries_by_dataset,
            'period_days': days
        }


# Global instance
query_logger = QueryLoggerService()
