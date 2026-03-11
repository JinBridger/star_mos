import os
import json
import uuid
import random
from datetime import datetime
from flask import current_app

# Windows兼容性处理
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False


def get_available_experiments():
    """Get list of available experiments by scanning experiments directory"""
    experiments_dir = current_app.config['EXPERIMENTS_DIR']
    experiments = []
    
    if os.path.exists(experiments_dir):
        for item in os.listdir(experiments_dir):
            experiment_path = os.path.join(experiments_dir, item)
            if os.path.isdir(experiment_path):
                manifest_path = os.path.join(experiment_path, 'manifest.jsonl')
                metric_path = os.path.join(experiment_path, 'metric_defination.json')
                if os.path.exists(manifest_path) and os.path.exists(metric_path):
                    experiments.append(item)
    
    return experiments


def generate_user_id():
    """Generate unique user ID"""
    return uuid.uuid4().hex


def load_questions(experiment_name, user_id=None):
    """Load questions from manifest.jsonl file"""
    manifest_path = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                                experiment_name, 'manifest.jsonl')
    
    questions = []
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    question = json.loads(line)
                    # Randomize system order for each question, but keep it consistent for the user
                    if 'systems' in question:
                        systems = question['systems'].copy()
                        
                        # Use user_id as seed for consistent randomization
                        if user_id:
                            # Create a deterministic seed based on user_id and question content
                            seed_value = hash(user_id + str(question.get('question_id', '')))
                            random.seed(seed_value)
                        
                        random.shuffle(systems)
                        # Reassign system names to "样本1", "样本2", etc.
                        for i, system in enumerate(systems):
                            system['system_name'] = f"样本{i+1}"
                        question['systems'] = systems
                        
                        # Reset random seed to avoid affecting other parts of the application
                        if user_id:
                            random.seed()
                    
                    questions.append(question)
        return questions
    except Exception as e:
        current_app.logger.error(f"Error loading questions: {e}")
        return []


def load_metric_definitions(experiment_name):
    """Load metric definitions from metric_defination.json file"""
    metric_path = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'metric_defination.json')
    try:
        with open(metric_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        current_app.logger.error(f"Error loading metric definitions: {e}")
        return {}


def load_task_definitions(experiment_name):
    """Load task definitions from task_defination.json file"""
    task_path = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                            experiment_name, 'task_defination.json')
    try:
        with open(task_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        current_app.logger.error(f"Error loading task definitions: {e}")
        return {}


def save_user_responses(experiment_name, user_id, all_responses):
    """Save all user responses to file at once"""
    results_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'results')
    
    # Ensure results directory exists
    try:
        os.makedirs(results_dir, exist_ok=True)
    except Exception as e:
        current_app.logger.error(f"Failed to create results directory: {e}")
        return False
    
    user_file = os.path.join(results_dir, f'user_{user_id}.jsonl')
    
    current_app.logger.info(f"Saving {len(all_responses)} responses for user {user_id} to {user_file}")
    
    try:
        # Use file locking to prevent concurrent writes (if available)
        with open(user_file, 'w', encoding='utf-8') as f:
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            for response in all_responses:
                # Add timestamp to response
                response['timestamp'] = datetime.now().isoformat()
                f.write(json.dumps(response, ensure_ascii=False) + '\n')
            
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        current_app.logger.info(f"Successfully saved responses to {user_file}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error saving user responses: {e}")
        return False


def mark_user_completed(experiment_name, user_id):
    """Mark user as completed in completed_users.log"""
    results_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'results')
    
    os.makedirs(results_dir, exist_ok=True)
    
    completed_file = os.path.join(results_dir, 'completed_users.log')
    
    current_app.logger.info(f"Marking user {user_id} as completed in {completed_file}")
    
    try:
        with open(completed_file, 'a', encoding='utf-8') as f:
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            f.write(f"{user_id},{datetime.now().isoformat()}\n")
            
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        current_app.logger.info(f"Successfully marked user {user_id} as completed")
        return True
    except Exception as e:
        current_app.logger.error(f"Error marking user completed: {e}")
        return False


def is_user_completed(experiment_name, user_id):
    """Check if user has already completed the experiment"""
    results_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'results')
    
    completed_file = os.path.join(results_dir, 'completed_users.log')
    
    if not os.path.exists(completed_file):
        return False
    
    try:
        with open(completed_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith(user_id + ','):
                    return True
    except Exception as e:
        current_app.logger.error(f"Error checking user completion: {e}")
    
    return False


def calculate_system_scores(experiment_name):
    """Calculate final system scores from all user responses"""
    results_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'results')
    
    if not os.path.exists(results_dir):
        current_app.logger.warning(f"Results directory does not exist: {results_dir}")
        return {}
    
    # Collect all responses
    all_responses = []
    for filename in os.listdir(results_dir):
        if filename.startswith('user_') and filename.endswith('.jsonl'):
            user_file = os.path.join(results_dir, filename)
            try:
                with open(user_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            all_responses.append(json.loads(line))
            except Exception as e:
                current_app.logger.error(f"Error reading user file {filename}: {e}")
    
    current_app.logger.info(f"Calculating system scores from {len(all_responses)} responses")
    
    # Group responses by system and metric
    system_scores = {}
    
    for response in all_responses:
        sample_id = response.get('sample_id')
        scores = response.get('scores', {})
        
        for system_id, system_scores_dict in scores.items():
            if system_id not in system_scores:
                system_scores[system_id] = {}
            
            for metric, score in system_scores_dict.items():
                if metric not in system_scores[system_id]:
                    system_scores[system_id][metric] = []
                system_scores[system_id][metric].append(score)
    
    # Calculate statistics for each system and metric
    final_scores = {}
    for system_id, metrics in system_scores.items():
        final_scores[system_id] = {}
        for metric, scores_list in metrics.items():
            if scores_list:
                final_scores[system_id][metric] = {
                    'mean': sum(scores_list) / len(scores_list),
                    'std': (sum((x - sum(scores_list) / len(scores_list)) ** 2 for x in scores_list) / len(scores_list)) ** 0.5,
                    'count': len(scores_list),
                    'min': min(scores_list),
                    'max': max(scores_list)
                }
    
    current_app.logger.info(f"Calculated scores for {len(final_scores)} systems")
    return final_scores


def save_system_scores(experiment_name, system_scores):
    """Save calculated system scores to file"""
    results_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], 
                              experiment_name, 'results')
    
    os.makedirs(results_dir, exist_ok=True)
    
    scores_file = os.path.join(results_dir, 'system_scores.json')
    
    current_app.logger.info(f"Saving system scores to {scores_file}")
    
    try:
        with open(scores_file, 'w', encoding='utf-8') as f:
            json.dump(system_scores, f, ensure_ascii=False, indent=2)
        
        current_app.logger.info(f"Successfully saved system scores to {scores_file}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error saving system scores: {e}")
        return False