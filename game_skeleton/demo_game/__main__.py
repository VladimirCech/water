
import sys, argparse, time
import pygame
import httpx

API_BASE = "http://127.0.0.1:8000"

def run_game(token: str, access_token: str | None = None):
    session_id = None
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        r = httpx.post(f"{API_BASE}/sessions/attest", json={"token": token}, headers=headers, timeout=10.0)
        r.raise_for_status()
        session_id = r.json()["session_id"]
    except Exception as e:
        print("Attest failed:", e)

    pygame.init()
    screen = pygame.display.set_mode((600, 360))
    pygame.display.set_caption("water Demo Game — Press ESC to Exit")
    font = pygame.font.SysFont(None, 28)

    running = True
    last_hb = 0.0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        now = time.time()
        if session_id and (now - last_hb) > 30:
            try:
                httpx.post(f"{API_BASE}/sessions/{session_id}/heartbeat", headers=headers, timeout=5.0)
                last_hb = now
            except Exception as e:
                print("Heartbeat failed:", e)
                running = False

        screen.fill((20, 24, 28))
        msg = "water Demo — online session active" if session_id else "water Demo — offline"
        text = font.render(msg, True, (240, 240, 240))
        screen.blit(text, (40, 160))
        pygame.display.flip()
        pygame.time.delay(50)

    pygame.quit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True, help="Launch token (JWT)")
    ap.add_argument("--access", default=None, help="Access token for API (Bearer)")
    args = ap.parse_args()
    run_game(args.token, args.access)

if __name__ == "__main__":
    main()
