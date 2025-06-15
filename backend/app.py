#!/usr/bin/env python3
"""
Flask API for Trial Balance Processing
Provides endpoints for the ETL interface
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import tempfile
from trial_balance_processor import TrialBalanceProcessor

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure upload folder
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / 'trial_balance_uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/process', methods=['POST'])
def process_trial_balances():
    """Process uploaded trial balance files"""
    try:
        # Check if files were uploaded
        if 'prior_tb' not in request.files or 'current_tb' not in request.files:
            return jsonify({'error': 'Both prior and current trial balance files required'}), 400
            
        prior_file = request.files['prior_tb']
        current_file = request.files['current_tb']
        
        # Validate files
        for file in [prior_file, current_file]:
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type'}), 400
        
        # Save files temporarily
        prior_path = UPLOAD_FOLDER / secure_filename(prior_file.filename)
        current_path = UPLOAD_FOLDER / secure_filename(current_file.filename)
        
        prior_file.save(prior_path)
        current_file.save(current_path)
        
        # Process trial balances
        processor = TrialBalanceProcessor()
        
        # Load and validate data
        if not processor.load_trial_balances(prior_path, current_path):
            return jsonify({'error': 'Error loading trial balance data'}), 400
            
        # Calculate activity
        if not processor.calculate_activity():
            return jsonify({'error': 'Error calculating activity'}), 400
            
        # Generate journal entries
        if not processor.generate_journal_entries():
            return jsonify({'error': 'Error generating journal entries'}), 400
            
        # Export results
        output_path = UPLOAD_FOLDER / 'journal_entries.csv'
        processor.export_journal_entries(output_path)
        
        # Get summary statistics
        stats = processor.get_summary_stats()
        
        # Clean up temporary files
        prior_path.unlink()
        current_path.unlink()
        
        return jsonify({
            'message': 'Processing complete',
            'stats': stats,
            'journal_entries_url': '/api/download/journal_entries'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/journal_entries')
def download_journal_entries():
    """Download generated journal entries CSV"""
    try:
        file_path = UPLOAD_FOLDER / 'journal_entries.csv'
        if not file_path.exists():
            return jsonify({'error': 'Journal entries file not found'}), 404
            
        return send_file(
            file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name='journal_entries.csv'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def validate_file():
    """Validate uploaded CSV file structure"""
    try:
        print("11111ZPOOOOOOOOOOOOPPPPPP")

        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
            
        # Save and validate file
        file_path = UPLOAD_FOLDER / secure_filename(file.filename)
        file.save(file_path)
        
        processor = TrialBalanceProcessor()
        validation_result = processor.load_trial_balances(file_path, file_path)  # Use same file twice just for validation
        
        print("ZPOOOOOOOOOOOOPPPPPP")
        print(validation_result)
        # Clean up
        file_path.unlink()
        
        if validation_result:
            return jsonify({'message': 'File structure valid'})
        else:
            return jsonify({'error': 'Invalid file structure'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def main():
    """Main execution function"""
    # Ensure upload directory exists
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main() 