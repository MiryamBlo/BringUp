#!/usr/bin/env python3
"""Build Automation Web GUI"""
from flask import Flask, render_template_string, jsonify, request
import subprocess, os, threading, queue, signal, sys, shutil, shlex
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
script_dir = Path(__file__).parent.absolute()
build_script = script_dir / "build_automation.sh"
config_file = script_dir / "build_config.cfg"
current_process = None
output_queue = queue.Queue()
is_running = False
current_command = ''
current_command_plain = ''

# Simple ANSI color helper for log messages
ANSI_CODES = {
    'reset': '\x1b[0m',
    'bold': '\x1b[1m',
    'black': '\x1b[30m',
    'red': '\x1b[31m',
    'green': '\x1b[32m',
    'yellow': '\x1b[33m',
    'blue': '\x1b[34m',
    'magenta': '\x1b[35m',
    'cyan': '\x1b[36m',
    'white': '\x1b[37m',
}

def color_text(text, color):
    code = ANSI_CODES.get(color, '')
    reset = ANSI_CODES['reset'] if code else ''
    return f"{code}{text}{reset}"

def log_shell_command(cmd_str):
    """Set current command (plain and colored) and append an execution log entry."""
    global current_command, current_command_plain
    current_command_plain = cmd_str
    current_command = color_text(cmd_str, 'yellow')
    # Add a clear, prefixed line to the execution log
    output_queue.put(color_text(f"→ {cmd_str}", 'yellow'))

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<title>Build Automation GUI</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px}
.container{max-width:1200px;margin:0 auto;background:white;border-radius:15px;box-shadow:0 20px 60px rgba(0,0,0,0.3);overflow:hidden}
.header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:30px;text-align:center}
.header h1{font-size:2.5em;margin-bottom:10px}
.config-section{padding:25px;background:#f8f9fa;border-bottom:2px solid #e9ecef}
.config-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}
.btn-edit-config{padding:10px 20px;background:#667eea;color:white;border:none;border-radius:5px;cursor:pointer}
.config-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px}
.config-item{display:flex;flex-direction:column}
.config-label{font-weight:600;color:#6c757d;font-size:0.9em;margin-bottom:5px}
.config-value{color:#212529;font-family:monospace;background:white;padding:8px 12px;border-radius:5px;border:1px solid #dee2e6}
.section{padding:25px}
.section-title{font-size:1.2em;font-weight:bold;color:#495057;margin-bottom:20px;padding-bottom:10px;border-bottom:2px solid #667eea}
.button-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:20px}
.btn{padding:15px 25px;font-size:1em;font-weight:600;border:none;border-radius:8px;cursor:pointer;transition:all 0.3s ease;box-shadow:0 4px 6px rgba(0,0,0,0.1);color:white}
.btn:hover{transform:translateY(-2px);box-shadow:0 6px 12px rgba(0,0,0,0.15)}
.btn:disabled{opacity:0.6;cursor:not-allowed;transform:none}
.btn-update{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)}
.btn-build{background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%)}
.btn-generate{background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%)}
.btn-deploy{background:linear-gradient(135deg,#43e97b 0%,#38f9d7 100%)}
.btn-install{background:linear-gradient(135deg,#fa709a 0%,#fee140 100%)}
.btn-combined{background:linear-gradient(135deg,#30cfd0 0%,#330867 100%)}
.btn-all{background:linear-gradient(135deg,#ff0844 0%,#ffb199 100%);font-size:1.1em}
.log-section{background:#1e1e1e;color:#d4d4d4;padding:20px;border-radius:8px;height:400px;overflow-y:auto;font-family:monospace;font-size:0.9em;line-height:1.5}
.log-line{margin:2px 0;word-wrap:break-word;white-space:pre-wrap}
.log-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.current-command{font-family:monospace;font-size:0.9em;padding:6px 10px;border-radius:6px;background:#1e1e1e;color:#ffc107;max-width:60%;overflow:auto;white-space:nowrap;text-overflow:ellipsis;margin-left:15px} 
.btn-clear{padding:8px 16px;background:#dc3545;color:white;border:none;border-radius:5px;cursor:pointer}
.status-bar{background:#343a40;color:white;padding:15px 25px;display:flex;justify-content:space-between;align-items:center}
.status-indicator{display:flex;align-items:center;gap:10px}
.status-dot{width:12px;height:12px;border-radius:50%;background:#28a745}
.status-dot.running{background:#ffc107;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.spinner{display:none;width:20px;height:20px;border:3px solid rgba(255,255,255,0.3);border-top:3px solid white;border-radius:50%;animation:spin 1s linear infinite}
.spinner.active{display:inline-block}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
.modal{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center}
.modal.active{display:flex}
.modal-content{background:white;padding:30px;border-radius:10px;max-width:500px;text-align:center}
.modal-content h2{margin-bottom:15px}
.modal-content p{margin-bottom:25px}
.modal-buttons{display:flex;gap:10px;justify-content:center}
.modal-btn{padding:10px 30px;border:none;border-radius:5px;cursor:pointer;font-size:1em;font-weight:600}
.modal-btn-yes{background:#28a745;color:white}
.modal-btn-no{background:#6c757d;color:white}
.edit-modal{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;overflow-y:auto;padding:20px}
.edit-modal.active{display:flex}
.edit-modal-content{background:white;padding:30px;border-radius:10px;max-width:700px;width:100%;max-height:90vh;overflow-y:auto}
.form-group{margin-bottom:20px}
.form-label{display:block;font-weight:600;margin-bottom:8px}
.form-input{width:100%;padding:10px;border:2px solid #dee2e6;border-radius:5px;font-family:monospace}
.edit-buttons{display:flex;gap:10px;justify-content:flex-end;margin-top:25px}
.btn-save{padding:12px 30px;background:#28a745;color:white;border:none;border-radius:5px;cursor:pointer}
.btn-cancel{padding:12px 30px;background:#6c757d;color:white;border:none;border-radius:5px;cursor:pointer}
.btn-stop{display:none;padding:12px 30px;background:#dc3545;color:white;border:none;border-radius:5px;cursor:pointer;animation:pulse-red 1.5s infinite}
.btn-stop.active{display:inline-block}
@keyframes pulse-red{0%,100%{opacity:1}50%{opacity:0.7}}
.status-actions{display:flex;gap:10px;align-items:center}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>⚙️ Build Automation Control Panel</h1>
<p>Manage your build, generate, deploy, and install workflows</p>
</div>
<div class="config-section">
<div class="config-header">
<div class="config-title">📋 Configuration</div>
<button class="btn-edit-config" onclick="openConfigEditor()">✏️ Edit Config</button>
</div>
<div class="config-grid">
<div class="config-item">
<div class="config-label">Config File</div>
<div class="config-value" id="config-file">{{ config_file }}</div>
</div>
<div class="config-item">
<div class="config-label">Project Name</div>
<div class="config-value" id="project-name">{{ project_name }}</div>
</div>
<div class="config-item">
<div class="config-label">Build Type</div>
<div class="config-value" id="build-type">{{ build_type }}</div>
</div>
<div class="config-item">
<div class="config-label">Zero Config Path</div>
<div class="config-value" id="zero-config-path">{{ zero_config_path }}</div>
</div>
</div>
</div>
<div class="section">
<div class="section-title">🔧 Individual Operations</div>
<div class="button-grid">
<button class="btn btn-update" onclick="executeCommand('-u','Update APP_ROOT')">📝 Update APP_ROOT</button>
<button class="btn btn-build" onclick="executeCommand('-b','Build Project')">🔨 Build Project</button>
<button class="btn btn-generate" onclick="executeCommand('-g','Generate Package')">📦 Generate Package</button>
<button class="btn btn-deploy" onclick="executeCommand('-d','Deploy to Setup')">🚀 Deploy to Setup</button>
<button class="btn btn-install" onclick="executeCommand('-i','Install on Setup')">⚡ Install on Setup</button>
</div>
</div>
<div class="section">
<div class="section-title">🌱 Environment Setup</div>
<div class="button-grid">
<button class="btn btn-update" onclick="openEnvCreator()">🔧 Create Environment</button>
</div>
</div>
<div class="section">
<div class="section-title">🔗 Combined Operations</div>
<div class="button-grid">
<button class="btn btn-combined" onclick="executeCommand('-b -g','Build + Generate')">Build + Generate</button>
<button class="btn btn-combined" onclick="executeCommand('-g -d','Generate + Deploy')">Generate + Deploy</button>
<button class="btn btn-combined" onclick="executeCommand('-d -i','Deploy + Install')">Deploy + Install</button>
<button class="btn btn-combined" onclick="executeCommand('-u -b -g','Update + Build + Generate')">Update + Build + Generate</button>
<button class="btn btn-all" onclick="executeCommand('-a','Execute All Steps')">⚡ Execute All Steps</button>
</div>
</div>
<div class="section">
<div class="log-header">
<div class="section-title" style="margin:0;border:0">📊 Execution Log</div>
<div id="current-command" class="current-command" title=""></div>
<button class="btn-clear" onclick="clearLog()">Clear Log</button>
</div> 
<div class="log-section" id="log-output"></div>
</div>
<div class="status-bar">
<div class="status-indicator">
<div class="status-dot" id="status-dot"></div>
<span id="status-text">Ready</span>
</div>
<div class="status-actions">
<button class="btn-stop" id="btn-stop" onclick="stopExecution()">⏹ Stop</button>
<div class="spinner" id="spinner"></div>
</div>
</div>
</div>
<div class="modal" id="confirm-modal">
<div class="modal-content">
<h2>Confirm Action</h2>
<p id="confirm-message"></p>
<div class="modal-buttons">
<button class="modal-btn modal-btn-yes" onclick="confirmYes()">Yes, Execute</button>
<button class="modal-btn modal-btn-no" onclick="confirmNo()">Cancel</button>
</div>
</div>
</div>
<div class="edit-modal" id="edit-modal">
<div class="edit-modal-content">
<h2>✏️ Edit Configuration</h2>
<form id="config-form">
<div class="form-group">
<label class="form-label">APP_ROOT</label>
<input type="text" class="form-input" id="edit-app-root">
</div>
<div class="form-group">
<label class="form-label">PROJECT_NAME</label>
<input type="text" class="form-input" id="edit-project-name">
</div>
<div class="form-group">
<label class="form-label">SETUP_NAME</label>
<input type="text" class="form-input" id="edit-setup-name">
</div>
<div class="form-group">
<label class="form-label">ENV_PATH</label>
<input type="text" class="form-input" id="edit-env-path">
</div>
<div class="form-group"><label class="form-label">Zero Config Path</label>
<input type="text" class="form-input" id="edit-zero-config-path">
</div>
<div class="form-group"><label class="form-label">BUILD_TYPE</label>
<select class="form-input" id="edit-build-type">
<option value="HW">HW</option>
<option value="SW">SW</option>
</select>
</div>
<div class="form-group">
<label class="form-label">OUTPUT_BASE</label>
<input type="text" class="form-input" id="edit-output-base">
</div>
<div class="form-group">
<label class="form-label">AVPC_IP</label>
<input type="text" class="form-input" id="edit-avpc-ip">
</div>
<div class="form-group">
<label class="form-label">AVPC_PASSWORD</label>
<input type="password" class="form-input" id="edit-avpc-password">
</div>
<div class="edit-buttons">
<button type="button" class="btn-cancel" onclick="closeConfigEditor()">Cancel</button>
<button type="button" class="btn-save" onclick="saveConfig()">💾 Save</button>
</div>
</form>
</div>
</div>
<div class="edit-modal" id="env-creator-modal">
<div class="edit-modal-content">
<h2>🌱 Create Environment</h2>
<p style="margin-bottom:20px">Configure environment creation:</p>
<div class="form-group">
<label class="form-label">Destination Path</label>
<input type="text" class="form-input" id="env-dest-path" placeholder="/path/to/destination" value="">
</div>
<p style="margin-bottom:15px;font-weight:600">Select environment type:</p>
<div class="button-grid">
<button class="btn btn-update" onclick="createEnvironment('AVM')">📦 AVM</button>
<button class="btn btn-generate" onclick="createEnvironment('Bundle')">📦 Bundle</button>
</div>
<div style="margin-top:20px">
<button type="button" class="btn-cancel" onclick="closeEnvCreator()">Cancel</button>
</div>
</div>
</div>
<script>
let pendingCommand = null;
let pendingDescription = null;
let logUpdateInterval = null;

function executeCommand(options, description) {
    pendingCommand = options;
    pendingDescription = description;
    document.getElementById('confirm-message').textContent = 'Are you sure you want to execute: ' + description + '?';
    document.getElementById('confirm-modal').classList.add('active');
}

function confirmNo() {
    document.getElementById('confirm-modal').classList.remove('active');
    pendingCommand = null;
    pendingDescription = null;
}

function confirmYes() {
    document.getElementById('confirm-modal').classList.remove('active');
    if (pendingCommand) {
        runCommand(pendingCommand, pendingDescription);
    }
}

function runCommand(options, description) {
    setStatus('running', 'Executing: ' + description + '...');
    disableButtons(true);
    showStopButton(true);
    
    fetch('/execute', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({options: options, description: description})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            logUpdateInterval = setInterval(updateLog, 500);
        } else {
            addLog('Error: ' + data.message);
            setStatus('ready', 'Ready');
            disableButtons(false);
        }
    });
}

function updateLog() {
    fetch('/get_output')
    .then(r => r.json())
    .then(data => {
        if (data.output) {
            data.output.forEach(line => addLog(line));
        }
        // Render the current command in the Execution Log header (ANSI -> HTML)
        try {
            const cmdEl = document.getElementById('current-command');
            const cmdText = data.current_command || '';
            // Hide the element if empty (no visible command), otherwise show it
            if (!cmdText || cmdText.trim() === '') {
                cmdEl.style.display = 'none';
                cmdEl.innerHTML = '';
                cmdEl.title = '';
            } else {
                cmdEl.style.display = '';
                cmdEl.innerHTML = ansiToHtml(cmdText);
                cmdEl.title = data.current_command_plain || '';
            }
        } catch (e) {}
        if (data.finished) {
            clearInterval(logUpdateInterval);
            setStatus('ready', data.status);
            disableButtons(false);
            showStopButton(false);
            if (data.success) {
                alert('✓ ' + data.description + ' completed successfully!');
            } else if (data.stopped) {
                alert('⏹ ' + data.description + ' was stopped by user.');
            } else {
                alert('✗ ' + data.description + ' failed!');
            }
        }
    });
}

function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function ansiToHtml(text) {
    // Normalize common escaped forms to actual ESC character so regex matches reliably
    try {
        // Replace literal backslash-x sequences (\x1b) and backslash-u sequences (\u001b) with an actual ESC
        text = text.replace(/\\x1b/g, '\x1b').replace(/\\u001b/g, '\x1b');
        // Some inputs may include the ESC char as the visible glyph '\u001b' already, leave as-is
    } catch (e) {}

    text = escapeHtml(text);

    // Replace actual ESC sequences like \x1b[0;34m or \u001b[0;34m
    const ansiRegex = /\x1b\[([0-9;]+)m/g;
    text = text.replace(ansiRegex, function(_, codes) {
        let parts = codes.split(';').map(Number);
        // Treat 0 as reset; if it's the only code, close span; otherwise remove it and continue
        if (parts.length === 1 && parts[0] === 0) return '</span>';
        if (parts.includes(0)) parts = parts.filter(p => p !== 0);
        let styles = [];
        parts.forEach(code => {
            if (code === 1) styles.push('font-weight:bold');
            else if (code >= 30 && code <= 37) {
                const cols = ['black','red','green','yellow','blue','magenta','cyan','white'];
                styles.push('color:' + cols[code-30]);
            } else if (code >= 90 && code <= 97) {
                const cols = ['grey','red','green','yellow','blue','magenta','cyan','white'];
                styles.push('color:' + cols[code-90]);
            }
        });
        if (styles.length) return '<span style="' + styles.join(';') + '">';
        return '';
    });
    return text;
}

function addLog(msg) {
    const logDiv = document.getElementById('log-output');
    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = ansiToHtml(msg);
    logDiv.appendChild(line);
    logDiv.scrollTop = logDiv.scrollHeight;
}

function clearLog() {
    document.getElementById('log-output').innerHTML = '';
}

function setStatus(state, text) {
    const dot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const spinner = document.getElementById('spinner');
    statusText.textContent = text;
    if (state === 'running') {
        dot.classList.add('running');
        spinner.classList.add('active');
    } else {
        dot.classList.remove('running');
        spinner.classList.remove('active');
    }
}

function disableButtons(disabled) {
    document.querySelectorAll('.btn, .btn-edit-config').forEach(btn => btn.disabled = disabled);
}

function showStopButton(show) {
    const stopBtn = document.getElementById('btn-stop');
    if (show) {
        stopBtn.classList.add('active');
    } else {
        stopBtn.classList.remove('active');
    }
}

function stopExecution() {
    if (!confirm('Are you sure you want to stop the current execution?')) {
        return;
    }
    addLog('');
    addLog('⏹ Stop requested by user...');
    
    fetch('/stop_execution', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            addLog('⏹ Stop signal sent successfully');
        } else {
            addLog('Error stopping execution: ' + data.message);
        }
    })
    .catch(err => addLog('Error: ' + err));
}

function openConfigEditor() {
    fetch('/get_full_config')
    .then(r => r.json())
    .then(data => {
        document.getElementById('edit-app-root').value = data.APP_ROOT || '';
        document.getElementById('edit-project-name').value = data.PROJECT_NAME || '';
        document.getElementById('edit-setup-name').value = data.SETUP_NAME || '';
        document.getElementById('edit-env-path').value = data.ENV_PATH || '';
        document.getElementById('edit-zero-config-path').value = data.ZERO_CONFIG_PATH || '';
        document.getElementById('edit-build-type').value = data.BUILD_TYPE || 'HW';
        document.getElementById('edit-output-base').value = data.OUTPUT_BASE || '';
        document.getElementById('edit-avpc-ip').value = data.AVPC_IP || '';
        document.getElementById('edit-avpc-password').value = data.AVPC_PASSWORD || '';
        document.getElementById('edit-modal').classList.add('active');
    })
    .catch(err => alert('Error loading configuration: ' + err));
}

function closeConfigEditor() {
    document.getElementById('edit-modal').classList.remove('active');
}

function saveConfig() {
    const formData = {
        APP_ROOT: document.getElementById('edit-app-root').value,
        PROJECT_NAME: document.getElementById('edit-project-name').value,
        SETUP_NAME: document.getElementById('edit-setup-name').value,
        ENV_PATH: document.getElementById('edit-env-path').value,
        ZERO_CONFIG_PATH: document.getElementById('edit-zero-config-path').value,
        BUILD_TYPE: document.getElementById('edit-build-type').value,
        OUTPUT_BASE: document.getElementById('edit-output-base').value,
        AVPC_IP: document.getElementById('edit-avpc-ip').value,
        AVPC_PASSWORD: document.getElementById('edit-avpc-password').value
    };
    
    if (!confirm('Save configuration changes?')) {
        return;
    }
    
    fetch('/save_config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✓ Configuration saved successfully!');
            closeConfigEditor();
            refreshConfig();
        } else {
            alert('Error saving configuration: ' + data.message);
        }
    })
    .catch(err => alert('Error saving configuration: ' + err));
}

function refreshConfig() {
    fetch('/get_config')
    .then(r => r.json())
    .then(config => {
        document.getElementById('config-file').textContent = config.config_file;
        document.getElementById('project-name').textContent = config.project_name;
        document.getElementById('build-type').textContent = config.build_type;
        document.getElementById('zero-config-path').textContent = config.zero_config_path || '';
    });
}

function openEnvCreator() {
    document.getElementById('env-creator-modal').classList.add('active');
}

function closeEnvCreator() {
    document.getElementById('env-creator-modal').classList.remove('active');
}

function createEnvironment(envType) {
    const destPath = document.getElementById('env-dest-path').value.trim();
    
    if (!destPath) {
        alert('Please enter a destination path');
        return;
    }
    
    closeEnvCreator();
    setStatus('running', 'Creating ' + envType + ' environment...');
    disableButtons(true);
    showStopButton(true);
    
    fetch('/create_environment', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({env_type: envType, dest_path: destPath})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            logUpdateInterval = setInterval(updateLog, 500);
        } else {
            addLog('Error: ' + data.message);
            setStatus('ready', 'Ready');
            disableButtons(false);
            showStopButton(false);
        }
    });
}

setInterval(() => {
    fetch('/get_config')
    .then(r => r.json())
    .then(data => {
        document.getElementById('config-file').textContent = data.config_file;
        document.getElementById('project-name').textContent = data.project_name;
        document.getElementById('build-type').textContent = data.build_type;
        document.getElementById('zero-config-path').textContent = data.zero_config_path || '';
    });
}, 30000);
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, **load_config())

@app.route('/get_config')
def get_config():
    return jsonify(load_config())

@app.route('/get_full_config')
def get_full_config():
    config_data = {}
    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config_data[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error loading config: {e}")
    return jsonify(config_data)


@app.route('/save_config', methods=['POST'])
def save_config_route():
    try:
        data = request.json
        if config_file.exists():
            backup_file = config_file.parent / f"{config_file.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(config_file, backup_file)
        
        with open(config_file, 'w') as f:
            f.write("# Build Configuration File\n\n")
            for key in ['APP_ROOT', 'PROJECT_NAME', 'SETUP_NAME', 'ENV_PATH', 'ZERO_CONFIG_PATH', 'BUILD_TYPE', 'OUTPUT_BASE', 'AVPC_IP', 'AVPC_PASSWORD']:
                f.write(f"{key}={data.get(key, '')}\n\n")
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/execute', methods=['POST'])
def execute():
    global current_process, is_running, output_queue
    if is_running:
        return jsonify({'success': False, 'message': 'Another command is already running'})
    
    data = request.json
    while not output_queue.empty():
        output_queue.get()
    
    thread = threading.Thread(target=run_command, args=(data.get('options', ''), data.get('description', '')))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True})

@app.route('/create_environment', methods=['POST'])
def create_environment():
    global current_process, is_running, output_queue
    if is_running:
        return jsonify({'success': False, 'message': 'Another command is already running'})
    
    data = request.json
    env_type = data.get('env_type', '')
    dest_path = data.get('dest_path', '')
    
    while not output_queue.empty():
        output_queue.get()
    
    thread = threading.Thread(target=run_env_creation, args=(env_type, dest_path))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True})

@app.route('/get_output')
def get_output():
    global is_running
    output_lines = []
    while not output_queue.empty():
        output_lines.append(output_queue.get())
    
    stopped = False
    if current_process and hasattr(current_process, 'stopped'):
        stopped = current_process.stopped
    
    return jsonify({
        'output': output_lines,
        'finished': not is_running,
        'success': getattr(current_process, 'returncode', 0) == 0 if current_process else False,
        'stopped': stopped,
        'status': 'Ready' if not is_running else 'Running...',
        'description': getattr(current_process, 'description', ''),
        'current_command': current_command,
        'current_command_plain': current_command_plain
    })

@app.route('/stop_execution', methods=['POST'])
def stop_execution():
    global current_process, is_running
    try:
        if current_process and is_running:
            output_queue.put('')
            output_queue.put('⏹ Stopping execution...')
            current_process.stopped = True
            current_process.terminate()
            import time
            time.sleep(1)
            if current_process.poll() is None:
                current_process.kill()
            output_queue.put('⏹ Execution stopped by user')
            return jsonify({'success': True, 'message': 'Execution stopped'})
        else:
            return jsonify({'success': False, 'message': 'No running execution to stop'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def load_config():
    config_data = {
        'config_file': str(config_file.name),
        'project_name': 'N/A',
        'build_type': 'N/A',
        'zero_config_path': ''
    }
    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'PROJECT_NAME':
                            config_data['project_name'] = value
                        elif key == 'BUILD_TYPE':
                            config_data['build_type'] = value
                        elif key == 'ZERO_CONFIG_PATH':
                            config_data['zero_config_path'] = value
    except Exception as e:
        print(f"Error loading config: {e}")
    return config_data


def read_full_config_dict():
    data = {}
    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        data[key.strip()] = value.strip()
    except Exception:
        pass
    return data


def write_full_config_dict(conf):
    try:
        if config_file.exists():
            backup_file = config_file.parent / f"{config_file.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(config_file, backup_file)
        with open(config_file, 'w') as f:
            f.write("# Build Configuration File\n\n")
            for key in ['APP_ROOT', 'PROJECT_NAME', 'SETUP_NAME', 'ENV_PATH', 'ZERO_CONFIG_PATH', 'BUILD_TYPE', 'OUTPUT_BASE', 'AVPC_IP', 'AVPC_PASSWORD']:
                f.write(f"{key}={conf.get(key, '')}\n\n")
    except Exception:
        pass


def run_command(options, description):
    global current_process, is_running, current_command, current_command_plain
    is_running = True
    output_queue.put("")
    output_queue.put("=" * 60)
    output_queue.put(color_text(f"Executing: {description}", 'cyan'))
    output_queue.put(color_text(f"Config: {config_file}", 'blue'))
    cmd = [str(build_script), "-c", str(config_file)] + options.split()
    cmd_str = ' '.join(shlex.quote(x) for x in cmd)
    # log and display the exact shell command
    log_shell_command(cmd_str)
    output_queue.put(color_text(f"CWD: {os.getcwd()}", 'magenta'))
    output_queue.put("=" * 60)
    output_queue.put("")
    
    try:
        current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        current_process.description = description
        current_process.stopped = False
        
        for line in current_process.stdout:
            # Pass through subprocess output (may contain its own ANSI colors)
            output_queue.put(line.rstrip())
            if hasattr(current_process, 'stopped') and current_process.stopped:
                break
        
        current_process.wait()
        
        if hasattr(current_process, 'stopped') and current_process.stopped:
            output_queue.put("")
            output_queue.put(color_text(f"⏹ {description} was stopped by user", 'yellow'))
            output_queue.put("")
        elif current_process.returncode == 0:
            output_queue.put("")
            output_queue.put(color_text(f"✓ {description} completed successfully!", 'green'))
            output_queue.put("")
            # If this was a generate invocation and it succeeded, try to read the canonical bkc path
            if '-g' in options.split():
                try:
                    conf = read_full_config_dict()
                    env_path = conf.get('ENV_PATH') or conf.get('env_path') or ''
                    if env_path:
                        last_bkc = Path(env_path) / '.last_bkc_path'
                        if last_bkc.exists():
                            bkc_path = last_bkc.read_text().strip()
                            if bkc_path:
                                conf['ZERO_CONFIG_PATH'] = bkc_path
                                write_full_config_dict(conf)
                                output_queue.put(color_text(f"Saved ZERO_CONFIG_PATH: {bkc_path}", 'green'))
                except Exception as e:
                    output_queue.put(color_text(f"✗ Failed to save ZERO_CONFIG_PATH: {str(e)}", 'red'))
                output_queue.put("")
        else:
            output_queue.put("")
            output_queue.put(color_text(f"✗ {description} failed with exit code {current_process.returncode}", 'red'))
            output_queue.put("")
    except Exception as e:
        output_queue.put("")
        output_queue.put(color_text(f"✗ Error: {str(e)}", 'red'))
        output_queue.put("")
        if current_process:
            current_process.returncode = 1
    finally:
        # clear current command when done
        current_command = ''
        current_command_plain = ''
        is_running = False

def run_env_creation(env_type, dest_path):
    global current_process, is_running, current_command, current_command_plain
    is_running = True
    output_queue.put("")
    output_queue.put("=" * 60)
    output_queue.put(f"Creating {env_type} Environment")
    output_queue.put("=" * 60)
    output_queue.put("")
    
    try:
        # Validate destination path
        if not dest_path:
            output_queue.put("✗ Destination path is required")
            is_running = False
            return
        
        dest_root = Path(dest_path).expanduser().resolve()
        
        # Create destination root if it doesn't exist
        if not dest_root.exists():
            cmd_mkdir_root = 'mkdir -p ' + shlex.quote(str(dest_root))
            log_shell_command(cmd_mkdir_root)
            output_queue.put(f"Creating destination directory: {dest_root}")
            dest_root.mkdir(parents=True, exist_ok=True)
        
        # Build a dated directory name inside destination: <env_type>-YYYYMMDD_HHMMSS
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_dir_name = f"{env_type}-{timestamp}"
        i = 0
        created = False
        clone_path = None
        while not created:
            candidate = dest_root / (base_dir_name if i == 0 else f"{base_dir_name}-{i}")
            cmd_mkdir_clone = 'mkdir -p ' + shlex.quote(str(candidate))
            # set & log the current command
            log_shell_command(cmd_mkdir_clone)
            try:
                candidate.mkdir(parents=True, exist_ok=False)
                clone_path = candidate
                created = True
                output_queue.put(f"Created environment directory: {clone_path}")
            except FileExistsError:
                # directory exists — try a new suffix
                i += 1
                continue

        # Decide which repo and branch to clone based on env_type
        if env_type == 'AVM':
            repo_url = 'git@gitlab.mobileye.com:av-psw/bundle.git'
            branch = 'gateway/av_master'
        elif env_type == 'Bundle':
            repo_url = 'git@gitlab.mobileye.com:bundle/bundle.git'
            branch = 'bundle_master'
        else:
            output_queue.put(f"✗ Unknown environment type: {env_type}")
            is_running = False
            return

        output_queue.put(f"Repository: {repo_url}")
        output_queue.put(f"Branch: {branch}")
        output_queue.put(f"Destination: {clone_path}")
        output_queue.put("")
        output_queue.put("Starting git clone with submodules into the new directory...")
        output_queue.put("")

        # git clone --recurse-submodules -j30 <repo> -b <branch> .
        cmd = ['git', 'clone', '--recurse-submodules', '-j30', repo_url, '-b', branch, '.']
        cmd_str = ' '.join(shlex.quote(x) for x in cmd)
        log_shell_command(cmd_str)
        output_queue.put(color_text(f"CWD: {clone_path}", 'magenta'))
        
        current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            cwd=str(clone_path)
        )
        current_process.description = f"Create {env_type} Environment"
        current_process.stopped = False
        
        for line in current_process.stdout:
            output_queue.put(line.rstrip())
            if hasattr(current_process, 'stopped') and current_process.stopped:
                break
        
        current_process.wait()
        
        if hasattr(current_process, 'stopped') and current_process.stopped:
            output_queue.put("")
            output_queue.put(f"⏹ Environment creation was stopped by user")
            output_queue.put("")
        elif current_process.returncode == 0:
            output_queue.put("")
            output_queue.put(f"✓ {env_type} environment created successfully!")
            output_queue.put(f"Location: {clone_path}")
            output_queue.put("")
        else:
            output_queue.put("")
            output_queue.put(f"✗ Environment creation failed with exit code {current_process.returncode}")
            output_queue.put("")
    except Exception as e:
        output_queue.put("")
        output_queue.put(f"✗ Error: {str(e)}")
        output_queue.put("")
        if current_process:
            current_process.returncode = 1
    finally:
        # clear current command when done
        current_command = ''
        current_command_plain = ''
        is_running = False

def signal_handler(sig, frame):
    print('\n\nShutting down server...')
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    print("\n" + "=" * 60)
    print("Build Automation Web GUI")
    print("=" * 60)
    print(f"\nServer starting...")
    print(f"Build script: {build_script}")
    print(f"Config file: {config_file}")
    print("\n" + "=" * 60)
    print("Open your browser and navigate to:")
    print("\n  http://localhost:8080")
    print("\n  Or if accessing remotely:")
    print(f"  http://{os.uname()[1]}:8080")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
