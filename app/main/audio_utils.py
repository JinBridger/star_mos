import os
import librosa
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
from io import BytesIO
import base64
import hashlib

def generate_mel_spectrogram(audio_path, cache_dir='app/static/cache/mel'):
    """
    Generate mel spectrogram for audio file and return base64 encoded image
    
    Args:
        audio_path: Path to audio file (can be web path like /static/... or absolute path)
        cache_dir: Directory to cache generated spectrograms
        
    Returns:
        base64 encoded PNG image string
    """
    # Convert web path to filesystem path
    actual_path = convert_web_path_to_filesystem(audio_path)
    
    if not os.path.exists(actual_path):
        print(f"Audio file not found: {actual_path}")
        return None
    
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Generate cache filename based on audio file hash
    audio_hash = get_file_hash(actual_path)
    cache_filename = f"{audio_hash}.png"
    cache_path = os.path.join(cache_dir, cache_filename)
    
    # Check if cached version exists
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            img_data = f.read()
        return base64.b64encode(img_data).decode('utf-8')
    
    try:
        # Load audio file
        y, sr = librosa.load(actual_path, sr=None)
        
        # Generate mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y, 
            sr=sr, 
            n_mels=128, 
            fmax=8000,
            hop_length=512,
            n_fft=2048
        )
        
        # Convert to dB scale
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # Create figure
        plt.figure(figsize=(10, 4))
        plt.subplot(1, 1, 1)
        
        # Plot mel spectrogram
        librosa.display.specshow(
            mel_spec_db, 
            sr=sr, 
            hop_length=512,
            x_axis='time', 
            y_axis='mel',
            fmax=8000,
            cmap='viridis'
        )
        
        plt.colorbar(format='%+2.0f dB')
        plt.title('Mel Spectrogram')
        plt.tight_layout()
        
        # Save to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        
        # Save to cache
        with open(cache_path, 'wb') as f:
            f.write(img_buffer.getvalue())
        
        # Convert to base64
        img_data = img_buffer.getvalue()
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        plt.close()  # Close figure to free memory
        
        return img_base64
        
    except Exception as e:
        print(f"Error generating mel spectrogram for {actual_path}: {e}")
        return None

def convert_web_path_to_filesystem(web_path):
    """
    Convert web path (like /static/audio/samples/file.wav) to filesystem path
    
    Args:
        web_path: Web path starting with /static/ or absolute filesystem path
        
    Returns:
        Absolute filesystem path
    """
    if web_path.startswith('/static/'):
        # Remove leading /static/ and prepend with actual static directory
        relative_path = web_path[8:]  # Remove '/static/'
        return os.path.join('app', 'static', relative_path)
    else:
        # Assume it's already a filesystem path
        return web_path

def get_file_hash(file_path):
    """Generate MD5 hash of file for caching"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        # Also include file modification time in hash
        mtime = str(os.path.getmtime(file_path))
        hash_md5.update(mtime.encode())
        return hash_md5.hexdigest()
    except:
        return hashlib.md5(file_path.encode()).hexdigest()

def clear_mel_cache(cache_dir='app/static/cache/mel'):
    """Clear mel spectrogram cache directory"""
    if os.path.exists(cache_dir):
        for filename in os.listdir(cache_dir):
            if filename.endswith('.png'):
                os.remove(os.path.join(cache_dir, filename))

def pregenerate_all_mel_spectrograms():
    """
    Pre-generate all mel spectrograms for all experiments at startup
    
    Returns:
        dict: Status of generation for each audio file
    """
    from app.main.utils import get_available_experiments, load_questions
    
    print("Starting mel spectrogram pre-generation...")
    results = {}
    total_generated = 0
    total_cached = 0
    total_failed = 0
    
    experiments = get_available_experiments()
    
    for experiment_name in experiments:
        print(f"Processing experiment: {experiment_name}")
        questions = load_questions(experiment_name)
        
        if not questions:
            print(f"No questions found for experiment: {experiment_name}")
            continue
            
        for i, question in enumerate(questions):
            question_id = question.get('question_id', f'question_{i}')
            
            # Process GT audio mel spectrogram
            if question.get('show_gt_audio_mel') and question.get('gt_audio_path'):
                gt_path = question['gt_audio_path']
                print(f"Generating GT mel for {question_id}: {gt_path}")
                
                # Check if already cached
                actual_path = convert_web_path_to_filesystem(gt_path)
                if os.path.exists(actual_path):
                    audio_hash = get_file_hash(actual_path)
                    cache_path = os.path.join('app/static/cache/mel', f"{audio_hash}.png")
                    
                    if os.path.exists(cache_path):
                        print(f"GT mel already cached for {question_id}")
                        total_cached += 1
                        results[f"{experiment_name}_{question_id}_gt"] = "cached"
                    else:
                        gt_mel = generate_mel_spectrogram(gt_path)
                        if gt_mel:
                            print(f"GT mel generated successfully for {question_id}")
                            total_generated += 1
                            results[f"{experiment_name}_{question_id}_gt"] = "generated"
                        else:
                            print(f"Failed to generate GT mel for {question_id}")
                            total_failed += 1
                            results[f"{experiment_name}_{question_id}_gt"] = "failed"
                else:
                    print(f"GT audio file not found: {actual_path}")
                    total_failed += 1
                    results[f"{experiment_name}_{question_id}_gt"] = "file_not_found"
            
            # Process Generated audio mel spectrogram
            if question.get('show_gen_audio_mel') and question.get('gen_audio_path'):
                gen_path = question['gen_audio_path']
                print(f"Generating Gen mel for {question_id}: {gen_path}")
                
                # Check if already cached
                actual_path = convert_web_path_to_filesystem(gen_path)
                if os.path.exists(actual_path):
                    audio_hash = get_file_hash(actual_path)
                    cache_path = os.path.join('app/static/cache/mel', f"{audio_hash}.png")
                    
                    if os.path.exists(cache_path):
                        print(f"Gen mel already cached for {question_id}")
                        total_cached += 1
                        results[f"{experiment_name}_{question_id}_gen"] = "cached"
                    else:
                        gen_mel = generate_mel_spectrogram(gen_path)
                        if gen_mel:
                            print(f"Gen mel generated successfully for {question_id}")
                            total_generated += 1
                            results[f"{experiment_name}_{question_id}_gen"] = "generated"
                        else:
                            print(f"Failed to generate Gen mel for {question_id}")
                            total_failed += 1
                            results[f"{experiment_name}_{question_id}_gen"] = "failed"
                else:
                    print(f"Gen audio file not found: {actual_path}")
                    total_failed += 1
                    results[f"{experiment_name}_{question_id}_gen"] = "file_not_found"
    
    print(f"Mel spectrogram pre-generation completed:")
    print(f"  - Generated: {total_generated}")
    print(f"  - Cached: {total_cached}")
    print(f"  - Failed: {total_failed}")
    
    if total_failed > 0:
        print("WARNING: Some mel spectrograms failed to generate!")
        failed_items = [k for k, v in results.items() if v in ['failed', 'file_not_found']]
        for item in failed_items:
            print(f"  - {item}: {results[item]}")
        
        # Don't start if there are failures
        return False, results
    
    return True, results

def get_cached_mel_spectrogram(audio_path, cache_dir='app/static/cache/mel'):
    """
    Get mel spectrogram from cache (assumes it was pre-generated)
    
    Args:
        audio_path: Path to audio file
        cache_dir: Directory where spectrograms are cached
        
    Returns:
        base64 encoded PNG image string or None
    """
    actual_path = convert_web_path_to_filesystem(audio_path)
    
    if not os.path.exists(actual_path):
        print(f"Audio file not found: {actual_path}")
        return None
    
    # Generate cache filename based on audio file hash
    audio_hash = get_file_hash(actual_path)
    cache_filename = f"{audio_hash}.png"
    cache_path = os.path.join(cache_dir, cache_filename)
    
    # Check if cached version exists
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                img_data = f.read()
            return base64.b64encode(img_data).decode('utf-8')
        except Exception as e:
            print(f"Error reading cached mel spectrogram: {e}")
            return None
    else:
        print(f"Cached mel spectrogram not found: {cache_path}")
        return None