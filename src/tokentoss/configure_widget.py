"""Configuration widget for setting up OAuth client credentials in Jupyter notebooks.

Provides a password-safe input widget so credentials are entered at runtime
and never appear in .ipynb source or version control.

Usage:
    from tokentoss import ConfigureWidget
    display(ConfigureWidget())
"""

from __future__ import annotations

import anywidget
import traitlets

from .setup import configure

_ESM = """
function render({ model, el }) {
    const container = document.createElement('div');
    container.className = 'tokentoss-configure';

    // Client ID field
    const idLabel = document.createElement('label');
    idLabel.className = 'tokentoss-configure-label';
    idLabel.textContent = 'Client ID';
    const idInput = document.createElement('input');
    idInput.type = 'text';
    idInput.className = 'tokentoss-configure-input';
    idInput.placeholder = '123456789.apps.googleusercontent.com';

    // Client Secret field
    const secretLabel = document.createElement('label');
    secretLabel.className = 'tokentoss-configure-label';
    secretLabel.textContent = 'Client Secret';
    const secretInput = document.createElement('input');
    secretInput.type = 'password';
    secretInput.className = 'tokentoss-configure-input';
    secretInput.placeholder = 'GOCSPX-...';

    // Advanced (optional) section
    const advancedHeader = document.createElement('div');
    advancedHeader.className = 'tokentoss-configure-advanced-header';
    advancedHeader.innerHTML = '&#9654; Advanced (optional)';
    let advancedOpen = false;

    const advancedContent = document.createElement('div');
    advancedContent.className = 'tokentoss-configure-advanced-content';
    advancedContent.style.display = 'none';

    const projectLabel = document.createElement('label');
    projectLabel.className = 'tokentoss-configure-label';
    projectLabel.textContent = 'Project ID';
    const projectInput = document.createElement('input');
    projectInput.type = 'text';
    projectInput.className = 'tokentoss-configure-input';
    projectInput.placeholder = 'my-gcp-project';

    advancedContent.appendChild(projectLabel);
    advancedContent.appendChild(projectInput);

    advancedHeader.addEventListener('click', () => {
        advancedOpen = !advancedOpen;
        advancedContent.style.display = advancedOpen ? 'block' : 'none';
        advancedHeader.innerHTML = (advancedOpen ? '&#9660;' : '&#9654;') + ' Advanced (optional)';
    });

    // Submit button
    const button = document.createElement('button');
    button.className = 'tokentoss-configure-button';
    button.textContent = 'Configure';

    // Status display
    const statusEl = document.createElement('div');
    statusEl.className = 'tokentoss-configure-status';

    // Assemble DOM
    container.appendChild(idLabel);
    container.appendChild(idInput);
    container.appendChild(secretLabel);
    container.appendChild(secretInput);
    container.appendChild(advancedHeader);
    container.appendChild(advancedContent);
    container.appendChild(button);
    container.appendChild(statusEl);
    el.appendChild(container);

    function updateStatus() {
        const status = model.get('status');
        const configured = model.get('configured');
        statusEl.textContent = status;
        statusEl.className = 'tokentoss-configure-status' +
            (configured ? ' tokentoss-configure-success' : '');
        if (status.startsWith('Error')) {
            statusEl.className = 'tokentoss-configure-status tokentoss-configure-error';
        }
    }

    button.addEventListener('click', () => {
        model.set('client_id', idInput.value);
        model.set('client_secret', secretInput.value);
        model.set('project_id', projectInput.value);
        model.set('_submit', model.get('_submit') + 1);
        model.save_changes();
    });

    model.on('change:status', updateStatus);
    model.on('change:configured', updateStatus);

    updateStatus();
}

export default { render };
"""

_CSS = """
.tokentoss-configure {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 16px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #ffffff;
    max-width: 400px;
}

.tokentoss-configure-label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    margin-bottom: 4px;
    margin-top: 12px;
}

.tokentoss-configure-label:first-child {
    margin-top: 0;
}

.tokentoss-configure-input {
    width: 100%;
    padding: 8px 12px;
    font-size: 13px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    box-sizing: border-box;
}

.tokentoss-configure-input:focus {
    outline: none;
    border-color: #4285f4;
    box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
}

.tokentoss-configure-button {
    margin-top: 16px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
    color: #ffffff;
    background: #4285f4;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;
}

.tokentoss-configure-button:hover {
    background: #3574e2;
}

.tokentoss-configure-status {
    margin-top: 12px;
    font-size: 13px;
    color: #6b7280;
}

.tokentoss-configure-success {
    color: #059669;
}

.tokentoss-configure-error {
    color: #dc2626;
}

.tokentoss-configure-advanced-header {
    margin-top: 16px;
    font-size: 13px;
    color: #6b7280;
    cursor: pointer;
    user-select: none;
}

.tokentoss-configure-advanced-header:hover {
    color: #374151;
}

.tokentoss-configure-advanced-content {
    margin-top: 4px;
}
"""


class ConfigureWidget(anywidget.AnyWidget):
    """Widget for configuring OAuth client credentials in Jupyter notebooks.

    Provides password-style input fields for client_id and client_secret,
    so credentials are entered at runtime and never appear in notebook source.

    Example:
        from tokentoss import ConfigureWidget
        display(ConfigureWidget())
        # Enter credentials and click Configure
    """

    client_id = traitlets.Unicode("").tag(sync=True)
    client_secret = traitlets.Unicode("").tag(sync=True)
    status = traitlets.Unicode("Enter credentials").tag(sync=True)
    configured = traitlets.Bool(False).tag(sync=True)
    _submit = traitlets.Int(0).tag(sync=True)

    _esm = _ESM
    _css = _CSS

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.observe(self._on_submit, names=["_submit"])

    def _on_submit(self, change):
        """Handle submit button press."""
        if change["new"] == 0:
            return

        client_id = self.client_id.strip()
        client_secret = self.client_secret.strip()

        if not client_id or not client_secret:
            self.status = "Error: both Client ID and Client Secret are required"
            self.configured = False
            return

        try:
            path = configure(client_id=client_id, client_secret=client_secret)
            self.status = f"Configured! Saved to {path}"
            self.configured = True
        except Exception as e:
            self.status = f"Error: {e}"
            self.configured = False
