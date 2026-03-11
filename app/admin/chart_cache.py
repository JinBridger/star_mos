import os
import json
import hashlib
from flask import current_app
from app.main.utils import get_available_experiments, load_questions, load_metric_definitions
from app.admin.analysis_tools import generate_score_distribution_plot, get_experiment_statistics


def get_chart_cache_path():
    """Get chart cache directory path"""
    return os.path.join('app', 'static', 'cache', 'charts')


def get_chart_cache_key(experiment_name, metric, task_type=None):
    """Generate cache key for chart"""
    key_string = f"{experiment_name}_{metric}"
    if task_type:
        key_string += f"_{task_type}"
    return hashlib.md5(key_string.encode()).hexdigest()


def save_chart_to_cache(experiment_name, metric, chart_data, task_type=None):
    """Save chart data to cache"""
    cache_dir = get_chart_cache_path()
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_key = get_chart_cache_key(experiment_name, metric, task_type)
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    
    cache_data = {
        'experiment_name': experiment_name,
        'metric': metric,
        'task_type': task_type,
        'chart_data': chart_data
    }
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
        return True
    except Exception as e:
        print(f"Error saving chart cache: {e}")
        return False


def load_chart_from_cache(experiment_name, metric, task_type=None):
    """Load chart data from cache"""
    cache_dir = get_chart_cache_path()
    cache_key = get_chart_cache_key(experiment_name, metric, task_type)
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        return cache_data.get('chart_data')
    except Exception as e:
        print(f"Error loading chart cache: {e}")
        return None


def clear_chart_cache():
    """Clear all chart cache"""
    cache_dir = get_chart_cache_path()
    if os.path.exists(cache_dir):
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(cache_dir, filename))


def pregenerate_all_charts():
    """
    Pre-generate all charts for all experiments (grouped by task_type)
    
    Returns:
        tuple: (success, total_charts, generated_charts, errors)
    """
    print("Starting chart pre-generation...")
    
    experiments = get_available_experiments()
    total_charts = 0
    generated_charts = 0
    errors = []
    
    for experiment_name in experiments:
        print(f"Processing charts for experiment: {experiment_name}")
        
        # Get experiment statistics to find all metrics and task types
        stats = get_experiment_statistics(experiment_name)
        
        if not stats.get('task_type_stats'):
            print(f"No task type stats found for experiment: {experiment_name}")
            continue
        
        # Generate charts for each task type and metric combination
        for task_type, task_stats in stats['task_type_stats'].items():
            if not task_stats.get('metrics_stats'):
                continue
                
            for metric in task_stats['metrics_stats'].keys():
                total_charts += 1
                print(f"Generating chart for {experiment_name} - {task_type} - {metric}")
                
                try:
                    # Check if already cached
                    cached_chart = load_chart_from_cache(experiment_name, metric, task_type)
                    if cached_chart:
                        print(f"Chart already cached for {experiment_name} - {task_type} - {metric}")
                        generated_charts += 1
                        continue
                    
                    # Generate new chart
                    chart_data = generate_score_distribution_plot(experiment_name, metric, task_type)
                    
                    if chart_data:
                        # Save to cache
                        if save_chart_to_cache(experiment_name, metric, chart_data, task_type):
                            print(f"Chart generated and cached for {experiment_name} - {task_type} - {metric}")
                            generated_charts += 1
                        else:
                            error_msg = f"Failed to cache chart for {experiment_name} - {task_type} - {metric}"
                            print(error_msg)
                            errors.append(error_msg)
                    else:
                        error_msg = f"Failed to generate chart for {experiment_name} - {task_type} - {metric}"
                        print(error_msg)
                        errors.append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Error processing {experiment_name} - {task_type} - {metric}: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
    
    success = len(errors) == 0
    print(f"Chart pre-generation completed:")
    print(f"  - Total charts: {total_charts}")
    print(f"  - Generated/Cached: {generated_charts}")
    print(f"  - Errors: {len(errors)}")
    
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    
    return success, total_charts, generated_charts, errors


def get_chart_generation_progress():
    """
    Get current chart generation progress (for task_type grouped charts)
    
    Returns:
        dict: Progress information
    """
    experiments = get_available_experiments()
    total_charts = 0
    cached_charts = 0
    
    for experiment_name in experiments:
        stats = get_experiment_statistics(experiment_name)
        
        if stats.get('task_type_stats'):
            for task_type, task_stats in stats['task_type_stats'].items():
                if task_stats.get('metrics_stats'):
                    for metric in task_stats['metrics_stats'].keys():
                        total_charts += 1
                        
                        if load_chart_from_cache(experiment_name, metric, task_type):
                            cached_charts += 1
    
    progress = (cached_charts / total_charts * 100) if total_charts > 0 else 100
    
    return {
        'total_charts': total_charts,
        'cached_charts': cached_charts,
        'progress': progress,
        'completed': cached_charts == total_charts
    }