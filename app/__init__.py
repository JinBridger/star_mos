from flask import Flask
import os
import sys
import logging

# Add the project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_app():
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app.logger.setLevel(logging.INFO)
    
    # Load configuration
    try:
        from config import Config
        app.config.from_object(Config)
    except ImportError:
        # Fallback configuration if config.py is not found
        app.config['SECRET_KEY'] = 'dev-secret-key'
        app.config['EXPERIMENTS_DIR'] = 'experiments'
        app.config['EXPERIMENT_CODES'] = {
            'tts_experiment_1': 'tts2024',
            'ttm_experiment_2': 'ttm2024'
        }
        app.config['ADMIN_VERIFICATION_CODE'] = 'admin2024'
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Pre-generate mel spectrograms and composite videos at startup
    with app.app_context():
        from app.main.audio_utils import pregenerate_all_mel_spectrograms
        from app.main.video_utils import pregenerate_all_composite_videos
        
        print("Initializing mel spectrogram cache...")
        success, results = pregenerate_all_mel_spectrograms()
        
        if not success:
            print("ERROR: Failed to generate all required mel spectrograms!")
            print("Please check audio files and try again.")
            # You could choose to exit here if you want to enforce all spectrograms exist
            # import sys
            # sys.exit(1)
        else:
            print("All mel spectrograms ready!")
        
        print("Initializing composite video cache...")
        video_success, video_results = pregenerate_all_composite_videos()
        
        if not video_success:
            print("ERROR: Failed to generate all required composite videos!")
            print("Please check video and audio files and ffmpeg installation.")
            print(f"Video generation results: {video_results}")
            # You could choose to exit here if you want to enforce all videos exist
            # import sys
            # sys.exit(1)
        else:
            print(f"All composite videos ready! Generated {video_results['generated_videos']} videos.")
    
    return app