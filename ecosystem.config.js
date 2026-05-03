module.exports = {
    apps:[{
        name: "HFT_Momentum_Bot",
        script: "main.py",
        interpreter: "./venv/Scripts/python.exe",
        autorestart: true,
        watch: false,
        max_restarts: 10,
        min_uptime: "60s",
        log_date_format: "YYYY-MM-DD HH:mm:ss Z",
        merge_logs: true,
        env: { PYTHONUNBUFFERED: "1" }
    }]
};
