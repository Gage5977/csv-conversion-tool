#!/usr/bin/env python3
"""
Trial Balance Processor
Handles ETL processing of trial balance data and generates journal entries
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import logging

class TrialBalanceProcessor:
    def __init__(self, config_path=None):
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path) if config_path else {}
        self.prior_tb = None
        self.current_tb = None
        self.activity = None
        self.journal_entries = None
        
    def _setup_logging(self):
        """Configure logging"""
        logger = logging.getLogger('TrialBalanceProcessor')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def _load_config(self, config_path):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
            
    def load_trial_balances(self, prior_path, current_path):
        """Load prior and current trial balance CSV files"""
        try:
            # Load CSVs with standard accounting columns
            self.prior_tb = pd.read_csv(prior_path)
            self.current_tb = pd.read_csv(current_path)
            
            # Validate required columns
            required_cols = ['Account_Code', 'Account_Name', 'Debit', 'Credit']
            for df in [self.prior_tb, self.current_tb]:
                missing = [col for col in required_cols if col not in df.columns]
                if missing:
                    raise ValueError(f"Missing required columns: {missing}")
            
            # Clean and standardize data
            for df in [self.prior_tb, self.current_tb]:
                df['Debit'] = pd.to_numeric(df['Debit'].fillna(0))
                df['Credit'] = pd.to_numeric(df['Credit'].fillna(0))
                df['Net'] = df['Debit'] - df['Credit']
            
            self.logger.info("Trial balance data loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading trial balances: {e}")
            return False
    
    def calculate_activity(self):
        """Calculate period-over-period activity"""
        try:
            if self.prior_tb is None or self.current_tb is None:
                raise ValueError("Trial balance data not loaded")
            
            print("prior_tb", self.prior_tb)
            print("current_tb", self.current_tb)
            
            # Merge prior and current on account
            merged = pd.merge(
                self.prior_tb[['Account_Code', 'Net']].rename(columns={'Net': 'Prior_Net'}),
                self.current_tb[['Account_Code', 'Net']].rename(columns={'Net': 'Current_Net'}),
                on='Account',
                how='outer'
            ).fillna(0)

            print("merged", merged)
            
            # Calculate activity
            merged['Activity'] = merged['Current_Net'] - merged['Prior_Net']
            
            print("merged", merged['Activity'])

            # Split into debits and credits
            self.activity = merged.copy()
            self.activity['Debit'] = np.where(merged['Activity'] > 0, merged['Activity'], 0)
            self.activity['Credit'] = np.where(merged['Activity'] < 0, -merged['Activity'], 0)

            print("activity", activity)
            
            self.logger.info("Activity calculated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error calculating activity: {e}")
            return False
    
    def generate_journal_entries(self):
        """Generate journal entries from activity"""
        try:
            if self.activity is None:
                raise ValueError("Activity not calculated")
            
            # Filter for accounts with activity
            active = self.activity[
                (self.activity['Debit'] != 0) | 
                (self.activity['Credit'] != 0)
            ].copy()
            
            # Create journal entry dataframe
            je_data = []
            entry_number = 1
            
            # Group by debit/credit to create balanced entries
            debit_accounts = active[active['Debit'] > 0]
            credit_accounts = active[active['Credit'] > 0]
            
            # Add entry lines
            for _, row in debit_accounts.iterrows():
                je_data.append({
                    'Entry': entry_number,
                    'Account': row['Account'],
                    'Debit': row['Debit'],
                    'Credit': 0
                })
                
            for _, row in credit_accounts.iterrows():
                je_data.append({
                    'Entry': entry_number,
                    'Account': row['Account'],
                    'Debit': 0,
                    'Credit': row['Credit']
                })
            
            self.journal_entries = pd.DataFrame(je_data)
            
            # Validate entries are balanced
            entry_totals = self.journal_entries.groupby('Entry').agg({
                'Debit': 'sum',
                'Credit': 'sum'
            })
            
            if not np.allclose(entry_totals['Debit'], entry_totals['Credit']):
                self.logger.warning("Journal entries not balanced")
            
            self.logger.info("Journal entries generated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating journal entries: {e}")
            return False
    
    def export_journal_entries(self, output_path):
        """Export journal entries to CSV"""
        try:
            if self.journal_entries is None:
                raise ValueError("No journal entries to export")
                
            # Add metadata
            self.journal_entries['Date'] = datetime.now().strftime('%Y-%m-%d')
            self.journal_entries['Description'] = 'Period Activity'
            
            # Export to CSV
            self.journal_entries.to_csv(output_path, index=False)
            self.logger.info(f"Journal entries exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting journal entries: {e}")
            return False
            
    def get_summary_stats(self):
        """Get summary statistics of the processed data"""
        try:
            if self.journal_entries is None:
                raise ValueError("No journal entries available")
                
            stats = {
                'total_entries': len(self.journal_entries['Entry'].unique()),
                'total_debit': self.journal_entries['Debit'].sum(),
                'total_credit': self.journal_entries['Credit'].sum(),
                'total_accounts': len(self.journal_entries['Account'].unique()),
                'timestamp': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting summary stats: {e}")
            return None

def main():
    """Main execution function"""
    processor = TrialBalanceProcessor()
    
    # Example usage
    success = processor.load_trial_balances(
        'prior_trial_balance.csv',
        'current_trial_balance.csv'
    )
    
    if success:
        processor.calculate_activity()
        processor.generate_journal_entries()
        processor.export_journal_entries('journal_entries.csv')
        print(processor.get_summary_stats())

if __name__ == '__main__':
    main() 