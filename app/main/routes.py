import os
from flask import render_template, request, session, redirect, url_for, jsonify, current_app
from app.main import bp
from app.main.utils import (
    get_available_experiments, generate_user_id, load_questions,
    load_metric_definitions, load_task_definitions, save_user_responses, 
    mark_user_completed, is_user_completed, calculate_system_scores, save_system_scores
)
from app.main.audio_utils import get_cached_mel_spectrogram
from app.main.video_utils import get_cached_composite_video


@bp.route('/')
def welcome():
    """Welcome page showing available experiments"""
    experiments = get_available_experiments()
    return render_template('main/welcome.html', experiments=experiments)


@bp.route('/experiment/<experiment_name>')
def experiment_verification(experiment_name):
    """Experiment verification page"""
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return redirect(url_for('main.welcome'))

    return render_template(
        'main/welcome.html',
        experiments=experiments,
        selected_experiment=experiment_name
    )


@bp.route('/experiment/<experiment_name>/verify', methods=['POST'])
def verify_experiment(experiment_name):
    """Verify experiment access code"""
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return redirect(url_for('main.welcome'))

    verification_code = request.form.get('verification_code', '').strip()
    expected_code = current_app.config['EXPERIMENT_CODES'].get(experiment_name)

    if verification_code != expected_code:
        return render_template(
            'main/welcome.html',
            experiments=experiments,
            selected_experiment=experiment_name,
            error='Invalid verification code'
        )

    # Generate user ID and initialize session
    user_id = generate_user_id()
    session['user_id'] = user_id
    session['experiment_name'] = experiment_name
    session['current_question_index'] = 0
    session['user_responses'] = []  # Store all responses in session

    # Check if user already completed (shouldn't happen with new ID, but safety check)
    if is_user_completed(experiment_name, user_id):
        return redirect(url_for('main.thanks'))

    return redirect(
        url_for('main.experiment_question', experiment_name=experiment_name)
    )


@bp.route('/experiment/<experiment_name>/question')
def experiment_question(experiment_name):
    """Display experiment question"""
    
    # Check session validity
    if (
        'user_id' not in session or 'experiment_name' not in session or
        session['experiment_name'] != experiment_name
    ):
        return redirect(url_for('main.welcome'))

    user_id = session['user_id']
    current_index = session.get('current_question_index', 0)

    # Check if user already completed
    if is_user_completed(experiment_name, user_id):
        return redirect(url_for('main.thanks'))

    # Load questions and definitions
    questions = load_questions(experiment_name, user_id)
    metric_definitions = load_metric_definitions(experiment_name)
    task_definitions = load_task_definitions(experiment_name)

    if not questions:
        return "Error loading questions", 500

    # Check if all questions completed
    if current_index >= len(questions):
        # Save all responses at once
        user_responses = session.get('user_responses', [])
        current_app.logger.info(f"Experiment completed. User responses count: {len(user_responses)}")
        
        if user_responses:
            save_success = save_user_responses(experiment_name, user_id, user_responses)
            current_app.logger.info(f"Save user responses result: {save_success}")
        else:
            current_app.logger.warning("No user responses to save!")
        
        # Calculate and save system scores
        system_scores = calculate_system_scores(experiment_name)
        save_system_scores(experiment_name, system_scores)
        
        mark_user_completed(experiment_name, user_id)
        session.pop('user_id', None)
        session.pop('experiment_name', None)
        session.pop('current_question_index', None)
        session.pop('user_responses', None)
        return redirect(url_for('main.thanks'))

    current_question = questions[current_index]

    # Get metric definitions for current question
    question_metrics = {}
    for metric in current_question.get('metrics', []):
        if metric in metric_definitions:
            question_metrics[metric] = metric_definitions[metric]

    # Get task description
    task_type = current_question.get('task_type', '')
    task_description = ''
    if task_type and task_type in task_definitions:
        task_description = task_definitions[task_type].get('description', '')

    # Get pre-generated mel spectrograms from cache
    mel_spectrograms = {}
    
    # Ground truth audio mel
    if current_question.get('show_gt_audio_mel') and current_question.get('gt_audio_path'):
        gt_mel = get_cached_mel_spectrogram(current_question['gt_audio_path'])
        print(f'loaded gt mel spectrogram from cache, success: {gt_mel is not None}')
        if gt_mel:
            mel_spectrograms['gt_audio_mel'] = gt_mel

    # Generated audio mel for each system (always show for SR tasks, or when explicitly enabled)
    if 'systems' in current_question:
        for system in current_question['systems']:
            if 'audio_path' in system:
                # For SR tasks, always show mel spectrograms for generated audio
                # For other tasks, check if show_gen_audio_mel is enabled
                should_show_mel = (
                    current_question.get('task_type') == 'sr' or 
                    current_question.get('show_gen_audio_mel', False)
                )
                
                if should_show_mel:
                    system_mel = get_cached_mel_spectrogram(system['audio_path'])
                    print(f'loaded {system["system_id"]} mel spectrogram from cache, success: {system_mel is not None}')
                    if system_mel:
                        mel_spectrograms[f'{system["system_id"]}_mel'] = system_mel

    # Prompt mel (for audio prompts)
    if current_question.get('show_prompt_mel') and current_question.get('prompt'):
        prompt = current_question['prompt']
        # Check if prompt is an audio file path
        if prompt.startswith('/static/') and (prompt.endswith('.wav') or prompt.endswith('.mp3') or prompt.endswith('.flac')):
            prompt_mel = get_cached_mel_spectrogram(prompt)
            print(f'loaded prompt mel spectrogram from cache, success: {prompt_mel is not None}')
            if prompt_mel:
                mel_spectrograms['prompt_mel'] = prompt_mel

    # Handle V2A (Video-to-Audio) task composite video generation
    composite_video_paths = {}
    if current_question.get('task_type') == 'v2a' and 'systems' in current_question:
        video_path = current_question.get('prompt')  # Original video
        
        for system in current_question['systems']:
            if 'audio_path' in system:
                audio_path = system['audio_path']  # Generated audio
                
                if video_path and audio_path:
                    composite_video_path = get_cached_composite_video(video_path, audio_path)
                    print(f'loaded composite video for {system["system_id"]} from cache, success: {composite_video_path is not None}')
                    if composite_video_path:
                        composite_video_paths[system['system_id']] = composite_video_path

    # Get previously saved answers for this question
    user_responses = session.get('user_responses', [])
    previous_answers = {}
    
    if current_index < len(user_responses):
        saved_response = user_responses[current_index]
        if saved_response and 'scores' in saved_response:
            previous_answers = saved_response['scores']
    
    is_last_question = (current_index + 1) >= len(questions)
    current_app.logger.info(f"Rendering question {current_index + 1}/{len(questions)}, is_last_question: {is_last_question}")

    return render_template(
        'main/experiment.html',
        question=current_question,
        metrics=question_metrics,
        task_description=task_description,
        mel_spectrograms=mel_spectrograms,
        composite_video_paths=composite_video_paths,
        current_index=current_index + 1,
        total_questions=len(questions),
        experiment_name=experiment_name,
        can_go_back=current_index > 0,
        is_last_question=is_last_question,
        previous_answers=previous_answers
    )


@bp.route('/experiment/<experiment_name>/submit', methods=['POST'])
def submit_answer(experiment_name):
    """Submit answer via AJAX"""
    
    # Check session validity
    if (
        'user_id' not in session or 'experiment_name' not in session or
        session['experiment_name'] != experiment_name
    ):
        return jsonify({'error': 'Invalid session'}), 400

    user_id = session['user_id']
    current_index = session.get('current_question_index', 0)

    # Check if user already completed
    if is_user_completed(experiment_name, user_id):
        return jsonify({'error': 'Already completed'}), 400

    # Get submitted data
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Load questions to get question_id
    questions = load_questions(experiment_name, user_id)
    if current_index >= len(questions):
        return jsonify({'error': 'No more questions'}), 400

    current_question = questions[current_index]

    # Prepare response data
    response_data = {
        'user_id': user_id,
        'experiment_name': experiment_name,
        'sample_id': current_question.get('sample_id', f'sample_{current_index}'),
        'question_index': current_index,
        'task_type': current_question.get('task_type', 'unknown'),
        'scores': data.get('scores', {}),
        'response_time_ms': data.get('response_time_ms', 0)
    }

    # Store response in session
    user_responses = session.get('user_responses', [])
    
    # Update or add response at current index
    if current_index < len(user_responses):
        user_responses[current_index] = response_data
    else:
        user_responses.append(response_data)
    
    session['user_responses'] = user_responses
    
    current_app.logger.info(f"Stored response for question {current_index + 1}. Total responses: {len(user_responses)}")

    # Update session
    session['current_question_index'] = current_index + 1

    # Check if this was the last question
    is_last_question = (current_index + 1) >= len(questions)
    
    current_app.logger.info(f"Is last question: {is_last_question}")

    return jsonify({
        'success': True,
        'is_last_question': is_last_question,
        'next_question_index': current_index + 1
    })


@bp.route('/experiment/<experiment_name>/previous', methods=['POST'])
def go_to_previous_question(experiment_name):
    """Go to previous question"""
    # Check session validity
    if (
        'user_id' not in session or 'experiment_name' not in session or
        session['experiment_name'] != experiment_name
    ):
        return jsonify({'error': 'Invalid session'}), 400

    current_index = session.get('current_question_index', 0)
    
    if current_index > 0:
        session['current_question_index'] = current_index - 1
        return jsonify({
            'success': True,
            'previous_question_index': current_index - 1
        })
    else:
        return jsonify({'error': 'Already at first question'}), 400


@bp.route('/experiments/<experiment_name>/<path:filename>')
def experiment_file(experiment_name, filename):
    """Serve files from experiment directories"""
    from flask import send_from_directory
    
    # Security check: ensure the experiment exists
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return "Experiment not found", 404
    
    # Get the experiment directory path
    experiment_dir = os.path.join(current_app.config['EXPERIMENTS_DIR'], experiment_name)
    
    # Security check: ensure the file is within the experiment directory
    requested_path = os.path.join(experiment_dir, filename)
    if not os.path.abspath(requested_path).startswith(os.path.abspath(experiment_dir)):
        return "Access denied", 403
    
    # Check if file exists
    if not os.path.exists(requested_path):
        return "File not found", 404
    
    # Serve the file
    try:
        # Use absolute path for send_from_directory
        abs_experiment_dir = os.path.abspath(experiment_dir)
        return send_from_directory(abs_experiment_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving file: {e}")
        return f"Error serving file: {str(e)}", 500


@bp.route('/thanks')
def thanks():
    """Thank you page"""
    return render_template('main/thanks.html')
