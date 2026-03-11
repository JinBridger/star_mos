import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from flask import current_app
import base64
from io import BytesIO


def get_completed_users_for_experiment(experiment_name):
    """Get list of users who completed ALL questions in the experiment"""
    from app.main.utils import load_questions
    
    questions = load_questions(experiment_name)
    if not questions:
        return set()
    
    total_questions = len(questions)
    results_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'results')
    
    if not os.path.exists(results_dir):
        return set()
    
    completed_users = set()
    
    # Check each user file
    for filename in os.listdir(results_dir):
        if filename.startswith('user_') and filename.endswith('.jsonl'):
            file_path = os.path.join(results_dir, filename)
            try:
                user_responses = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            user_responses.append(data)
                
                # Check if user completed all questions
                if len(user_responses) >= total_questions:
                    # Extract user_id from first response
                    if user_responses:
                        user_id = user_responses[0].get('user_id')
                        if user_id:
                            completed_users.add(user_id)
                            
            except Exception as e:
                current_app.logger.error(f"Error checking completion for {filename}: {e}")
    
    return completed_users


def load_experiment_results(experiment_name, only_completed_users=True):
    """Load all results for an experiment into a pandas DataFrame"""
    results_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'results')
    
    if not os.path.exists(results_dir):
        return pd.DataFrame()
    
    # Get completed users if filtering is enabled
    completed_users = set()
    if only_completed_users:
        completed_users = get_completed_users_for_experiment(experiment_name)
        if not completed_users:
            return pd.DataFrame()
    
    all_data = []
    
    # Load all user result files
    for filename in os.listdir(results_dir):
        if filename.startswith('user_') and filename.endswith('.jsonl'):
            file_path = os.path.join(results_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            
                            # Filter by completed users if enabled
                            if only_completed_users:
                                user_id = data.get('user_id')
                                if user_id not in completed_users:
                                    continue
                            
                            all_data.append(data)
            except Exception as e:
                current_app.logger.error(f"Error loading {filename}: {e}")
    
    if not all_data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data)
    
    # Expand scores column into separate columns
    if 'scores' in df.columns:
        scores_df = pd.json_normalize(df['scores'])
        scores_df.columns = [f'score_{col}' for col in scores_df.columns]
        df = pd.concat([df, scores_df], axis=1)
    
    return df


def get_experiment_statistics(experiment_name, metric=None, task_type=None):
    """Get statistics for experiment data"""
    df = load_experiment_results(experiment_name, only_completed_users=True)
    
    if df.empty:
        return {
            'total_responses': 0,
            'unique_users': 0,
            'metrics_stats': {},
            'task_type_stats': {},
            'error': 'No data found'
        }
    
    # Filter by task_type if specified
    if task_type and 'task_type' in df.columns:
        df = df[df['task_type'] == task_type]
    
    # Get score columns
    score_columns = [col for col in df.columns if col.startswith('score_')]
    
    # Calculate overall statistics
    stats = {
        'total_responses': len(df),
        'unique_users': df['user_id'].nunique() if 'user_id' in df.columns else 0,
        'unique_questions': df['question_id'].nunique() if 'question_id' in df.columns else 0,
        'metrics_stats': {},
        'task_type_stats': {}
    }
    
    # Calculate statistics for each metric
    for col in score_columns:
        metric_name = col.replace('score_', '')
        if metric and metric != metric_name:
            continue
            
        metric_data = df[col].dropna()
        if len(metric_data) > 0:
            # Handle NaN values for JSON serialization
            std_val = float(metric_data.std())
            if pd.isna(std_val) or std_val != std_val:  # Check for NaN
                std_val = 0.0
            
            stats['metrics_stats'][metric_name] = {
                'count': len(metric_data),
                'mean': float(metric_data.mean()),
                'std': std_val,
                'min': float(metric_data.min()),
                'max': float(metric_data.max()),
                'median': float(metric_data.median()),
                'q25': float(metric_data.quantile(0.25)),
                'q75': float(metric_data.quantile(0.75))
            }
    
    # Calculate statistics grouped by task_type
    if 'task_type' in df.columns and not task_type:  # Only if not filtering by specific task_type
        task_types = df['task_type'].unique()
        for tt in task_types:
            task_df = df[df['task_type'] == tt]
            task_stats = {
                'total_responses': len(task_df),
                'unique_users': task_df['user_id'].nunique() if 'user_id' in task_df.columns else 0,
                'unique_questions': task_df['question_id'].nunique() if 'question_id' in task_df.columns else 0,
                'metrics_stats': {}
            }
            
            # Calculate metrics for this task type
            for col in score_columns:
                metric_name = col.replace('score_', '')
                metric_data = task_df[col].dropna()
                if len(metric_data) > 0:
                    # Handle NaN values for JSON serialization
                    std_val = float(metric_data.std())
                    if pd.isna(std_val) or std_val != std_val:  # Check for NaN
                        std_val = 0.0
                    
                    task_stats['metrics_stats'][metric_name] = {
                        'count': len(metric_data),
                        'mean': float(metric_data.mean()),
                        'std': std_val,
                        'min': float(metric_data.min()),
                        'max': float(metric_data.max()),
                        'median': float(metric_data.median()),
                        'q25': float(metric_data.quantile(0.25)),
                        'q75': float(metric_data.quantile(0.75))
                    }
            
            stats['task_type_stats'][tt] = task_stats
    
    return stats


def generate_score_distribution_plot(experiment_name, metric, task_type=None):
    """Generate score distribution histogram for a specific metric"""
    df = load_experiment_results(experiment_name, only_completed_users=True)
    
    if df.empty:
        return None
    
    # Filter by task_type if specified
    if task_type and 'task_type' in df.columns:
        df = df[df['task_type'] == task_type]
    
    score_col = f'score_{metric}'
    if score_col not in df.columns:
        return None
    
    # Create plot with better size for web display
    plt.figure(figsize=(8, 5))
    plt.style.use('default')
    
    data = df[score_col].dropna()
    if len(data) == 0:
        plt.close()
        return None
    
    # Create histogram
    plt.hist(data, bins=range(1, 7), alpha=0.7, edgecolor='black', align='left')
    plt.xlabel('Score')
    plt.ylabel('Frequency')
    
    # Create title with task type if specified
    if task_type:
        plt.title(f'{metric} Score Distribution - {task_type.upper()}')
    else:
        plt.title(f'{metric} Score Distribution')
    
    plt.xticks(range(1, 6))
    plt.grid(True, alpha=0.3)
    
    # Add statistics text
    mean_val = data.mean()
    std_val = data.std()
    plt.text(0.02, 0.98, f'Mean: {mean_val:.2f}\nStd: {std_val:.2f}\nN: {len(data)}',
             transform=plt.gca().transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Convert plot to base64 string with optimized settings
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64


def get_task_type_summary(experiment_name):
    """Get summary statistics grouped by task type"""
    df = load_experiment_results(experiment_name)
    
    if df.empty or 'task_type' not in df.columns:
        return {}
    
    task_types = df['task_type'].unique()
    summary = {}
    
    for task_type in task_types:
        task_df = df[df['task_type'] == task_type]
        score_columns = [col for col in task_df.columns if col.startswith('score_')]
        
        task_summary = {
            'total_responses': len(task_df),
            'unique_questions': task_df['question_id'].nunique() if 'question_id' in task_df.columns else 0,
            'metrics': {}
        }
        
        for col in score_columns:
            metric_name = col.replace('score_', '')
            metric_data = task_df[col].dropna()
            if len(metric_data) > 0:
                # Handle NaN values for JSON serialization
                std_val = float(metric_data.std())
                if pd.isna(std_val) or std_val != std_val:  # Check for NaN
                    std_val = 0.0
                
                task_summary['metrics'][metric_name] = {
                    'count': len(metric_data),
                    'mean': float(metric_data.mean()),
                    'std': std_val
                }
        
        summary[task_type] = task_summary
    
    return summary


def get_completed_users_count(experiment_name):
    """Get count of users who completed ALL questions in the experiment"""
    completed_users = get_completed_users_for_experiment(experiment_name)
    return len(completed_users)