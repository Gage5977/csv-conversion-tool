#!/usr/bin/env python3
"""
Enhanced Trial Balance Processor
Main processing engine replicating Excel Trial Balance Conversion Tool
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from ..engines.account_mapping_engine import AccountMappingEngine
from ..engines.mri_import_generator import MRIImportGenerator
from ..validators.validation_engine import ValidationEngine


class EnhancedTrialBalanceProcessor:
    """
    Enhanced processor that replicates Excel Trial Balance Conversion Tool functionality
    Includes account mapping, MRI import generation, and comprehensive validation
    """
    
    def __init__(self, config_dir: Path):
        self.logger = self._setup_logging()
        self.config_dir = Path(config_dir)
        
        # Load system configuration
        self.system_config = self._load_system_config()
        
        # Initialize engines
        self.mapping_engine = AccountMappingEngine(config_dir / 'data' / 'mappings')
        self.import_generator = MRIImportGenerator(self.system_config)
        self.validation_engine = ValidationEngine(self.system_config)
        
        # Data storage
        self.prior_tb = None
        self.current_tb = None
        self.activity_data = None
        self.mri_import_data = None
        self.validation_results = None
        
    def _setup_logging(self):
        """Configure logging"""
        logger = logging.getLogger('EnhancedTrialBalanceProcessor')
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _load_system_config(self) -> Dict:
        """Load system configuration"""
        try:
            config_file = self.config_dir / 'config' / 'system_config.json'
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading system config: {e}")
            return {}
    
    def load_trial_balances(self, prior_path: Path, current_path: Path) -> bool:
        """Load and parse trial balance files (CSV or Excel)"""
        try:
            # Load files
            self.prior_tb = self._load_trial_balance_file(prior_path, "Prior")
            self.current_tb = self._load_trial_balance_file(current_path, "Current")
            
            if self.prior_tb is None or self.current_tb is None:
                return False
            
            # Clean and standardize data
            self.prior_tb = self._clean_trial_balance_data(self.prior_tb)
            self.current_tb = self._clean_trial_balance_data(self.current_tb)
            
            self.logger.info(f"Trial balances loaded - Prior: {len(self.prior_tb)} accounts, Current: {len(self.current_tb)} accounts")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading trial balances: {e}")
            return False
    
    def _load_trial_balance_file(self, file_path: Path, period_name: str) -> Optional[pd.DataFrame]:
        """Load trial balance file (CSV or Excel)"""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                # Try to detect trial balance data in Excel file
                df = self._parse_excel_trial_balance(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            if df is None or df.empty:
                raise ValueError(f"No data found in {period_name} trial balance file")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading {period_name} trial balance file {file_path}: {e}")
            return None
    
    def _parse_excel_trial_balance(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Parse Excel trial balance file (handles complex formats)"""
        try:
            # Read Excel file and find trial balance data
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                
                # Look for trial balance indicators
                tb_indicators = ['GL Account', 'Account', 'Balance Forward', 'Ending Balance']
                
                for i, row in df.iterrows():
                    row_str = ' '.join(str(cell) for cell in row if pd.notna(cell))
                    if any(indicator in row_str for indicator in tb_indicators):
                        # Found header row, parse from here
                        header_row = i
                        tb_df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
                        
                        # Clean up the dataframe
                        tb_df = tb_df.dropna(how='all')  # Remove empty rows
                        
                        # Standardize column names
                        tb_df = self._standardize_excel_columns(tb_df)
                        
                        if self._is_valid_trial_balance(tb_df):
                            return tb_df
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing Excel trial balance: {e}")
            return None
    
    def _standardize_excel_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Excel column names to expected format"""
        column_mapping = {
            'GL Account': 'Account',
            'Description': 'Description',
            'Balance Forward': 'Balance_Forward',
            'Debit': 'Debit',
            'Credit': 'Credit',
            'Ending Balance': 'Ending_Balance'
        }
        
        # Find and rename columns
        for excel_col, standard_col in column_mapping.items():
            matching_cols = [col for col in df.columns if excel_col in str(col)]
            if matching_cols:
                df = df.rename(columns={matching_cols[0]: standard_col})
        
        # Calculate Net balance if not present
        if 'Net' not in df.columns:
            if 'Ending_Balance' in df.columns:
                df['Net'] = df['Ending_Balance']
            elif 'Debit' in df.columns and 'Credit' in df.columns:
                df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
                df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
                df['Net'] = df['Debit'] - df['Credit']
        
        return df
    
    def _is_valid_trial_balance(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame contains valid trial balance data"""
        required_columns = ['Account']
        has_required = all(col in df.columns for col in required_columns)
        has_data = len(df) > 0
        return has_required and has_data
    
    def _clean_trial_balance_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize trial balance data"""
        try:
            df = df.copy()
            
            # Remove total rows
            df = df[~df['Account'].astype(str).str.upper().str.contains('TOTAL', na=False)]
            
            # Remove empty accounts
            df = df[df['Account'].notna() & (df['Account'].astype(str).str.strip() != '')]
            
            # Ensure numeric columns
            numeric_cols = ['Debit', 'Credit', 'Net', 'Ending_Balance', 'Balance_Forward']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Calculate Net if not present
            if 'Net' not in df.columns:
                if 'Debit' in df.columns and 'Credit' in df.columns:
                    df['Net'] = df['Debit'] - df['Credit']
                elif 'Ending_Balance' in df.columns:
                    df['Net'] = df['Ending_Balance']
            
            # Clean account codes
            df['Account'] = df['Account'].astype(str).str.strip()
            
            # Ensure Description column exists
            if 'Description' not in df.columns:
                df['Description'] = df['Account']
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error cleaning trial balance data: {e}")
            return df
    
    def calculate_activity_with_mapping(self) -> bool:
        """Calculate activity and apply account mappings"""
        try:
            if self.prior_tb is None or self.current_tb is None:
                raise ValueError("Trial balance data not loaded")
            
            # Merge prior and current on account
            merged = pd.merge(
                self.prior_tb[['Account', 'Description', 'Net']].rename(columns={'Net': 'Prior_Net'}),
                self.current_tb[['Account', 'Description', 'Net']].rename(columns={'Net': 'Current_Net'}),
                on='Account',
                how='outer',
                suffixes=('_prior', '_current')
            ).fillna(0)
            
            # Use description from current period, fallback to prior
            merged['Description'] = merged['Description_current'].fillna(merged['Description_prior'])
            merged = merged.drop(['Description_prior', 'Description_current'], axis=1)
            
            # Calculate activity
            merged['Activity'] = merged['Current_Net'] - merged['Prior_Net']
            
            # Apply account mappings
            merged['MRI_Account'] = merged['Account'].apply(
                lambda x: self.mapping_engine.transform_account(x, merged[merged['Account'] == x]['Description'].iloc[0] if len(merged[merged['Account'] == x]) > 0 else "")
            )
            
            # Filter out unmapped accounts if required
            if self.system_config.get('validation_rules', {}).get('require_account_mapping', True):
                unmapped_accounts = merged[merged['MRI_Account'].isna()]['Account'].tolist()
                if unmapped_accounts:
                    self.logger.warning(f"Unmapped accounts found: {unmapped_accounts}")
                
                merged = merged[merged['MRI_Account'].notna()]
            
            # Apply materiality threshold
            threshold = self.system_config.get('processing_rules', {}).get('materiality_threshold', 0.01)
            merged = merged[np.abs(merged['Activity']) >= threshold]
            
            self.activity_data = merged
            
            self.logger.info(f"Activity calculated with mappings - {len(self.activity_data)} accounts with material changes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error calculating activity with mapping: {e}")
            return False
    
    def generate_mri_import_file(self, period: str, entity_id: Optional[str] = None) -> bool:
        """Generate MRI import file"""
        try:
            if self.activity_data is None:
                raise ValueError("Activity data not calculated")
            
            # Generate MRI import records
            self.mri_import_data = self.import_generator.generate_import_records(
                self.activity_data,
                period,
                entity_id
            )
            
            self.logger.info(f"MRI import file generated with {len(self.mri_import_data)} records")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating MRI import file: {e}")
            return False
    
    def run_comprehensive_validation(self) -> bool:
        """Run comprehensive validation suite"""
        try:
            if self.prior_tb is None or self.current_tb is None or self.activity_data is None:
                raise ValueError("Required data not loaded")
            
            # Get account mappings for validation
            account_mappings = {}
            for _, row in self.activity_data.iterrows():
                if pd.notna(row['MRI_Account']):
                    account_mappings[row['Account']] = row['MRI_Account']
            
            # Run validation
            self.validation_results = self.validation_engine.validate_pre_import(
                self.prior_tb,
                self.current_tb,
                self.activity_data,
                account_mappings
            )
            
            status = self.validation_results['overall_status']
            self.logger.info(f"Comprehensive validation completed: {status}")
            return status in ['PASS', 'WARNING']
            
        except Exception as e:
            self.logger.error(f"Error running validation: {e}")
            return False
    
    def export_mri_import_file(self, output_path: Path) -> bool:
        """Export MRI import file to CSV"""
        try:
            if self.mri_import_data is None:
                raise ValueError("MRI import data not generated")
            
            return self.import_generator.export_to_csv(self.mri_import_data, output_path)
            
        except Exception as e:
            self.logger.error(f"Error exporting MRI import file: {e}")
            return False
    
    def get_processing_summary(self) -> Dict:
        """Get comprehensive processing summary"""
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'status': 'completed' if self.mri_import_data is not None else 'incomplete'
            }
            
            # Data summary
            if self.prior_tb is not None and self.current_tb is not None:
                summary['trial_balance_summary'] = {
                    'prior_accounts': len(self.prior_tb),
                    'current_accounts': len(self.current_tb),
                    'total_unique_accounts': len(set(self.prior_tb['Account'].tolist() + self.current_tb['Account'].tolist()))
                }
            
            # Activity summary
            if self.activity_data is not None:
                summary['activity_summary'] = {
                    'accounts_with_activity': len(self.activity_data),
                    'total_activity_amount': float(self.activity_data['Activity'].abs().sum()),
                    'mapped_accounts': len(self.activity_data[self.activity_data['MRI_Account'].notna()]),
                    'unmapped_accounts': len(self.activity_data[self.activity_data['MRI_Account'].isna()])
                }
            
            # Import summary
            if self.mri_import_data is not None:
                summary['import_summary'] = self.import_generator.get_import_summary(self.mri_import_data)
            
            # Validation summary
            if self.validation_results is not None:
                summary['validation_summary'] = {
                    'overall_status': self.validation_results['overall_status'],
                    'validations_run': len(self.validation_results['validations']),
                    'failed_validations': self.validation_results.get('failed_validations', [])
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating processing summary: {e}")
            return {'error': str(e)}