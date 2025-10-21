"""
Weighting Service
Handles weight column detection, application, and NCCS merging
"""
from typing import Dict, List, Any, Optional, Tuple
import re


class WeightingService:
    """
    Service for handling panel data weighting and NCCS merging

    Features:
    - Auto-detect weight columns
    - Apply weighting to query results
    - NCCS socioeconomic class merging (A+A1→A, C+D+E→C/D/E)
    """

    # Common weight column name patterns
    WEIGHT_PATTERNS = [
        'weight',
        'wt',
        'sample_weight',
        'user_weight',
        'respondent_weight',
        'panel_weight',
        'projection_weight'
    ]

    # NCCS column name patterns
    NCCS_PATTERNS = [
        'nccs',
        'sec',
        'socio_economic_class',
        'socioeconomic_class',
        'economic_class'
    ]

    def __init__(self):
        """Initialize weighting service"""
        pass

    def detect_weight_column(self, columns: List[str]) -> Optional[str]:
        """
        Detect weight column from list of column names

        Args:
            columns: List of column names

        Returns:
            Weight column name if found, None otherwise
        """
        columns_lower = [col.lower() for col in columns]

        for pattern in self.WEIGHT_PATTERNS:
            for i, col_lower in enumerate(columns_lower):
                if pattern in col_lower:
                    return columns[i]  # Return original case

        return None

    def detect_nccs_column(self, columns: List[str]) -> Optional[str]:
        """
        Detect NCCS (socioeconomic class) column

        Args:
            columns: List of column names

        Returns:
            NCCS column name if found, None otherwise
        """
        columns_lower = [col.lower() for col in columns]

        for pattern in self.NCCS_PATTERNS:
            for i, col_lower in enumerate(columns_lower):
                if pattern in col_lower:
                    return columns[i]  # Return original case

        return None

    def is_aggregated_query(self, query: str) -> bool:
        """
        Check if query is aggregated (has GROUP BY or aggregate functions)

        Args:
            query: SQL query string

        Returns:
            True if aggregated, False if raw data
        """
        query_upper = query.upper()

        # Check for GROUP BY
        if 'GROUP BY' in query_upper:
            return True

        # Check for aggregate functions
        agg_functions = ['COUNT(', 'SUM(', 'AVG(', 'MIN(', 'MAX(', 'STDDEV(', 'VARIANCE(']
        for func in agg_functions:
            if func in query_upper:
                return True

        return False

    def should_apply_5_row_limit(self, query: str, row_count: int) -> Tuple[bool, bool]:
        """
        Determine if 5-row limit should be applied

        Args:
            query: SQL query string
            row_count: Number of rows returned

        Returns:
            Tuple of (should_limit, is_raw_data)
        """
        is_raw = not self.is_aggregated_query(query)

        # Apply limit if:
        # 1. Query is raw data (no aggregation)
        # 2. More than 5 rows returned
        should_limit = is_raw and row_count > 5

        return should_limit, is_raw

    def apply_nccs_merging(
        self,
        rows: List[Dict[str, Any]],
        nccs_column: str
    ) -> List[Dict[str, Any]]:
        """
        Apply NCCS merging rules to results

        Rules:
        - A + A1 → A
        - C + D + E → C/D/E

        Args:
            rows: Query result rows
            nccs_column: Name of NCCS column

        Returns:
            Rows with NCCS values merged
        """
        if not rows or nccs_column not in rows[0]:
            return rows

        # Apply merging rules
        merged_rows = []
        for row in rows:
            nccs_value = row.get(nccs_column)

            if nccs_value:
                # Convert to string and uppercase
                nccs_str = str(nccs_value).strip().upper()

                # Rule 1: A1 → A
                if nccs_str == 'A1':
                    row[nccs_column] = 'A'

                # Rule 2: C, D, E → C/D/E
                elif nccs_str in ['C', 'D', 'E']:
                    row[nccs_column] = 'C/D/E'

            merged_rows.append(row)

        return merged_rows

    def apply_weighting(
        self,
        rows: List[Dict[str, Any]],
        weight_column: str,
        numeric_columns: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply weighting to numeric columns

        Args:
            rows: Query result rows
            weight_column: Name of weight column
            numeric_columns: List of numeric columns to weight (auto-detect if None)

        Returns:
            Tuple of (weighted_rows, metadata)
        """
        if not rows or weight_column not in rows[0]:
            return rows, {'weighted': False, 'reason': 'No weight column found'}

        # Auto-detect numeric columns if not provided
        if numeric_columns is None:
            numeric_columns = self._detect_numeric_columns(rows)

        # Remove weight column from numeric columns (don't weight the weight itself)
        numeric_columns = [col for col in numeric_columns if col != weight_column]

        if not numeric_columns:
            return rows, {'weighted': False, 'reason': 'No numeric columns to weight'}

        # Apply weighting
        weighted_rows = []
        total_weight = 0

        for row in rows:
            weight = row.get(weight_column)

            if weight is None or not isinstance(weight, (int, float)):
                weighted_rows.append(row)
                continue

            total_weight += weight

            # Create new row with weighted values
            weighted_row = row.copy()

            for col in numeric_columns:
                value = row.get(col)

                if value is not None and isinstance(value, (int, float)):
                    # Apply weight
                    weighted_row[f'{col}_weighted'] = value * weight

            weighted_rows.append(weighted_row)

        metadata = {
            'weighted': True,
            'weight_column': weight_column,
            'weighted_columns': numeric_columns,
            'total_weight': total_weight,
            'row_count': len(weighted_rows)
        }

        return weighted_rows, metadata

    def _detect_numeric_columns(self, rows: List[Dict[str, Any]]) -> List[str]:
        """
        Detect numeric columns from data

        Args:
            rows: Query result rows

        Returns:
            List of numeric column names
        """
        if not rows:
            return []

        numeric_cols = []
        first_row = rows[0]

        for col, value in first_row.items():
            if isinstance(value, (int, float)) and value is not None:
                numeric_cols.append(col)

        return numeric_cols

    def validate_weighting_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that query is appropriate for weighting

        Args:
            query: SQL query string

        Returns:
            Tuple of (is_valid, warning_message)
        """
        query_upper = query.upper()

        # Check if query includes weight column
        has_weight_col = any(pattern.upper() in query_upper for pattern in self.WEIGHT_PATTERNS)

        if not has_weight_col:
            return False, "Warning: Query does not include weight column. Add weight column for accurate population estimates."

        # Check if query is aggregating at event level (not user level)
        # This is a heuristic - may need refinement
        if 'GROUP BY' in query_upper:
            # Good - has aggregation
            # Check if grouping by user/respondent
            has_user_group = any(
                keyword in query_upper
                for keyword in ['USER_ID', 'RESPONDENT_ID', 'PANELIST_ID', 'USER ']
            )

            if not has_user_group:
                return True, "Note: Ensure you're aggregating at user level, not event level."

        return True, None

    def format_weighted_result_summary(self, metadata: Dict[str, Any]) -> str:
        """
        Format weighting metadata as Markdown summary

        Args:
            metadata: Weighting metadata dict

        Returns:
            Markdown formatted summary
        """
        if not metadata.get('weighted', False):
            return ""

        md = "\n### Weighting Applied\n\n"
        md += f"- **Weight Column**: `{metadata.get('weight_column')}`\n"
        md += f"- **Total Weight**: {metadata.get('total_weight', 0):,.2f}\n"
        md += f"- **Weighted Columns**: {', '.join(f'`{col}`' for col in metadata.get('weighted_columns', []))}\n"
        md += f"- **Population Represented**: ~{int(metadata.get('total_weight', 0)):,} individuals\n"
        md += "\n"

        return md

    def get_weighting_instructions(self) -> str:
        """
        Get instructions for using weighting in queries

        Returns:
            Markdown formatted instructions
        """
        return """
## Weighting Instructions

When querying panel data, follow these rules:

1. **Always include weight column** in SELECT clause
2. **Aggregate at user level**, not event level:
   - ✓ Good: `SELECT user_id, SUM(events * weight) FROM ...`
   - ✗ Bad: `SELECT event_id, weight FROM ...`

3. **Use SUM(metric * weight)** for weighted totals
4. **Use SUM(metric * weight) / SUM(weight)** for weighted averages

5. **Example queries**:
   ```sql
   -- Weighted average spend per user
   SELECT
     gender,
     SUM(spend * weight) / SUM(weight) as avg_spend_weighted
   FROM users
   GROUP BY gender

   -- Total weighted population
   SELECT SUM(weight) as total_population FROM users
   ```

**NCCS Merging**: A1→A, C/D/E→C/D/E (applied automatically)
"""


# Global instance
weighting_service = WeightingService()
