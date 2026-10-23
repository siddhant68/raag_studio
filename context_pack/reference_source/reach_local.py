"""Run the unmodified Agent Reach CLI with its private state scoped to this project."""
from pathlib import Path
from agent_reach.config import Config
from agent_reach.runtime import state
workspace_state = Path(__file__).resolve().parent / 'reach_state'
Config.CONFIG_DIR = workspace_state
Config.CONFIG_FILE = workspace_state / 'config.yaml'
state.root = lambda: workspace_state
from agent_reach.cli import main
main()
