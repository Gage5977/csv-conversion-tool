#!/usr/bin/env python3
"""
Account Mapping Engine
Handles complex account transformations from Bitwise to MRI format
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple


class AccountMappingEngine:
    """
    Engine for transforming Bitwise account codes to MRI format
    Replicates Excel GL Mapping functionality
    """
    
    def __init__(self, config_dir: Path):
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self.gl_mapping = self._load_gl_mapping()
        self.mri_chart = self._load_mri_chart()
        self.transformation_rules = self.gl_mapping.get('transformation_rules', {})
        
    def _load_gl_mapping(self) -> Dict:
        """Load GL mapping configuration"""
        try:
            mapping_file = self.config_dir / 'gl_mapping.json'
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading GL mapping: {e}")
            return {}
    
    def _load_mri_chart(self) -> Dict:
        """Load MRI chart of accounts"""
        try:
            chart_file = self.config_dir / 'mri_chart_of_accounts.json'
            with open(chart_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading MRI chart: {e}")
            return {}
    
    def transform_account(self, source_account: str, description: str = "") -> Optional[str]:
        """
        Transform source account to MRI format
        
        Args:
            source_account: Bitwise account code (e.g., "10100-0-000: Cash - Checking")
            description: Account description for pattern matching
            
        Returns:
            MRI account code (e.g., "GM10100") or None if no mapping found
        """
        try:
            # Clean the source account
            cleaned_account = self._clean_account_code(source_account)
            
            # Direct mapping lookup
            account_mappings = self.gl_mapping.get('account_mappings', {})
            
            # Try exact match first
            if cleaned_account in account_mappings:
                return account_mappings[cleaned_account]['target_account']
            
            # Try original account string
            if source_account in account_mappings:
                return account_mappings[source_account]['target_account']
            
            # Try pattern matching
            pattern_match = self._match_by_pattern(source_account, description)
            if pattern_match:
                return pattern_match
            
            # Try transformation rules
            transformed = self._apply_transformation_rules(source_account)
            if transformed:
                return transformed
            
            self.logger.warning(f"No mapping found for account: {source_account}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error transforming account {source_account}: {e}")
            return None
    
    def _clean_account_code(self, account: str) -> str:
        """Clean account code by removing common patterns"""
        # Remove description part after colon
        if ':' in account:
            account = account.split(':')[0].strip()
        
        # Apply removal patterns
        remove_patterns = self.transformation_rules.get('remove_patterns', [])
        for pattern in remove_patterns:
            account = re.sub(pattern, '', account)
        
        return account.strip()
    
    def _match_by_pattern(self, source_account: str, description: str) -> Optional[str]:
        """Match account using regex patterns"""
        mapping_patterns = self.gl_mapping.get('mapping_patterns', {})
        
        for pattern_name, pattern_config in mapping_patterns.items():
            pattern = pattern_config.get('source_pattern', '')
            if re.search(pattern, source_account, re.IGNORECASE) or \
               re.search(pattern, description, re.IGNORECASE):
                return pattern_config.get('target_account')
        
        return None
    
    def _apply_transformation_rules(self, source_account: str) -> Optional[str]:
        """Apply automatic transformation rules"""
        try:
            # Extract numeric part
            numeric_match = re.search(r'(\d+)', source_account)
            if not numeric_match:
                return None
            
            numeric_part = numeric_match.group(1)
            
            # Apply prefix rules
            prefix_rules = self.transformation_rules.get('prefix_rules', {})
            default_prefix = prefix_rules.get('default_prefix', 'GM')
            
            # Construct target account
            target_account = f"{default_prefix}{numeric_part}"
            
            # Validate against MRI chart
            if self._validate_target_account(target_account):
                return target_account
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error applying transformation rules: {e}")
            return None
    
    def _validate_target_account(self, target_account: str) -> bool:
        """Validate target account exists in MRI chart"""
        mri_accounts = self.mri_chart.get('accounts', {})
        return target_account in mri_accounts
    
    def get_account_description(self, mri_account: str) -> str:
        """Get description for MRI account"""
        mri_accounts = self.mri_chart.get('accounts', {})
        account_info = mri_accounts.get(mri_account, {})
        return account_info.get('description', 'Unknown Account')
    
    def get_account_type(self, mri_account: str) -> str:
        """Get account type for MRI account"""
        mri_accounts = self.mri_chart.get('accounts', {})
        account_info = mri_accounts.get(mri_account, {})
        return account_info.get('type', 'Unknown')
    
    def validate_all_mappings(self, source_accounts: List[str]) -> Dict:
        """
        Validate all source accounts have mappings
        
        Returns:
            Dict with mapped and unmapped accounts
        """
        mapped = []
        unmapped = []
        
        for account in source_accounts:
            target = self.transform_account(account)
            if target:
                mapped.append({
                    'source': account,
                    'target': target,
                    'description': self.get_account_description(target)
                })
            else:
                unmapped.append(account)
        
        return {
            'mapped': mapped,
            'unmapped': unmapped,
            'mapping_rate': len(mapped) / len(source_accounts) if source_accounts else 0
        }
    
    def get_consolidation_rules(self) -> Dict:
        """Get account consolidation rules"""
        return self.transformation_rules.get('consolidation_rules', {})
    
    def apply_consolidation(self, source_account: str) -> str:
        """Apply consolidation rules for special accounts"""
        consolidation_rules = self.get_consolidation_rules()
        
        for source_pattern, target_account in consolidation_rules.items():
            if source_pattern in source_account or \
               re.search(source_pattern, source_account, re.IGNORECASE):
                return target_account
        
        # No consolidation rule found, return normal mapping
        return self.transform_account(source_account) or source_account