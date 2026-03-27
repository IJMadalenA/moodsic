# Django Management Commands - Moodsic RL System

## Overview

Moodsic now includes 5 powerful Django management commands for streamlined workflow automation. These commands handle model training, evaluation, data collection, and Spotify synchronization.

## Commands Reference

### 1. train_agent - RL Model Training

**Purpose**: Trains the DQN agent using interaction data from your database.

```bash
python manage.py train_agent [OPTIONS]
```

**Options**:
- `--episodes NUM` (default: 50) - Number of training episodes
- `--days NUM` (default: 30) - Days of historical data to use
- `--batch-size NUM` (default: 64) - Training batch size
- `--save` - Save trained model to disk
- `--visualize` - Generate training history graphs
- `--verbose` - Show detailed logs

**Examples**:
```bash
# Quick training test
python manage.py train_agent --episodes 5

# Full training with data persistence
python manage.py train_agent --episodes 100 --days 30 --batch-size 64 --save

# Training with visualization
python manage.py train_agent --episodes 50 --save --visualize --verbose
```

**Output**:
- Model: `ml/models/dqn_agent_YYYYMMDD_HHMMSS.h5`
- Logs: `ml/logs/training_YYYYMMDD_HHMMSS.json`
- Graphs: `ml/logs/training_history_*.png` (if --visualize)

---

### 2. evaluate_model - Model Performance Evaluation

**Purpose**: Evaluates a trained model on test interactions and generates recommendations.

```bash
python manage.py evaluate_model --model-path PATH [OPTIONS]
```

**Options**:
- `--model-path PATH` (REQUIRED) - Path to the saved HDF5 model
- `--test-days NUM` (default: 7) - Recent days of interactions to test on
- `--show-recommendations` - Display top-10 track recommendations
- `--verbose` - Show detailed logs

**Examples**:
```bash
# Evaluate with specific model
python manage.py evaluate_model --model-path ml/models/dqn_agent_20260325_225939.h5

# Evaluate and get recommendations
python manage.py evaluate_model --model-path ml/models/dqn_agent_20260325_225939.h5 --show-recommendations

# Full diagnostic
python manage.py evaluate_model --model-path ml/models/model.h5 --test-days 14 --show-recommendations --verbose
```

**Output**:
- Accuracy metrics
- Mean reward score
- Top-10 recommended tracks
- Performance statistics

---

### 3. collect_interactions - Data Collection & Analytics

**Purpose**: Collects, processes, and analyzes user interactions from the database.

```bash
python manage.py collect_interactions [OPTIONS]
```

**Options**:
- `--days NUM` (default: 7) - Number of days to look back
- `--user-id ID` - Specific user to analyze (optional)
- `--generate-report` - Save detailed report to file
- `--save-session` - Group interactions into a session
- `--verbose` - Show detailed logs

**Examples**:
```bash
# Collect last week interactions
python manage.py collect_interactions --days 7

# Analyze specific user with report
python manage.py collect_interactions --user-id 1 --generate-report --days 30

# Create a session and save stats
python manage.py collect_interactions --save-session --generate-report

# Verbose output
python manage.py collect_interactions --days 14 --generate-report --verbose
```

**Output**:
- Interaction statistics (total, complete rate, skip rate)
- User and track metrics
- Top tracks ranking
- Report file: `interaction_report_YYYYMMDD_HHMMSS.txt` (if --generate-report)
- Session ID tracking (if --save-session)

---

### 4. sync_spotify_tracks - Spotify Synchronization

**Purpose**: Synchronizes Spotify tracks with local database.

```bash
python manage.py sync_spotify_tracks [OPTIONS]
```

**Options**:
- `--user-id ID` - Sync specific user's liked tracks (optional)
- `--playlist-id ID` - Sync specific playlist (optional, Spotify format)
- `--limit NUM` (default: 50) - Maximum tracks to sync
- `--save-all` - Save all found tracks
- `--verbose` - Show detailed logs

**Examples**:
```bash
# Sync trending tracks
python manage.py sync_spotify_tracks --limit 100

# Sync user's liked tracks
python manage.py sync_spotify_tracks --user-id 1 --limit 100

# Sync specific playlist
python manage.py sync_spotify_tracks --playlist-id spotify:playlist:123abc456def

# Full sync with details
python manage.py sync_spotify_tracks --limit 500 --save-all --verbose
```

**Output**:
- Number of tracks found
- New tracks created
- Existing tracks (duplicates)
- Sync completion status

---

### 5. moodsic_help - Command Documentation

**Purpose**: Displays comprehensive help about all available Moodsic commands.

```bash
python manage.py moodsic_help [OPTIONS]
```

**Options**:
- `--command NAME` - Get detailed help for specific command (optional)

**Examples**:
```bash
# Show all commands
python manage.py moodsic_help

# Get help for specific command
python manage.py moodsic_help --command train_agent

# Alternative
python manage.py moodsic_help --command evaluate_model
```

**Output**:
- Complete command list
- Workflow recommendations
- Tips and best practices
- Configuration requirements

---

## Recommended Workflows

### 1. Initial Setup & Training

```bash
# Step 1: Collect initial data
python manage.py collect_interactions --days 30 --save-session

# Step 2: Train the model
python manage.py train_agent --episodes 100 --days 30 --save --visualize

# Step 3: Evaluate performance
python manage.py evaluate_model --model-path ml/models/dqn_agent_20260325_225939.h5 --show-recommendations
```

### 2. Daily Operations

```bash
# Morning: Sync new tracks
python manage.py sync_spotify_tracks --limit 100

# Noon: Collect interactions
python manage.py collect_interactions --days 1

# Evening: Generate recommendations
python manage.py evaluate_model --model-path ml/models/dqn_agent_20260325_225939.h5 --show-recommendations
```

### 3. Model Improvement Loop

```bash
# Collect user feedback
python manage.py collect_interactions --generate-report --save-session

# Retrain with new data
python manage.py train_agent --episodes 50 --days 7 --save

# Evaluate improvement
python manage.py evaluate_model --model-path ml/models/dqn_agent_latest.h5 --test-days 7

# Compare metrics
echo "Check metrics in evaluation output"
```

---

## File Structure

```
apps/interactions/management/
├── __init__.py
├── commands/
│   ├── __init__.py
│   ├── train_agent.py           # RL model training
│   ├── evaluate_model.py        # Model evaluation
│   ├── collect_interactions.py  # Data collection
│   ├── sync_spotify_tracks.py   # Spotify sync
│   └── moodsic_help.py         # Help documentation
```

---

## Output Locations

### Model Files
- Location: `ml/models/`
- Format: `dqn_agent_YYYYMMDD_HHMMSS.h5`
- Size: ~33 KB

### Training Logs
- Location: `ml/logs/`
- Format: `training_YYYYMMDD_HHMMSS.json`
- Contains: Loss, reward, epsilon decay history

### Reports
- Location: Project root or specified directory
- Format: `interaction_report_YYYYMMDD_HHMMSS.txt`
- Contains: Summary statistics and top tracks

---

## Tips & Best Practices

1. **Always use --verbose for debugging**
   ```bash
   python manage.py train_agent --episodes 10 --verbose
   ```

2. **Save models after successful training**
   ```bash
   python manage.py train_agent --episodes 100 --save
   ```

3. **Generate reports for analysis**
   ```bash
   python manage.py collect_interactions --generate-report --days 30
   ```

4. **Test with small batches first**
   ```bash
   python manage.py train_agent --episodes 5 --batch-size 32 --verbose
   ```

5. **Keep track of model versions**
   - Models auto-save with timestamps
   - Evaluate each model after training
   - Keep best performing models

---

## Configuration Requirements

### Database
- PostgreSQL configured and connected ✅
- Migrations applied ✅
- Interaction & Track models created ✅

### Environment Variables (Optional)
```bash
# For Spotify sync command
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

### Python & Django
- Django 4.2.29 ✅
- Python 3.13 ✅
- All dependencies installed (`requirements.txt`) ✅

---

## Troubleshooting

### Command not found
```bash
# Ensure you're in project root
cd c:\Users\Usuario\Git\moodsic

# Check if commands are installed
python manage.py help train_agent
```

### Database errors
```bash
# Apply migrations if needed
python manage.py migrate

# Check database connection
python manage.py dbshell
```

### Model loading errors
```bash
# Verify model file exists
ls ml/models/

# Check file permissions
# Check file format (should be HDF5)
```

### Encoding errors on Windows
- Commands now use ASCII-safe format
- If issues persist, add to PowerShell:
  ```powershell
  $env:PYTHONIOENCODING='utf-8'
  ```

---

## Advanced Usage

### Batch Process Multiple Users
```bash
# Process all users
for i in 1 2 3 4 5; do
    python manage.py collect_interactions --user-id $i --save-session
done
```

### Scheduled Training (Cronjob Example)
```bash
# Windows Task Scheduler:
# Action: python manage.py train_agent --episodes 50 --days 7 --save
# Frequency: Daily at 02:00 AM
```

### Pipeline Automation
```bash
# Create a bash script: train_pipeline.sh
#!/bin/bash
python manage.py collect_interactions --days 7 --save-session
python manage.py train_agent --episodes 100 --save --visualize
python manage.py evaluate_model --model-path ml/models/dqn_agent_latest.h5
python manage.py sync_spotify_tracks --limit 100
```

---

## Support & Documentation

- Main docs: See `DEVELOPMENT.md`
- API reference: `DEVELOPMENT.md` - API Endpoints
- Test suite: `TEST_SUMMARY.md`
- Architecture: `README.md`

---

**Version**: 1.0  
**Last Updated**: 2026-03-25  
**Status**: Production Ready ✅
