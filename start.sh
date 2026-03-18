#!/bin/bash
cd /workspace/AutoResearch-MRL
source /workspace/venv/bin/activate
export MUJOCO_GL=egl
export WANDB_MODE=disabled

# Start sync loop in background
(while true; do python sync_results.py >> sync.log 2>&1; sleep 300; done) &
SYNC_PID=$!
echo "Sync loop PID: $SYNC_PID"

# Start run loop (foreground, logged)
echo "Starting run_loop.py at $(date)"
python run_loop.py --resume >> run_loop_output.log 2>&1 &
RUN_PID=$!
echo "Run loop PID: $RUN_PID"

echo "$SYNC_PID" > /tmp/sync.pid
echo "$RUN_PID" > /tmp/run.pid
echo "Both processes started. Check run_loop_output.log for progress."
