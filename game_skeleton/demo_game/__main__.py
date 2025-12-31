"""
Water Demo Game - Example game using Water DRM.

Run with:
    python -m demo_game --token <launch_token> --access <access_token>
"""

import argparse
import sys
import pygame

from demo_game.drm import WaterDRM, DRMConfig


# Game constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

# Colors
BG_COLOR = (20, 24, 28)
TEXT_COLOR = (240, 240, 240)
ACCENT_COLOR = (66, 133, 244)
ERROR_COLOR = (234, 67, 53)
SUCCESS_COLOR = (52, 168, 83)


class DemoGame:
    """Simple demo game showcasing Water DRM integration."""
    
    def __init__(self, drm: WaterDRM):
        self.drm = drm
        self.running = False
        
        # Pygame setup
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Water Demo Game")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_large = pygame.font.SysFont("Arial", 48)
        self.font_medium = pygame.font.SysFont("Arial", 24)
        self.font_small = pygame.font.SysFont("Arial", 18)
        
        # Game state
        self.player_x = WINDOW_WIDTH // 2
        self.player_y = WINDOW_HEIGHT // 2
        self.player_speed = 5
    
    def handle_events(self) -> None:
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def update(self) -> None:
        """Update game state."""
        # Simple player movement with arrow keys
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player_x -= self.player_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player_x += self.player_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player_y -= self.player_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player_y += self.player_speed
        
        # Keep player in bounds
        self.player_x = max(25, min(WINDOW_WIDTH - 25, self.player_x))
        self.player_y = max(25, min(WINDOW_HEIGHT - 25, self.player_y))
        
        # Send DRM heartbeat (rate-limited internally)
        if not self.drm.heartbeat():
            print("DRM heartbeat failed - session terminated")
            self.running = False
    
    def render(self) -> None:
        """Draw game graphics."""
        self.screen.fill(BG_COLOR)
        
        # Title
        title = self.font_large.render("Water Demo Game", True, TEXT_COLOR)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 30))
        
        # DRM status
        if self.drm.is_online:
            status_text = f"● Online (Session: {self.drm.session_id})"
            status_color = SUCCESS_COLOR
        else:
            status_text = "● Offline Mode"
            status_color = ERROR_COLOR
        
        status = self.font_small.render(status_text, True, status_color)
        self.screen.blit(status, (20, 20))
        
        # Instructions
        instructions = [
            "Use WASD or Arrow Keys to move",
            "Press ESC to exit",
        ]
        for i, text in enumerate(instructions):
            rendered = self.font_small.render(text, True, TEXT_COLOR)
            self.screen.blit(rendered, (20, WINDOW_HEIGHT - 60 + i * 25))
        
        # Draw player (simple circle)
        pygame.draw.circle(self.screen, ACCENT_COLOR, (self.player_x, self.player_y), 25)
        pygame.draw.circle(self.screen, TEXT_COLOR, (self.player_x, self.player_y), 25, 2)
        
        pygame.display.flip()
    
    def run(self) -> None:
        """Main game loop."""
        self.running = True
        
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(FPS)
        
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Water Demo Game")
    parser.add_argument("--token", required=True, help="Launch token from /drm/launch")
    parser.add_argument("--access", required=True, help="User access token")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--offline", action="store_true", help="Allow offline mode")
    args = parser.parse_args()
    
    # Configure DRM
    config = DRMConfig(
        api_base=args.api,
        allow_offline=args.offline,
    )
    
    def on_drm_failed(error: str):
        print(f"DRM Error: {error}")
    
    # Use DRM as context manager for clean shutdown
    with WaterDRM(config, on_validation_failed=on_drm_failed) as drm:
        # Validate license
        if not drm.validate(args.token, args.access):
            print("License validation failed. Exiting.")
            sys.exit(1)
        
        print(f"License validated! Session ID: {drm.session_id}")
        
        # Run game
        game = DemoGame(drm)
        game.run()
        
        print("Game closed. Goodbye!")


if __name__ == "__main__":
    main()
