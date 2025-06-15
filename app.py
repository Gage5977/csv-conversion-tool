#!/usr/bin/env python3
"""
Enhanced MRI Trial Balance Import System
Flask API implementing Excel Trial Balance Conversion Tool functionality
"""

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import tempfile
import logging
import json
import uuid
from datetime import datetime

# Import the processor - handle import path issues
import sys
sys.path.append(str(Path(__file__).parent))

# Import the working processor
from simple_processor import SimpleTrialBalanceProcessor as EnhancedTrialBalanceProcessor

app = Flask(__name__)
CORS(app)

# Ensure logs directory exists
logs_dir = Path(__file__).parent / 'logs'
logs_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'mri_import_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure paths
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / 'temp'
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Configure maximum file size (50MB)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_temp_files(*file_paths):
    """Clean up temporary files safely"""
    for file_path in file_paths:
        try:
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
        except Exception as e:
            logger.warning(f"Could not delete temp file {file_path}: {e}")

@app.errorhandler(413)
def file_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {error}", exc_info=True)
    return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/')
def index():
    """Main interface"""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'MRI Trial Balance Import System',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/process', methods=['POST'])
def process_trial_balances():
    """Process trial balances and generate MRI import file"""
    prior_path = None
    current_path = None
    
    try:
        # Validate request
        if 'prior_tb' not in request.files or 'current_tb' not in request.files:
            return jsonify({'error': 'Both prior and current trial balance files are required'}), 400
        
        # Get additional parameters
        period = request.form.get('period', '')
        entity_id = request.form.get('entity_id', '')
        
        if not period:
            return jsonify({'error': 'Period is required (format: MM/YY)'}), 400
        
        prior_file = request.files['prior_tb']
        current_file = request.files['current_tb']
        
        # Validate files
        for file, name in [(prior_file, 'prior'), (current_file, 'current')]:
            if file.filename == '':
                return jsonify({'error': f'No {name} period file selected'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': f'Invalid file type for {name} period. Please upload CSV or Excel file.'}), 400
        
        # Save files temporarily
        session_id = str(uuid.uuid4())[:8]
        
        prior_filename = f"prior_tb_{session_id}_{secure_filename(prior_file.filename)}"
        current_filename = f"current_tb_{session_id}_{secure_filename(current_file.filename)}"
        
        prior_path = UPLOAD_FOLDER / prior_filename
        current_path = UPLOAD_FOLDER / current_filename
        
        prior_file.save(prior_path)
        current_file.save(current_path)
        
        logger.info(f"Processing session {session_id}: {prior_filename}, {current_filename}")
        
        # Initialize processor
        processor = EnhancedTrialBalanceProcessor()
        
        # Load trial balances
        if not processor.load_trial_balances(prior_path, current_path):
            cleanup_temp_files(prior_path, current_path)
            return jsonify({'error': 'Failed to load trial balance data. Please check file format and content.'}), 400
        
        # Calculate activity with mapping
        if not processor.calculate_activity_with_mapping():
            cleanup_temp_files(prior_path, current_path)
            return jsonify({'error': 'Failed to calculate account activity. Please verify account mappings.'}), 400
        
        # Generate MRI import file
        if not processor.generate_mri_import_file(period, entity_id):
            cleanup_temp_files(prior_path, current_path)
            return jsonify({'error': 'Failed to generate MRI import file.'}), 400
        
        # Run validation
        validation_passed = processor.run_comprehensive_validation()
        
        # Export MRI import file
        output_filename = f'mri_import_{session_id}.csv'
        output_path = UPLOAD_FOLDER / output_filename
        
        if not processor.export_mri_import_file(output_path, period, entity_id):
            cleanup_temp_files(prior_path, current_path)
            return jsonify({'error': 'Failed to export MRI import file.'}), 500
        
        # Get processing summary
        summary = processor.get_processing_summary()
        
        # Clean up input files
        cleanup_temp_files(prior_path, current_path)
        
        # Prepare response
        response_data = {
            'message': 'Processing completed successfully',
            'session_id': session_id,
            'period': period,
            'entity_id': entity_id,
            'validation_passed': validation_passed,
            'summary': summary,
            'validation_results': processor.validation_results,
            'download_url': f'/api/download/mri_import/{session_id}'
        }
        
        logger.info(f"Processing completed for session {session_id}")
        return jsonify(response_data)
        
    except Exception as e:
        cleanup_temp_files(prior_path, current_path)
        logger.error(f"Error processing trial balances: {e}", exc_info=True)
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/download/mri_import/<session_id>')
def download_mri_import(session_id):
    """Download generated MRI import CSV"""
    try:
        # Validate session_id
        if not session_id.isalnum() or len(session_id) != 8:
            return jsonify({'error': 'Invalid session ID'}), 400
        
        file_path = UPLOAD_FOLDER / f'mri_import_{session_id}.csv'

        if not file_path.exists():
            return jsonify({'error': 'MRI import file not found or expired'}), 404
        
        return send_file(
            file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'mri_import_{session_id}.csv'
        )
        
    except Exception as e:
        logger.error(f"Error downloading MRI import file: {e}")
        return jsonify({'error': 'Failed to download file'}), 500

@app.route('/api/validate', methods=['POST'])
def validate_file():
    """Validate uploaded file structure"""
    file_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload CSV or Excel file.'}), 400
        
        # Save temporarily
        temp_id = str(uuid.uuid4())[:8]
        temp_filename = f"temp_validate_{temp_id}_{secure_filename(file.filename)}"
        file_path = UPLOAD_FOLDER / temp_filename
        
        file.save(file_path)
        
        # Initialize processor for validation
        processor = EnhancedTrialBalanceProcessor(BASE_DIR)
        
        # Try to load the file
        result = processor._load_trial_balance_file(file_path, "Validation")
        
        cleanup_temp_files(file_path)
        
        if result is not None:
            return jsonify({
                'message': 'File structure is valid',
                'details': {
                    'accounts_found': len(result),
                    'columns_found': list(result.columns),
                    'format': 'Valid trial balance format'
                }
            })
        else:
            return jsonify({'error': 'Invalid file structure. Please check format and content.'}), 400
        
    except Exception as e:
        cleanup_temp_files(file_path)
        logger.error(f"Error validating file: {e}")
        return jsonify({'error': 'File validation failed. Please check file format.'}), 400

@app.route('/api/mappings', methods=['GET'])
def get_account_mappings():
    """Get current account mappings"""
    try:
        processor = EnhancedTrialBalanceProcessor()
        
        # Return the simple processor's built-in mappings
        return jsonify({
            'mappings': processor.account_mappings,
            'mapping_info': {
                'description': 'Built-in account mappings',
                'total_mappings': len(processor.account_mappings)
            },
            'transformation_rules': {
                'remove_patterns': ['-0-000', ': .*'],
                'prefix_rules': {'default_prefix': 'GM'}
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting account mappings: {e}")
        return jsonify({'error': 'Failed to load account mappings'}), 500

@app.route('/api/config', methods=['GET'])
def get_system_config():
    """Get system configuration"""
    try:
        # Return basic config since we're using simple processor
        config_data = {
            'system_info': {
                'name': 'MRI Trial Balance Import System',
                'version': '1.0.0'
            },
            'entity_config': {
                'default_entity_id': 'M55020',
                'default_department': '@'
            },
            'processing_rules': {
                'materiality_threshold': 0.01
            }
        }
        
        return jsonify(config_data)
        
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        return jsonify({'error': 'Failed to load system configuration'}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_files():
    """Clean up old temporary files"""
    try:
        import time
        current_time = time.time()
        cleanup_count = 0
        
        # Remove files older than 1 hour
        for file_path in UPLOAD_FOLDER.glob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > 3600:  # 1 hour
                    try:
                        file_path.unlink()
                        cleanup_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete old file {file_path}: {e}")
        
        return jsonify({
            'message': 'Cleanup completed',
            'files_removed': cleanup_count
        })
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500

def main():
    """Main execution function"""
    # Ensure required directories exist
    (BASE_DIR / 'logs').mkdir(exist_ok=True)
    (BASE_DIR / 'temp').mkdir(exist_ok=True)
    
    logger.info("Starting MRI Trial Balance Import System")
    logger.info(f"Base directory: {BASE_DIR}")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()