from flask import render_template, request, session, redirect, url_for, jsonify, current_app
from app.admin import bp
from app.main.utils import get_available_experiments, load_metric_definitions, calculate_system_scores
from app.admin.analysis_tools import (
    get_experiment_statistics, generate_score_distribution_plot,
    get_task_type_summary, get_completed_users_count
)
from app.admin.chart_cache import (
    pregenerate_all_charts, load_chart_from_cache, 
    get_chart_generation_progress
)


@bp.route('/login')
def login():
    """Admin login page"""
    return render_template('admin/login.html')


@bp.route('/verify', methods=['POST'])
def verify_admin():
    """Verify admin access"""
    verification_code = request.form.get('verification_code', '').strip()
    expected_code = current_app.config['ADMIN_VERIFICATION_CODE']
    
    if verification_code != expected_code:
        return render_template('admin/login.html', error='Invalid verification code')
    
    session['admin_verified'] = True
    
    # Check if charts need to be generated
    progress = get_chart_generation_progress()
    if not progress['completed']:
        return redirect(url_for('admin.generate_charts'))
    
    return redirect(url_for('admin.dashboard'))


@bp.route('/generate_charts')
def generate_charts():
    """Chart generation page with progress"""
    # Check admin verification
    if not session.get('admin_verified'):
        return redirect(url_for('admin.login'))
    
    return render_template('admin/generate_charts.html')


@bp.route('/api/generate_charts', methods=['POST'])
def api_generate_charts():
    """API endpoint to start chart generation"""
    # Check admin verification
    if not session.get('admin_verified'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        success, total, generated, errors = pregenerate_all_charts()
        return jsonify({
            'success': success,
            'total_charts': total,
            'generated_charts': generated,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/chart_progress')
def api_chart_progress():
    """API endpoint to get chart generation progress"""
    # Check admin verification
    if not session.get('admin_verified'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    progress = get_chart_generation_progress()
    return jsonify(progress)


@bp.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    # Check admin verification
    if not session.get('admin_verified'):
        return redirect(url_for('admin.login'))
    
    experiments = get_available_experiments()
    
    # Get basic info for each experiment
    experiment_info = {}
    for experiment in experiments:
        experiment_info[experiment] = {
            'completed_users': get_completed_users_count(experiment),
            'metrics': list(load_metric_definitions(experiment).keys())
        }
    
    return render_template('admin/dashboard.html', 
                         experiments=experiments,
                         experiment_info=experiment_info)


@bp.route('/system_scores/<experiment_name>')
def system_scores(experiment_name):
    """System scores analysis page"""
    # Check admin verification
    if not session.get('admin_verified'):
        return redirect(url_for('admin.login'))
    
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return redirect(url_for('admin.dashboard'))
    
    # Calculate system scores
    system_scores = calculate_system_scores(experiment_name)
    
    # Get metric definitions for display
    metric_definitions = load_metric_definitions(experiment_name)
    
    return render_template('admin/system_scores.html',
                         experiment_name=experiment_name,
                         system_scores=system_scores,
                         metric_definitions=metric_definitions)


@bp.route('/api/system_scores/<experiment_name>')
def api_system_scores(experiment_name):
    """API endpoint to get system scores"""
    # Check admin verification
    if not session.get('admin_verified'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return jsonify({'error': 'Experiment not found'}), 404
    
    # Calculate system scores
    system_scores = calculate_system_scores(experiment_name)
    
    return jsonify(system_scores)


@bp.route('/api/experiment/<experiment_name>/stats')
def get_experiment_stats(experiment_name):
    """Get experiment statistics via API"""
    # Check admin verification
    if not session.get('admin_verified'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return jsonify({'error': 'Experiment not found'}), 404
    
    metric = request.args.get('metric')
    task_type = request.args.get('task_type')
    
    stats = get_experiment_statistics(experiment_name, metric, task_type)
    return jsonify(stats)


@bp.route('/api/experiment/<experiment_name>/plot/<metric>')
def get_score_plot(experiment_name, metric):
    """Get score distribution plot via API (from cache)"""
    # Check admin verification
    if not session.get('admin_verified'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return jsonify({'error': 'Experiment not found'}), 404
    
    task_type = request.args.get('task_type')
    
    # Try to load from cache first
    plot_data = load_chart_from_cache(experiment_name, metric, task_type)
    
    if plot_data is None:
        # Fallback: generate if not in cache
        plot_data = generate_score_distribution_plot(experiment_name, metric, task_type)
        
        # Save to cache for future use
        if plot_data:
            from app.admin.chart_cache import save_chart_to_cache
            save_chart_to_cache(experiment_name, metric, plot_data, task_type)
    
    if plot_data is None:
        return jsonify({'error': 'No data available for this metric'}), 404
    
    return jsonify({'plot': plot_data})


@bp.route('/api/experiment/<experiment_name>/task_summary')
def get_task_summary(experiment_name):
    """Get task type summary via API"""
    # Check admin verification
    if not session.get('admin_verified'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    experiments = get_available_experiments()
    if experiment_name not in experiments:
        return jsonify({'error': 'Experiment not found'}), 404
    
    summary = get_task_type_summary(experiment_name)
    return jsonify(summary)


@bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_verified', None)
    return redirect(url_for('admin.login'))