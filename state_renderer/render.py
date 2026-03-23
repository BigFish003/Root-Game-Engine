from PIL import Image, ImageDraw, ImageFont

class state_renderer:
    """Module for rendering Root game states."""

    def render_board(self, observation, output_path):
        """Render the game board as an image."""
        
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img) 
    
        draw.rectangle((0, 0, 550, 350), fill="blue", outline="black", width=3)

        img.save(output_path)

Render = state_renderer()
Render.render_board(observation={}, output_path='game_state.png')
