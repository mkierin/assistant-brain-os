module.exports = {
  apps: [
    {
      name: 'brain-bot',
      script: 'main.py',
      interpreter: './venv/bin/python',
      watch: false,
      cwd: '/root/assistant-brain-os',
      env: {
        NODE_ENV: 'production',
      },
    },
    {
      name: 'brain-worker',
      script: 'worker.py',
      interpreter: './venv/bin/python',
      instances: 2,
      exec_mode: 'fork',
      watch: false,
      cwd: '/root/assistant-brain-os',
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
