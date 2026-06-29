import React, { useState, useEffect, useRef } from 'react';
import './App.css';

export default function App() {
  // --- States ---
  const [status, setStatus] = useState({
    running: false,
    uptime: null,
    video_id: null,
    welcomed_count: 0,
    error: null,
  });

  const [config, setConfig] = useState({
    channel_id: '',
    video_id: '',
    bot_prefix: '/',
    welcome_message: '',
    cooldown_seconds: 5,
    poll_duration: 5,
  });

  const [commands, setCommands] = useState([]);
  
  const [poll, setPoll] = useState({
    question: '',
    options: ['', ''],
  });

  const [logs, setLogs] = useState([]);
  const [logFilter, setLogFilter] = useState('ALL');
  const [logSearch, setLogSearch] = useState('');
  const [autoScrollLogs, setAutoScrollLogs] = useState(true);
  
  const [toasts, setToasts] = useState([]);
  
  const [loading, setLoading] = useState({
    status: false,
    config: false,
    commands: false,
    startStop: false,
    poll: false,
  });

  // --- Refs ---
  const logViewerRef = useRef(null);

  // --- Toast helper ---
  const showToast = (message, type = 'info') => {
    const id = Date.now() + Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  // --- API Helpers ---
  const apiCall = async (url, method = 'GET', body = null) => {
    try {
      const options = { method };
      if (body) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(body);
      }
      const response = await fetch(url, options);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData?.error || `HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      showToast(err.message, 'error');
      return null;
    }
  };

  // --- Fetch Initial Data ---
  const fetchStatus = async () => {
    const data = await apiCall('/api/status');
    if (data) {
      setStatus(data);
      if (data.error) {
        showToast(data.error, 'error');
      }
    }
  };

  const fetchConfig = async () => {
    setLoading(prev => ({ ...prev, config: true }));
    const data = await apiCall('/api/config');
    if (data) {
      setConfig({
        channel_id: data.channel_id || '',
        video_id: data.video_id || '',
        bot_prefix: data.bot_prefix || '/',
        welcome_message: data.welcome_message || '',
        cooldown_seconds: data.cooldown_seconds ?? 5,
        poll_duration: data.poll_duration ?? 5,
      });
    }
    setLoading(prev => ({ ...prev, config: false }));
  };

  const fetchCommands = async () => {
    setLoading(prev => ({ ...prev, commands: true }));
    const data = await apiCall('/api/commands');
    if (data) {
      setCommands(data || []);
    }
    setLoading(prev => ({ ...prev, commands: false }));
  };

  // --- Lifecycle Hooks ---
  useEffect(() => {
    fetchStatus();
    fetchConfig();
    fetchCommands();

    // Poll status every 3 seconds
    const interval = setInterval(fetchStatus, 3000);

    // Connect to SSE log stream
    const eventSource = new EventSource('/api/logs/stream');
    eventSource.onmessage = (event) => {
      try {
        const entry = JSON.parse(event.data);
        setLogs((prev) => {
          const updated = [...prev, entry];
          return updated.slice(-1000);
        });
      } catch (err) {
        console.error('Failed to parse log record:', err);
      }
    };
    eventSource.onerror = () => {
      // Auto-reconnects
    };

    return () => {
      clearInterval(interval);
      eventSource.close();
    };
  }, []);

  // Log Auto-Scroll
  useEffect(() => {
    if (autoScrollLogs && logViewerRef.current) {
      logViewerRef.current.scrollTop = logViewerRef.current.scrollHeight;
    }
  }, [logs, autoScrollLogs]);

  // --- Bot Control Actions ---
  const startBot = async () => {
    setLoading(prev => ({ ...prev, startStop: true }));
    showToast('Starting background bot loop...', 'info');
    const result = await apiCall('/api/bot/start', 'POST');
    if (result && result.success) {
      showToast('Aster Bot started.', 'success');
      fetchStatus();
    }
    setLoading(prev => ({ ...prev, startStop: false }));
  };

  const stopBot = async () => {
    setLoading(prev => ({ ...prev, startStop: true }));
    showToast('Stopping bot loop...', 'info');
    const result = await apiCall('/api/bot/stop', 'POST');
    if (result && result.success) {
      showToast('Aster Bot stopped.', 'success');
      fetchStatus();
    }
    setLoading(prev => ({ ...prev, startStop: false }));
  };

  // --- Save Configuration ---
  const saveConfig = async (e) => {
    e.preventDefault();
    setLoading(prev => ({ ...prev, config: true }));
    
    const payload = {
      ...config,
      cooldown_seconds: parseInt(config.cooldown_seconds) || 5,
      poll_duration: parseInt(config.poll_duration) || 5,
      data_dir: 'data',
    };

    const result = await apiCall('/api/config', 'PUT', payload);
    if (result && result.success) {
      showToast(result.message || 'Config parameters saved.', 'success');
    }
    setLoading(prev => ({ ...prev, config: false }));
  };

  // --- Command list handlers ---
  const handleCommandChange = (index, field, value) => {
    const updated = [...commands];
    updated[index][field] = value;
    setCommands(updated);
  };

  const addCommandRow = () => {
    setCommands((prev) => [
      ...prev,
      { action: '/new', aliases: '', reply: 'Response content', isNewRow: true }
    ]);
    showToast('Appended command entry.', 'info');
  };

  const removeCommandRow = (index) => {
    setCommands((prev) => prev.filter((_, i) => i !== index));
  };

  const saveCommands = async () => {
    setLoading(prev => ({ ...prev, commands: true }));
    
    const processed = commands
      .filter((cmd) => cmd.action.trim())
      .map((cmd) => {
        let aliasesList = [];
        if (typeof cmd.aliases === 'string') {
          aliasesList = cmd.aliases
            .split(',')
            .map((a) => a.trim())
            .filter(Boolean);
        } else if (Array.isArray(cmd.aliases)) {
          aliasesList = cmd.aliases;
        }

        return {
          action: cmd.action.trim(),
          aliases: aliasesList,
          reply: cmd.reply.trim(),
        };
      });

    const result = await apiCall('/api/commands', 'PUT', processed);
    if (result && result.success) {
      showToast(result.message || 'Commands successfully reloaded.', 'success');
      fetchCommands();
    } else {
      setLoading(prev => ({ ...prev, commands: false }));
    }
  };

  // --- Live Poll handlers ---
  const handleAddPollOption = () => {
    if (poll.options.length >= 4) {
      showToast('Maximum of 4 options allowed.', 'warning');
      return;
    }
    setPoll((prev) => ({
      ...prev,
      options: [...prev.options, ''],
    }));
  };

  const handleRemovePollOption = (index) => {
    if (poll.options.length <= 2) {
      showToast('At least 2 options are required.', 'error');
      return;
    }
    setPoll((prev) => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index),
    }));
  };

  const handlePollOptionChange = (index, value) => {
    const updated = [...poll.options];
    updated[index] = value;
    setPoll((prev) => ({ ...prev, options: updated }));
  };

  const launchPoll = async () => {
    const question = poll.question.trim();
    const filledOptions = poll.options.map(o => o.trim()).filter(Boolean);

    if (!question) {
      showToast('Question input is blank.', 'error');
      return;
    }
    if (filledOptions.length < 2) {
      showToast('Provide at least 2 options.', 'error');
      return;
    }

    setLoading(prev => ({ ...prev, poll: true }));
    const result = await apiCall('/api/poll', 'POST', {
      question,
      options: filledOptions,
    });

    if (result && result.success) {
      showToast(result.message || 'Poll published to chat.', 'success');
      setPoll({ question: '', options: ['', ''] });
    }
    setLoading(prev => ({ ...prev, poll: false }));
  };

  // --- Logs Viewers ---
  const clearLogs = () => {
    setLogs([]);
    showToast('Logs viewport cleared.', 'info');
  };

  const formatUptime = (seconds) => {
    if (!seconds) return '—';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showToast('Value copied to clipboard.', 'success');
  };

  // Filter logs list
  const filteredLogs = logs.filter((log) => {
    if (logFilter !== 'ALL' && log.level !== logFilter) {
      return false;
    }
    if (logSearch) {
      return log.message.toLowerCase().includes(logSearch.toLowerCase());
    }
    return true;
  });

  return (
    <div className="app-container">
      {/* Dynamic Toast stack */}
      <div className="toast-stack">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast-alert ${toast.type}`}>
            <span>{toast.message}</span>
          </div>
        ))}
      </div>

      {/* Main Branding Header */}
      <span className="category-label">[ SYSTEM INTERFACE ]</span>
      <header className="app-header">
        <div className="logo-section">
          <span className="logo-icon">✦</span>
          <h1 className="logo-text">Aster</h1>
          <span className="badge-version">v3.0.0</span>
        </div>
        <div className={`status-pill ${status.running ? 'running' : 'stopped'}`}>
          <div className="status-indicator" />
          <span>{status.running ? 'Active' : 'Offline'}</span>
        </div>
      </header>

      {/* Bot Controls */}
      <span className="category-label">[ CONTROL MODULE ]</span>
      <div className="control-actions-bar">
        {status.running ? (
          <button 
            className="btn btn-danger" 
            onClick={stopBot} 
            disabled={loading.startStop}
          >
            Stop Moderator
          </button>
        ) : (
          <button 
            className="btn btn-primary" 
            onClick={startBot} 
            disabled={loading.startStop}
          >
            Start Moderator
          </button>
        )}
        <span className="system-status-msg">
          {status.running ? `System polling active. Session uptime: ${formatUptime(status.uptime)}` : 'System standby. Click Start to launch moderation loop.'}
        </span>
      </div>

      {/* Telemetry metrics */}
      <span className="category-label">[ LIVE TELEMETRY ]</span>
      <div className="dashboard-grid grid-3">
        <div className="panel-card">
          <div className="card-title">Broadcast Feed</div>
          <div className="stat-card-value">
            {status.video_id ? (
              <span 
                className="video-link-copy"
                onClick={() => copyToClipboard(status.video_id)}
                title="Copy Video ID"
              >
                {status.video_id}
              </span>
            ) : (
              'Auto-Detect'
            )}
          </div>
          <div className="stat-card-label">Current Video ID</div>
        </div>

        <div className="panel-card">
          <div className="card-title">Viewers Greeted</div>
          <div className="stat-card-value highlight">{status.welcomed_count}</div>
          <div className="stat-card-label">Total Welcomed</div>
        </div>

        <div className="panel-card">
          <div className="card-title">System Uptime</div>
          <div className="stat-card-value">{formatUptime(status.uptime)}</div>
          <div className="stat-card-label">Elapsed Time</div>
        </div>
      </div>

      {/* Secondary Configurations */}
      <div className="dashboard-grid grid-2-col" style={{ marginBottom: '40px' }}>
        
        {/* Config Form */}
        <div>
          <span className="category-label">[ CONFIGURATION ]</span>
          <div className="panel-card">
            <div className="card-title">Core Parameters</div>
            <form onSubmit={saveConfig}>
              <div className="form-group">
                <label className="form-label">Channel ID</label>
                <input
                  type="text"
                  className="input-field input-field-mono"
                  value={config.channel_id}
                  onChange={(e) => setConfig({ ...config, channel_id: e.target.value })}
                  placeholder="UCxxxxxxxxxx"
                />
                <div className="input-hint">Target channel to search for live streams</div>
              </div>

              <div className="form-group">
                <label className="form-label">Video ID Override</label>
                <input
                  type="text"
                  className="input-field input-field-mono"
                  value={config.video_id}
                  onChange={(e) => setConfig({ ...config, video_id: e.target.value })}
                  placeholder="Leave empty for auto-detect"
                />
                <div className="input-hint">Specific stream ID (skips search)</div>
              </div>

              <div className="form-group">
                <label className="form-label">Command Prefix</label>
                <input
                  type="text"
                  className="input-field input-field-mono"
                  value={config.bot_prefix}
                  onChange={(e) => setConfig({ ...config, bot_prefix: e.target.value })}
                  placeholder="/"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Welcome Text Template</label>
                <input
                  type="text"
                  className="input-field"
                  value={config.welcome_message}
                  onChange={(e) => setConfig({ ...config, welcome_message: e.target.value })}
                  placeholder="Welcome to the stream, {username}!"
                />
                <div className="input-hint">Greeting format. Use <code>{'{username}'}</code> for display name.</div>
              </div>

              <div className="form-group">
                <label className="form-label">Spam Cooldown (seconds)</label>
                <input
                  type="number"
                  min="0"
                  className="input-field input-field-mono"
                  value={config.cooldown_seconds}
                  onChange={(e) => setConfig({ ...config, cooldown_seconds: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Poll Active Time (minutes)</label>
                <input
                  type="number"
                  min="1"
                  className="input-field input-field-mono"
                  value={config.poll_duration}
                  onChange={(e) => setConfig({ ...config, poll_duration: e.target.value })}
                />
              </div>

              <div className="card-footer-actions">
                <button 
                  type="submit" 
                  className="btn btn-primary btn-sm"
                  disabled={loading.config}
                >
                  Save settings
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Custom Commands */}
        <div>
          <span className="category-label">[ COMMAND INTERCEPTS ]</span>
          <div className="panel-card">
            <div className="card-title">Chat Trigger Rules</div>
            <div className="table-container">
              <table className="commands-table">
                <thead>
                  <tr>
                    <th>Command</th>
                    <th>Aliases</th>
                    <th>Reply message</th>
                    <th style={{ width: '40px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {commands.map((cmd, idx) => (
                    <tr key={idx}>
                      <td>
                        <input
                          type="text"
                          className="input-field input-field-mono"
                          style={{ padding: '6px 8px' }}
                          value={cmd.action}
                          onChange={(e) => handleCommandChange(idx, 'action', e.target.value)}
                          placeholder="/command"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          className="input-field input-field-mono"
                          style={{ padding: '6px 8px' }}
                          value={
                            typeof cmd.aliases === 'string'
                              ? cmd.aliases
                              : (cmd.aliases || []).join(', ')
                          }
                          onChange={(e) => handleCommandChange(idx, 'aliases', e.target.value)}
                          placeholder="alias1, alias2"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          className="input-field"
                          style={{ padding: '6px 8px' }}
                          value={cmd.reply}
                          onChange={(e) => handleCommandChange(idx, 'reply', e.target.value)}
                          placeholder="Response"
                        />
                      </td>
                      <td>
                        <button
                          className="btn btn-danger-outline btn-sm"
                          style={{ padding: '5px 8px', fontSize: '10px' }}
                          onClick={() => removeCommandRow(idx)}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-secondary btn-sm" onClick={addCommandRow}>
                Add Command Row
              </button>
            </div>

            <div className="card-footer-actions">
              <button 
                className="btn btn-primary btn-sm" 
                onClick={saveCommands}
                disabled={loading.commands}
              >
                Save & Hot-Reload
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Live Poll Creation */}
      <span className="category-label">[ ENGAGEMENT MODULE ]</span>
      <div className="panel-card" style={{ marginBottom: '40px' }}>
        <div className="card-title">Launch Live YouTube Poll</div>
        <div className="form-group">
          <label className="form-label">Poll Question</label>
          <input
            type="text"
            className="input-field"
            value={poll.question}
            onChange={(e) => setPoll({ ...poll, question: e.target.value })}
            placeholder='e.g. "Which build to try?"'
          />
        </div>
        <div className="form-group">
          <label className="form-label">Options (2 to 4)</label>
          <div className="options-list">
            {poll.options.map((option, idx) => (
              <div key={idx} className="option-row">
                <input
                  type="text"
                  className="input-field"
                  value={option}
                  onChange={(e) => handlePollOptionChange(idx, e.target.value)}
                  placeholder={`Option ${idx + 1}`}
                />
                <button
                  className="btn btn-danger-outline btn-sm"
                  onClick={() => handleRemovePollOption(idx)}
                  disabled={poll.options.length <= 2}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <button 
            className="btn btn-secondary btn-sm" 
            onClick={handleAddPollOption}
            disabled={poll.options.length >= 4}
          >
            Add option
          </button>
        </div>
        <div className="card-footer-actions">
          <button 
            className="btn btn-success btn-sm" 
            onClick={launchPoll}
            disabled={loading.poll || !status.running}
            title={!status.running ? 'Start the bot first' : ''}
          >
            Launch Poll
          </button>
        </div>
      </div>

      {/* Live Logs */}
      <span className="category-label">[ CONSOLE TELEMETRY ]</span>
      <div className="panel-card">
        <div className="card-title">Live Server Records</div>
        
        {/* Controls */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <div className="filter-badge-row">
            {['ALL', 'INFO', 'WARNING', 'ERROR', 'DEBUG'].map((level) => (
              <span
                key={level}
                className={`filter-badge ${logFilter === level ? `active level-${level}` : ''}`}
                onClick={() => setLogFilter(level)}
              >
                {level}
              </span>
            ))}
          </div>
          
          <div className="terminal-search-box">
            <input
              type="text"
              className="input-field"
              style={{ padding: '6px 12px', fontSize: '12px' }}
              value={logSearch}
              onChange={(e) => setLogSearch(e.target.value)}
              placeholder="Search console logs..."
            />
            {logSearch && (
              <button 
                className="btn btn-secondary btn-sm" 
                style={{ padding: '4px 8px' }}
                onClick={() => setLogSearch('')}
              >
                ✕
              </button>
            )}
          </div>
        </div>

        <div className="terminal-viewer" ref={logViewerRef}>
          {filteredLogs.length === 0 ? (
            <div className="terminal-empty">
              {logs.length === 0 ? 'Connection active. Awaiting log events...' : 'No logs matches filters.'}
            </div>
          ) : (
            filteredLogs.map((log, index) => (
              <div key={index} className={`terminal-line log-level-${log.level || 'INFO'}`}>
                <span className="log-timestamp">[{log.time || '00:00:00'}]</span>
                <span>{log.message}</span>
              </div>
            ))
          )}
        </div>

        <div className="terminal-controls">
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              type="checkbox"
              id="autoscroll-logs-chk"
              checked={autoScrollLogs}
              onChange={(e) => setAutoScrollLogs(e.target.checked)}
              style={{ cursor: 'pointer', width: '14px', height: '14px' }}
            />
            <label htmlFor="autoscroll-logs-chk" style={{ fontSize: '12px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              Auto-scroll events
            </label>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-secondary btn-sm" onClick={clearLogs}>
              Clear Logs
            </button>
            <button 
              className="btn btn-secondary btn-sm" 
              onClick={() => {
                if (logViewerRef.current) {
                  logViewerRef.current.scrollTop = logViewerRef.current.scrollHeight;
                }
              }}
            >
              Scroll to Bottom
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
