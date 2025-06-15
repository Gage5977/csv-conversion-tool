#!/usr/bin/env python3
"""
MRI Import Generator
Generates MRI-compatible import files from trial balance activity
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional
import logging
from pathlib import Path


class MRIImportGenerator:
    """
    Generates MRI import files in the exact format required
    Replicates Excel MRI IMPORT sheet functionality
    """
    
    def __init__(self, system_config: Dict):
        self.logger = logging.getLogger(__name__)
        self.config = system_config
        self.mri_defaults = system_config.get('mri_defaults', {})
        self.entity_config = system_config.get('entity_config', {})
        
    def generate_import_records(self, 
                              activity_data: pd.DataFrame,
                              period: str,
                              entity_id: Optional[str] = None) -> pd.DataFrame:
        """
        Generate MRI import records from activity data
        
        Args:
            activity_data: DataFrame with account activity
            period: Period in MM/YY format (e.g., "04/25")
            entity_id: Entity identifier (defaults to config)
            
        Returns:
            DataFrame in MRI import format
        """
        try:
            if activity_data.empty:
                self.logger.warning("No activity data provided")
                return self._create_empty_import_df()
            
            # Use provided entity_id or default
            entity_id = entity_id or self.entity_config.get('default_entity_id', 'M55020')
            
            import_records = []
            
            for _, row in activity_data.iterrows():
                # Skip zero activity (already filtered in processor)
                if abs(row.get('Activity', 0)) < 0.01:
                    continue
                
                # Create import record
                record = self._create_import_record(
                    row=row,
                    period=period,
                    entity_id=entity_id
                )
                
                if record:
                    import_records.append(record)
            
            # Convert to DataFrame
            import_df = pd.DataFrame(import_records)
            
            if not import_df.empty:
                # Ensure proper column order
                import_df = self._ensure_column_order(import_df)
                # Validate import format
                self._validate_import_format(import_df)
            
            self.logger.info(f"Generated {len(import_df)} MRI import records")
            return import_df
            
        except Exception as e:
            self.logger.error(f"Error generating import records: {e}")
            return self._create_empty_import_df()
    
    def _create_import_record(self, row: pd.Series, period: str, entity_id: str) -> Optional[Dict]:
        """Create a single MRI import record"""
        try:
            # Get mapped account
            mri_account = row.get('MRI_Account', '')
            if not mri_account:
                self.logger.warning(f"No MRI account mapping for {row.get('Account', 'Unknown')}")
                return None
            
            # Calculate amount (activity amount)
            amount = row.get('Activity', 0)
            
            # Create record with all required fields
            record = {
                'PERIOD': self._format_period(period),
                'REF': self.mri_defaults.get('ref'),
                'SOURCE': self.mri_defaults.get('source', 'GA'),
                'ENTITYID': entity_id,
                'ACCTNUM': mri_account,
                'DEPARTMENT': self.mri_defaults.get('department', '@'),
                'AMT': round(amount, 2),
                'DESCRPN': row.get('Description', ''),
                'ENTRDATE': self._format_entry_date(period),
                'STATUS': self.mri_defaults.get('status', 'P'),
                'BASIS': self.mri_defaults.get('basis', 'B'),
                'AUDITFLAG': self.mri_defaults.get('auditflag'),
                'ADDLDESC': self.mri_defaults.get('addldesc'),
                'ASSETCLASS': self.mri_defaults.get('assetclass'),
                'ASSETCODE': self.mri_defaults.get('assetcode'),
                'INTERENTITY': self.mri_defaults.get('interentity')
            }
            
            return record
            
        except Exception as e:
            self.logger.error(f"Error creating import record: {e}")
            return None
    
    def _format_period(self, period: str) -> str:
        """Format period to MM/YY format"""
        try:
            # If already in MM/YY format, return as-is
            if re.match(r'\d{2}/\d{2}', period):
                return period
            
            # Try to parse various date formats
            if len(period) == 6:  # YYYYMM
                year = period[:4]
                month = period[4:6]
                return f"{month}/{year[2:]}"
            elif len(period) == 7 and period[4] == '-':  # YYYY-MM
                year, month = period.split('-')
                return f"{month}/{year[2:]}"
            
            # Default fallback
            current_date = datetime.now()
            return f"{current_date.month:02d}/{str(current_date.year)[2:]}"
            
        except Exception as e:
            self.logger.error(f"Error formatting period {period}: {e}")
            current_date = datetime.now()
            return f"{current_date.month:02d}/{str(current_date.year)[2:]}"
    
    def _format_entry_date(self, period: str) -> str:
        """Format entry date for MRI (YYYY-MM-DD HH:MM:SS)"""
        try:
            # Parse period to get year and month
            if '/' in period:  # MM/YY format
                month, year = period.split('/')
                full_year = f"20{year}" if len(year) == 2 else year
            else:
                # Use current date as fallback
                current = datetime.now()
                month = f"{current.month:02d}"
                full_year = str(current.year)
            
            # Use last day of month as entry date
            import calendar
            last_day = calendar.monthrange(int(full_year), int(month))[1]
            
            entry_date = datetime(int(full_year), int(month), last_day)
            return entry_date.strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            self.logger.error(f"Error formatting entry date: {e}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _create_empty_import_df(self) -> pd.DataFrame:
        """Create empty DataFrame with MRI import columns"""
        columns = [
            'PERIOD', 'REF', 'SOURCE', 'ENTITYID', 'ACCTNUM', 'DEPARTMENT',
            'AMT', 'DESCRPN', 'ENTRDATE', 'STATUS', 'BASIS', 'AUDITFLAG',
            'ADDLDESC', 'ASSETCLASS', 'ASSETCODE', 'INTERENTITY'
        ]
        return pd.DataFrame(columns=columns)
    
    def _ensure_column_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure DataFrame has correct MRI column order"""
        required_columns = [
            'PERIOD', 'REF', 'SOURCE', 'ENTITYID', 'ACCTNUM', 'DEPARTMENT',
            'AMT', 'DESCRPN', 'ENTRDATE', 'STATUS', 'BASIS', 'AUDITFLAG',
            'ADDLDESC', 'ASSETCLASS', 'ASSETCODE', 'INTERENTITY'
        ]
        
        # Add missing columns with None values
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        # Return with correct column order
        return df[required_columns]
    
    def _validate_import_format(self, df: pd.DataFrame) -> bool:
        """Validate MRI import format"""
        required_columns = [
            'PERIOD', 'SOURCE', 'ENTITYID', 'ACCTNUM', 'DEPARTMENT',
            'AMT', 'DESCRPN', 'ENTRDATE', 'STATUS', 'BASIS'
        ]
        
        # Check required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            self.logger.error(f"Missing required columns: {missing_cols}")
            return False
        
        # Check for required values
        if df['ENTITYID'].isna().any():
            self.logger.error("Missing ENTITYID values")
            return False
        
        if df['ACCTNUM'].isna().any():
            self.logger.error("Missing ACCTNUM values")
            return False
        
        # Validate numeric amounts
        if not pd.api.types.is_numeric_dtype(df['AMT']):
            self.logger.error("AMT column must be numeric")
            return False
        
        self.logger.info("MRI import format validation passed")
        return True
    
    def export_to_csv(self, import_df: pd.DataFrame, output_path: Path) -> bool:
        """Export MRI import data to CSV"""
        try:
            if import_df.empty:
                self.logger.warning("No data to export")
                # Create empty file with headers
                empty_df = self._create_empty_import_df()
                empty_df.to_csv(output_path, index=False)
                return True
            
            # Export with proper formatting
            import_df.to_csv(output_path, index=False, date_format='%Y-%m-%d %H:%M:%S')
            self.logger.info(f"MRI import file exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting MRI import file: {e}")
            return False
    
    def get_import_summary(self, import_df: pd.DataFrame) -> Dict:
        """Get summary statistics for import file"""
        if import_df.empty:
            return {
                'total_records': 0,
                'total_amount': 0.0,
                'unique_accounts': 0,
                'entities': [],
                'periods': []
            }
        
        return {
            'total_records': len(import_df),
            'total_amount': float(import_df['AMT'].sum()),
            'unique_accounts': len(import_df['ACCTNUM'].unique()),
            'entities': list(import_df['ENTITYID'].unique()),
            'periods': list(import_df['PERIOD'].unique()),
            'amount_range': {
                'min': float(import_df['AMT'].min()),
                'max': float(import_df['AMT'].max())
            }
        }