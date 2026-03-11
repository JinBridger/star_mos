import os
import subprocess
import hashlib
import librosa
from flask import current_app


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting video duration for {video_path}: {e}")
        return None


def get_audio_duration(audio_path):
    """Get audio duration in seconds using librosa"""
    try:
        y, sr = librosa.load(audio_path, sr=None)
        return len(y) / sr
    except Exception as e:
        print(f"Error getting audio duration for {audio_path}: {e}")
        return None


def generate_composite_video(video_path, audio_path, output_path):
    """
    Generate a composite video by replacing the original audio with new audio.
    Audio alignment: start from 0, truncate if too long, pad with silence if too short.
    
    Args:
        video_path: Path to the original video file
        audio_path: Path to the replacement audio file
        output_path: Path for the output composite video
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get video duration
        video_duration = get_video_duration(video_path)
        if video_duration is None:
            return False
        
        # Get audio duration
        audio_duration = get_audio_duration(audio_path)
        if audio_duration is None:
            return False
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Use ffmpeg to combine video and audio
        # If audio is longer than video, it will be truncated
        # If audio is shorter than video, it will be padded with silence
        cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-i', video_path,  # Input video
            '-i', audio_path,  # Input audio
            '-c:v', 'copy',  # Copy video stream without re-encoding
            '-c:a', 'aac',  # Encode audio as AAC
            '-map', '0:v:0',  # Map video from first input
            '-map', '1:a:0',  # Map audio from second input
            '-shortest',  # End when shortest stream ends
            '-avoid_negative_ts', 'make_zero',  # Avoid negative timestamps
            output_path
        ]
        
        # If audio is shorter than video, we need to pad it
        if audio_duration < video_duration:
            # Use filter to pad audio with silence
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-filter_complex', f'[1:a]apad=whole_dur={video_duration}[audio]',
                '-map', '0:v:0',
                '-map', '[audio]',
                '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                output_path
            ]
        
        # Run ffmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Check if output file was created
        if os.path.exists(output_path):
            print(f"Successfully generated composite video: {output_path}")
            return True
        else:
            print(f"Failed to generate composite video: {output_path}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error generating composite video: {e}")
        return False


def get_video_cache_path(video_path, audio_path):
    """
    Generate cache path for composite video based on video and audio paths.
    
    Args:
        video_path: Original video path
        audio_path: Replacement audio path
    
    Returns:
        str: Cache file path
    """
    # Create a hash from both paths to generate unique filename
    combined_path = f"{video_path}+{audio_path}"
    hash_obj = hashlib.md5(combined_path.encode())
    cache_filename = hash_obj.hexdigest() + '.mp4'
    
    # Return full cache path (relative to Flask app static directory)
    cache_dir = os.path.join('app', 'static', 'cache', 'videos')
    return os.path.join(cache_dir, cache_filename)


def get_cached_composite_video(video_path, audio_path):
    """
    Get cached composite video or generate if not exists.
    
    Args:
        video_path: Original video path (relative to app root)
        audio_path: Replacement audio path (relative to app root)
    
    Returns:
        str: Relative path to cached video, or None if failed
    """
    try:
        # Convert relative paths to absolute paths
        if video_path.startswith('/static/'):
            video_abs_path = os.path.join('app', video_path[1:])  # Remove leading '/'
        else:
            video_abs_path = video_path
            
        if audio_path.startswith('/static/'):
            audio_abs_path = os.path.join('app', audio_path[1:])  # Remove leading '/'
        else:
            audio_abs_path = audio_path
        
        # Get cache path
        cache_path = get_video_cache_path(video_path, audio_path)
        cache_abs_path = cache_path
        
        # Check if cached video exists
        if os.path.exists(cache_abs_path):
            # Return relative path for web access (remove app/ prefix)
            web_path = cache_path.replace('app/', '/')
            return web_path.replace(os.sep, '/')
        
        # Generate composite video if not cached
        print(f"Generating composite video: {video_path} + {audio_path}")
        success = generate_composite_video(video_abs_path, audio_abs_path, cache_abs_path)
        
        if success:
            # Return relative path for web access (remove app/ prefix)
            web_path = cache_path.replace('app/', '/')
            return web_path.replace(os.sep, '/')
        else:
            return None
            
    except Exception as e:
        print(f"Error getting cached composite video: {e}")
        return None


def pregenerate_all_composite_videos():
    """
    Pre-generate all composite videos for V2A tasks at startup.
    
    Returns:
        tuple: (success, results_dict)
        - success: bool indicating if all videos were processed
        - results_dict: dict with details about generation process
    """
    from app.main.utils import get_available_experiments, load_questions
    
    results = {
        'total_videos': 0,
        'generated_videos': 0,
        'cached_videos': 0,
        'failed_videos': 0,
        'errors': []
    }
    
    try:
        experiments = get_available_experiments()
        
        for experiment_name in experiments:
            questions = load_questions(experiment_name)
            if not questions:
                continue
                
            for question in questions:
                # Only process V2A tasks
                if question.get('task_type') != 'v2a':
                    continue
                
                video_path = question.get('prompt')  # Video file path
                
                if not video_path:
                    results['errors'].append(f"Missing video path in question {question.get('sample_id', 'unknown')}")
                    results['failed_videos'] += 1
                    continue
                
                # Handle multi-system structure
                systems = question.get('systems', [])
                if not systems:
                    results['errors'].append(f"No systems found in question {question.get('sample_id', 'unknown')}")
                    results['failed_videos'] += 1
                    continue
                
                # Process each system's audio
                for system in systems:
                    audio_path = system.get('audio_path')
                    
                    if not audio_path:
                        results['errors'].append(f"Missing audio path for system {system.get('system_id', 'unknown')} in question {question.get('sample_id', 'unknown')}")
                        results['failed_videos'] += 1
                        continue
                    
                    results['total_videos'] += 1
                    
                    # Try to get cached composite video
                    composite_video_path = get_cached_composite_video(video_path, audio_path)
                    
                    if composite_video_path:
                        results['generated_videos'] += 1
                        print(f"Composite video ready: {composite_video_path}")
                    else:
                        results['failed_videos'] += 1
                        results['errors'].append(f"Failed to generate composite video for {video_path} + {audio_path}")
        
        success = results['failed_videos'] == 0
        return success, results
        
    except Exception as e:
        results['errors'].append(f"Error in pregenerate_all_composite_videos: {e}")
        return False, results