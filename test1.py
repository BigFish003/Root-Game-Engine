from Data.Data_converter import *
from state_renderer.render import *
import os, json

with open(r"C:\Users\samth\OneDrive\Documents\Root_June_AI_Dataset\turn_end_games_20260607_223511.jsonl", "r", encoding="utf-8") as file:
    line = file.readlines()[27]

engine = gamestate_line_to_root_engine(str(line))
render = state_renderer()

render.render_board(engine.get_observation(Faction.ALLIANCE), output_path="game_state.png")

print(engine.get_state().board.warriors[3])