import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'zeyuxie'
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Experiment verification codes
    EXPERIMENT_CODES = {
        'star': 'star2025'
    }
    
    # Admin verification code
    ADMIN_VERIFICATION_CODE = 'zeyuxie'
    
    # File paths
    EXPERIMENTS_DIR = 'experiments'
    
    # Upload configuration
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size