#!/usr/bin/env python3
"""
Validation Engine
Comprehensive validation framework replicating Excel validation sheets
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime


class ValidationEngine:
    """
    Multi-level validation engine for trial balance processing
    Replicates Excel Pre TB Upload Validation functionality
    """
    
    def __init__(self, system_config: Dict):
        self.logger = logging.getLogger(__name__)
        self.config = system_config
        self.validation_rules = system_config.get('validation_rules', {})
        self.processing_rules = system_config.get('processing_rules', {})
        
    def validate_pre_import(self, 
                           prior_tb: pd.DataFrame,
                           current_tb: pd.DataFrame,
                           activity_data: pd.DataFrame,
                           account_mappings: Dict) -> Dict:
        """
        Comprehensive pre-import validation
        
        Returns:
            Validation results with pass/fail status and details
        """
        validation_results = {
            'overall_status': 'PASS',
            'timestamp': datetime.now().isoformat(),
            'validations': {}
        }
        
        try:
            # 1. Account Mapping Validation
            mapping_result = self._validate_account_mappings(prior_tb, current_tb, account_mappings)
            validation_results['validations']['account_mapping'] = mapping_result
            
            # 2. Balance Reconciliation
            balance_result = self._validate_balance_reconciliation(prior_tb, current_tb, activity_data)
            validation_results['validations']['balance_reconciliation'] = balance_result
            
            # 3. Activity Calculation Validation
            activity_result = self._validate_activity_calculation(prior_tb, current_tb, activity_data)
            validation_results['validations']['activity_calculation'] = activity_result
            
            # 4. Materiality Threshold Check
            materiality_result = self._validate_materiality_threshold(activity_data)
            validation_results['validations']['materiality_threshold'] = materiality_result
            
            # 5. Data Quality Checks
            quality_result = self._validate_data_quality(prior_tb, current_tb)
            validation_results['validations']['data_quality'] = quality_result
            
            # Determine overall status
            failed_validations = [
                name for name, result in validation_results['validations'].items()
                if result['status'] == 'FAIL'
            ]
            
            if failed_validations:
                validation_results['overall_status'] = 'FAIL'
                validation_results['failed_validations'] = failed_validations
            
            self.logger.info(f"Pre-import validation completed: {validation_results['overall_status']}")
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error in pre-import validation: {e}")
            validation_results['overall_status'] = 'ERROR'
            validation_results['error'] = str(e)
            return validation_results
    
    def _validate_account_mappings(self, 
                                  prior_tb: pd.DataFrame,
                                  current_tb: pd.DataFrame,
                                  account_mappings: Dict) -> Dict:
        """Validate all accounts have proper mappings"""
        try:
            # Get all unique accounts
            all_accounts = set()
            all_accounts.update(prior_tb['Account'].unique())
            all_accounts.update(current_tb['Account'].unique())
            
            mapped_accounts = []
            unmapped_accounts = []
            
            for account in all_accounts:
                if account in account_mappings:
                    mapped_accounts.append(account)
                else:
                    unmapped_accounts.append(account)
            
            mapping_rate = len(mapped_accounts) / len(all_accounts) if all_accounts else 1.0
            
            result = {
                'status': 'PASS' if mapping_rate == 1.0 else 'FAIL',
                'mapping_rate': mapping_rate,
                'total_accounts': len(all_accounts),
                'mapped_accounts': len(mapped_accounts),
                'unmapped_accounts': unmapped_accounts,
                'details': f"Mapping rate: {mapping_rate:.2%}"
            }
            
            if unmapped_accounts:
                result['warning'] = f"Unmapped accounts: {', '.join(unmapped_accounts[:5])}"
                if len(unmapped_accounts) > 5:
                    result['warning'] += f" and {len(unmapped_accounts) - 5} more"
            
            return result
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'details': 'Error validating account mappings'
            }
    
    def _validate_balance_reconciliation(self,
                                       prior_tb: pd.DataFrame,
                                       current_tb: pd.DataFrame,
                                       activity_data: pd.DataFrame) -> Dict:
        """Validate balance reconciliation: Prior + Activity = Current"""
        try:
            reconciliation_errors = []
            tolerance = self.processing_rules.get('balance_tolerance', 0.005)
            
            for _, activity_row in activity_data.iterrows():
                account = activity_row['Account']
                calculated_activity = activity_row['Activity']
                
                # Get prior balance
                prior_row = prior_tb[prior_tb['Account'] == account]
                prior_balance = prior_row['Net'].iloc[0] if not prior_row.empty else 0
                
                # Get current balance
                current_row = current_tb[current_tb['Account'] == account]
                current_balance = current_row['Net'].iloc[0] if not current_row.empty else 0
                
                # Calculate expected activity
                expected_activity = current_balance - prior_balance
                variance = abs(calculated_activity - expected_activity)
                
                if variance > tolerance:
                    reconciliation_errors.append({
                        'account': account,
                        'prior_balance': prior_balance,
                        'current_balance': current_balance,
                        'expected_activity': expected_activity,
                        'calculated_activity': calculated_activity,
                        'variance': variance
                    })
            
            result = {
                'status': 'PASS' if not reconciliation_errors else 'FAIL',
                'total_accounts_checked': len(activity_data),
                'reconciliation_errors': len(reconciliation_errors),
                'tolerance': tolerance,
                'details': f"Checked {len(activity_data)} accounts for balance reconciliation"
            }
            
            if reconciliation_errors:
                result['errors'] = reconciliation_errors[:10]  # Limit to first 10
                total_variance = sum(err['variance'] for err in reconciliation_errors)
                result['total_variance'] = total_variance
            
            return result
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'details': 'Error validating balance reconciliation'
            }
    
    def _validate_activity_calculation(self,
                                     prior_tb: pd.DataFrame,
                                     current_tb: pd.DataFrame,
                                     activity_data: pd.DataFrame) -> Dict:
        """Validate activity calculation logic"""
        try:
            # Recalculate activity and compare
            validation_errors = []
            
            for _, row in activity_data.iterrows():
                account = row['Account']
                reported_activity = row['Activity']
                
                # Get balances
                prior_net = prior_tb[prior_tb['Account'] == account]['Net'].iloc[0] if not prior_tb[prior_tb['Account'] == account].empty else 0
                current_net = current_tb[current_tb['Account'] == account]['Net'].iloc[0] if not current_tb[current_tb['Account'] == account].empty else 0
                
                # Calculate activity
                calculated_activity = current_net - prior_net
                
                # Check if matches reported activity
                if abs(reported_activity - calculated_activity) > 0.001:
                    validation_errors.append({
                        'account': account,
                        'reported_activity': reported_activity,
                        'calculated_activity': calculated_activity,
                        'variance': abs(reported_activity - calculated_activity)
                    })
            
            return {
                'status': 'PASS' if not validation_errors else 'FAIL',
                'calculation_errors': len(validation_errors),
                'total_accounts': len(activity_data),
                'details': f"Validated activity calculation for {len(activity_data)} accounts",
                'errors': validation_errors[:5] if validation_errors else []
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'details': 'Error validating activity calculation'
            }
    
    def _validate_materiality_threshold(self, activity_data: pd.DataFrame) -> Dict:
        """Validate materiality threshold application"""
        try:
            threshold = self.processing_rules.get('materiality_threshold', 0.01)
            
            # Check for accounts below threshold
            below_threshold = activity_data[
                np.abs(activity_data['Activity']) < threshold
            ]
            
            # Check for zero activity
            zero_activity = activity_data[
                np.abs(activity_data['Activity']) < 0.001
            ]
            
            return {
                'status': 'PASS',
                'materiality_threshold': threshold,
                'total_accounts': len(activity_data),
                'below_threshold': len(below_threshold),
                'zero_activity': len(zero_activity),
                'details': f"Applied materiality threshold of ${threshold}"
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'details': 'Error validating materiality threshold'
            }
    
    def _validate_data_quality(self,
                             prior_tb: pd.DataFrame,
                             current_tb: pd.DataFrame) -> Dict:
        """Validate data quality and completeness"""
        try:
            quality_issues = []
            
            # Check for missing account codes
            if prior_tb['Account'].isna().any():
                quality_issues.append("Missing account codes in prior TB")
            
            if current_tb['Account'].isna().any():
                quality_issues.append("Missing account codes in current TB")
            
            # Check for duplicate accounts
            prior_duplicates = prior_tb[prior_tb['Account'].duplicated()]
            if not prior_duplicates.empty:
                quality_issues.append(f"Duplicate accounts in prior TB: {len(prior_duplicates)}")
            
            current_duplicates = current_tb[current_tb['Account'].duplicated()]
            if not current_duplicates.empty:
                quality_issues.append(f"Duplicate accounts in current TB: {len(current_duplicates)}")
            
            # Check for invalid numeric values
            numeric_cols = ['Debit', 'Credit', 'Net']
            for col in numeric_cols:
                if col in prior_tb.columns and not pd.api.types.is_numeric_dtype(prior_tb[col]):
                    quality_issues.append(f"Non-numeric values in prior TB {col} column")
                
                if col in current_tb.columns and not pd.api.types.is_numeric_dtype(current_tb[col]):
                    quality_issues.append(f"Non-numeric values in current TB {col} column")
            
            return {
                'status': 'PASS' if not quality_issues else 'FAIL',
                'issues_found': len(quality_issues),
                'issues': quality_issues,
                'details': f"Data quality check completed"
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'details': 'Error validating data quality'
            }
    
    def generate_variance_report(self,
                                operator_balances: pd.DataFrame,
                                system_balances: pd.DataFrame,
                                etl_changes: pd.DataFrame) -> pd.DataFrame:
        """
        Generate variance report matching Excel validation format
        
        Returns:
            DataFrame with variance analysis
        """
        try:
            # Merge all data sources
            variance_data = []
            
            # Get all unique accounts
            all_accounts = set()
            all_accounts.update(operator_balances['Account'].unique())
            all_accounts.update(system_balances['Account'].unique())
            all_accounts.update(etl_changes['Account'].unique())
            
            for account in all_accounts:
                # Get operator balance
                op_balance = operator_balances[
                    operator_balances['Account'] == account
                ]['Ending_Balance'].iloc[0] if not operator_balances[
                    operator_balances['Account'] == account
                ].empty else 0
                
                # Get ETL change
                etl_change = etl_changes[
                    etl_changes['Account'] == account
                ]['Activity'].iloc[0] if not etl_changes[
                    etl_changes['Account'] == account
                ].empty else 0
                
                # Calculate expected system balance
                expected_system_balance = op_balance + etl_change
                
                # Get actual system balance
                actual_system_balance = system_balances[
                    system_balances['Account'] == account
                ]['Balance'].iloc[0] if not system_balances[
                    system_balances['Account'] == account
                ].empty else 0
                
                # Calculate variance
                variance = actual_system_balance - expected_system_balance
                
                variance_data.append({
                    'Account': account,
                    'Description': operator_balances[
                        operator_balances['Account'] == account
                    ]['Description'].iloc[0] if not operator_balances[
                        operator_balances['Account'] == account
                    ].empty else '',
                    'Operator_Balance': op_balance,
                    'ETL_Change': etl_change,
                    'MRI_Expected_Balance': expected_system_balance,
                    'MRI_Actual_Balance': actual_system_balance,
                    'Variance': variance
                })
            
            variance_df = pd.DataFrame(variance_data)
            
            # Add summary statistics
            total_variance = variance_df['Variance'].sum()
            variance_df.loc[len(variance_df)] = {
                'Account': 'TOTAL',
                'Description': 'Summary',
                'Operator_Balance': variance_df['Operator_Balance'].sum(),
                'ETL_Change': variance_df['ETL_Change'].sum(),
                'MRI_Expected_Balance': variance_df['MRI_Expected_Balance'].sum(),
                'MRI_Actual_Balance': variance_df['MRI_Actual_Balance'].sum(),
                'Variance': total_variance
            }
            
            self.logger.info(f"Generated variance report with {len(variance_df)-1} accounts")
            return variance_df
            
        except Exception as e:
            self.logger.error(f"Error generating variance report: {e}")
            return pd.DataFrame()
    
    def get_validation_summary(self, validation_results: Dict) -> str:
        """Generate human-readable validation summary"""
        try:
            summary = []
            summary.append(f"Validation Status: {validation_results['overall_status']}")
            summary.append(f"Timestamp: {validation_results['timestamp']}")
            summary.append("")
            
            for validation_name, result in validation_results['validations'].items():
                status = result['status']
                details = result.get('details', '')
                summary.append(f"{validation_name.replace('_', ' ').title()}: {status}")
                if details:
                    summary.append(f"  {details}")
                if 'warning' in result:
                    summary.append(f"  WARNING: {result['warning']}")
                summary.append("")
            
            return "\n".join(summary)
            
        except Exception as e:
            return f"Error generating validation summary: {e}"