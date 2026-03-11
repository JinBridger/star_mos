// Admin dashboard JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    let currentChart = null;
    
    // Handle experiment selection
    const experimentItems = document.querySelectorAll('.experiment-item');
    
    experimentItems.forEach(item => {
        item.addEventListener('click', function() {
            // Update active state
            experimentItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            const experimentName = this.dataset.experiment;
            loadExperimentAnalysis(experimentName);
        });
    });
    
    function loadExperimentAnalysis(experimentName) {
        const analysisContent = document.getElementById('analysis-content');
        
        // Show loading state
        analysisContent.innerHTML = `
            <div class="card">
                <div class="card-body text-center">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="mt-2">加载分析数据中...</div>
                </div>
            </div>
        `;
        
        // Load experiment statistics
        fetch(`/admin/api/experiment/${experimentName}/stats`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                    return;
                }
                
                renderAnalysisResults(experimentName, data);
            })
            .catch(error => {
                console.error('Error loading stats:', error);
                showError('加载统计数据失败');
            });
    }
    
    function renderAnalysisResults(experimentName, stats) {
        const analysisContent = document.getElementById('analysis-content');
        
        let html = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5>实验概况 - ${experimentName}</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-primary">${stats.total_responses}</h4>
                                <small class="text-muted">总回答数</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-success">${stats.unique_users}</h4>
                                <small class="text-muted">参与用户</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-info">${stats.unique_questions}</h4>
                                <small class="text-muted">题目数量</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-warning">${Object.keys(stats.metrics_stats).length}</h4>
                                <small class="text-muted">评估指标</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Task type grouped metrics analysis
        if (stats.task_type_stats && Object.keys(stats.task_type_stats).length > 0) {
            Object.entries(stats.task_type_stats).forEach(([taskType, taskStats]) => {
                if (taskStats.metrics_stats && Object.keys(taskStats.metrics_stats).length > 0) {
                    html += `
                        <div class="card mb-4">
                            <div class="card-header">
                                <h5>指标分析 - ${taskType.toUpperCase()}</h5>
                                <small class="text-muted">
                                    ${taskStats.total_responses} 个回答 | 
                                    ${taskStats.unique_users} 个用户 | 
                                    ${taskStats.unique_questions} 个题目
                                </small>
                            </div>
                            <div class="card-body">
                                <div class="row">
                    `;
                    
                    Object.entries(taskStats.metrics_stats).forEach(([metric, metricStats]) => {
                        const chartId = `chart-${taskType}-${metric}`;
                        const loadingId = `chart-loading-${taskType}-${metric}`;
                        
                        html += `
                            <div class="col-md-6 mb-4">
                                <h6>${metric} 指标</h6>
                                <div class="chart-container">
                                    <img id="${chartId}" alt="${metric} Score Distribution - ${taskType}" 
                                         style="display: none;" />
                                    <div id="${loadingId}" class="text-center">
                                        <div class="spinner-border spinner-border-sm" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                        <div class="mt-2 small">加载图表中...</div>
                                    </div>
                                </div>
                                <table class="table table-sm stats-table">
                                    <thead>
                                        <tr>
                                            <th>统计量</th>
                                            <th>数值</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr><td>样本数</td><td>${metricStats.count}</td></tr>
                                        <tr><td>平均值</td><td>${metricStats.mean.toFixed(3)}</td></tr>
                                        <tr><td>标准差</td><td>${metricStats.std.toFixed(3)}</td></tr>
                                        <tr><td>中位数</td><td>${metricStats.median.toFixed(3)}</td></tr>
                                        <tr><td>最小值</td><td>${metricStats.min}</td></tr>
                                        <tr><td>最大值</td><td>${metricStats.max}</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        `;
                    });
                    
                    html += `
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
        }
        
        // Task type analysis section
        html += `
            <div class="card mb-4">
                <div class="card-header">
                    <h5>任务类型分析</h5>
                </div>
                <div class="card-body" id="task-analysis">
                    <div class="text-center">
                        <div class="spinner-border spinner-border-sm" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <span class="ms-2">加载任务分析...</span>
                    </div>
                </div>
            </div>
        `;
        
        analysisContent.innerHTML = html;
        
        // Load charts for each task type and metric
        if (stats.task_type_stats) {
            Object.entries(stats.task_type_stats).forEach(([taskType, taskStats]) => {
                if (taskStats.metrics_stats) {
                    Object.keys(taskStats.metrics_stats).forEach(metric => {
                        loadMetricChart(experimentName, metric, taskType);
                    });
                }
            });
        }
        
        // Load task type analysis
        loadTaskAnalysis(experimentName);
    }
    
    function loadMetricChart(experimentName, metric, taskType = null) {
        const url = taskType 
            ? `/admin/api/experiment/${experimentName}/plot/${metric}?task_type=${taskType}`
            : `/admin/api/experiment/${experimentName}/plot/${metric}`;
            
        const chartId = taskType ? `chart-${taskType}-${metric}` : `chart-${metric}`;
        const loadingId = taskType ? `chart-loading-${taskType}-${metric}` : `chart-loading-${metric}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const imgElement = document.getElementById(chartId);
                const loadingElement = document.getElementById(loadingId);
                
                if (data.error) {
                    const displayName = taskType ? `${taskType.toUpperCase()} - ${metric}` : metric;
                    console.error(`Error loading chart for ${displayName}:`, data.error);
                    if (loadingElement) {
                        loadingElement.innerHTML = `
                            <div class="alert alert-warning">
                                <small>无法加载 ${displayName} 图表</small>
                            </div>
                        `;
                    }
                    return;
                }
                
                if (imgElement && data.plot) {
                    // Set image source
                    imgElement.src = `data:image/png;base64,${data.plot}`;
                    imgElement.onload = function() {
                        // Hide loading and show image
                        if (loadingElement) {
                            loadingElement.style.display = 'none';
                        }
                        imgElement.style.display = 'block';
                    };
                    imgElement.onerror = function() {
                        // Handle image loading error
                        if (loadingElement) {
                            loadingElement.innerHTML = `
                                <div class="alert alert-danger">
                                    <small>图表加载失败</small>
                                </div>
                            `;
                        }
                    };
                } else {
                    const displayName = taskType ? `${taskType.toUpperCase()} - ${metric}` : metric;
                    if (loadingElement) {
                        loadingElement.innerHTML = `
                            <div class="alert alert-info">
                                <small>暂无 ${displayName} 数据</small>
                            </div>
                        `;
                    }
                }
            })
            .catch(error => {
                const displayName = taskType ? `${taskType.toUpperCase()} - ${metric}` : metric;
                console.error(`Error loading chart for ${displayName}:`, error);
                if (loadingElement) {
                    loadingElement.innerHTML = `
                        <div class="alert alert-danger">
                            <small>网络错误，无法加载图表</small>
                        </div>
                    `;
                }
            });
    }
    
    function loadTaskAnalysis(experimentName) {
        fetch(`/admin/api/experiment/${experimentName}/task_summary`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('task-analysis').innerHTML = 
                        `<div class="alert alert-warning">${data.error}</div>`;
                    return;
                }
                
                renderTaskAnalysis(data);
            })
            .catch(error => {
                console.error('Error loading task analysis:', error);
                document.getElementById('task-analysis').innerHTML = 
                    '<div class="alert alert-danger">加载任务分析失败</div>';
            });
    }
    
    function renderTaskAnalysis(taskData) {
        const taskAnalysisDiv = document.getElementById('task-analysis');
        
        if (Object.keys(taskData).length === 0) {
            taskAnalysisDiv.innerHTML = '<div class="alert alert-info">暂无任务类型数据</div>';
            return;
        }
        
        let html = '<div class="row">';
        
        Object.entries(taskData).forEach(([taskType, taskStats]) => {
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">${taskType.toUpperCase()}</h6>
                        </div>
                        <div class="card-body">
                            <p class="mb-2">
                                <strong>总回答数：</strong> ${taskStats.total_responses}<br>
                                <strong>题目数量：</strong> ${taskStats.unique_questions}
                            </p>
                            
                            <h6>指标统计：</h6>
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>指标</th>
                                        <th>均值</th>
                                        <th>标准差</th>
                                        <th>样本数</th>
                                    </tr>
                                </thead>
                                <tbody>
            `;
            
            Object.entries(taskStats.metrics).forEach(([metric, metricStats]) => {
                html += `
                    <tr>
                        <td>${metric}</td>
                        <td>${metricStats.mean.toFixed(3)}</td>
                        <td>${metricStats.std.toFixed(3)}</td>
                        <td>${metricStats.count}</td>
                    </tr>
                `;
            });
            
            html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        taskAnalysisDiv.innerHTML = html;
    }
    
    function showError(message) {
        const analysisContent = document.getElementById('analysis-content');
        analysisContent.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <div class="alert alert-danger">
                        <h5>错误</h5>
                        <p class="mb-0">${message}</p>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Auto-refresh functionality
    let autoRefreshInterval;
    
    function startAutoRefresh() {
        autoRefreshInterval = setInterval(() => {
            const activeExperiment = document.querySelector('.experiment-item.active');
            if (activeExperiment) {
                const experimentName = activeExperiment.dataset.experiment;
                loadExperimentAnalysis(experimentName);
            }
        }, 30000); // Refresh every 30 seconds
    }
    
    function stopAutoRefresh() {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
        }
    }
    
    // Start auto-refresh when page loads
    startAutoRefresh();
    
    // Stop auto-refresh when page is hidden
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    });
});