module.exports = {
  apps: [
    {
      name: 'brain-bot',
      script: 'main.py',
      interpreter: 'python',
      watch: false,
      env: {
        NODE_ENV: 'production',
      },
    },
    {
      name: 'brain-worker',
      script: 'worker.py',
      interpreter: 'python',
      instances: 2,
      exec_mode: 'fork',
      watch: false,
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
