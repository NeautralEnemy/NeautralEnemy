# Colonial Command

Colonial Command is a lightweight turn-based grand strategy prototype inspired by Amiga aesthetics and the colonial-era conflicts of the 1700s. Everything is rendered procedurally with Pygame using a chunky 320×200 internal resolution that is upscaled with nearest-neighbour filtering.

## Running the game

Double-click the script that matches your operating system:

- **Windows**: `Run_Windows.bat`
- **macOS**: `Run_macOS.command`
- **Linux**: `Run_Linux.sh`

On first launch each script creates a project-local virtual environment, installs Pygame quietly, and then starts the game. Subsequent runs reuse the environment. If Python is not available on the system the scripts print a helpful message.

## Gameplay overview

- Control the British Empire and expand across Europe, the Americas, Africa, and India.
- Each turn consists of **Recruit**, **Build**, **Research**, **Move**, and **End Turn** actions presented on the campaign HUD.
- Regions generate income based on economy and stability; spend funds on units and infrastructure.
- Maintain overland and naval **supply lines** from your capital—isolated regions lose stability, stall recruitment, and bleed armies to attrition.
- Develop provinces with multi-turn **Market, Fort, and Culture** projects that deepen the economy, harden defenses, and recover order.
- Fortified, well-supplied regions gain combat advantages in both auto-resolve and tactical clashes, while starving defenders crumble quickly.
- Research three mini tech trees (Economy, Military, Naval) to unlock faction bonuses.
- Manage diplomacy, trade, and public order through event messages. AI factions will recruit, move, and contest territory using simple heuristics.
- Battles auto-resolve with morale-aware power calculations; tactical simulations are summarised via the log.

## Controls & hotkeys

- Mouse-driven interface for selecting regions and pressing HUD buttons.
- `H` – Help overlay
- `Z` – Undo the last army move
- `G` – Cheat +1000 gold
- `F` – Cheat reveal map
- `R` – Cheat instant research
- `Esc` – Quit to desktop

## Saves & configuration

- Autosaves trigger at the start of each player turn and are stored in `saves/autosave.json`.
- Visual/audio settings persist to `config.json` (palette, scanlines, audio mute, window scale).

## Optional executable build

PyInstaller configuration is included for convenience. After the scripts create the virtual environment you can run:

```bash
# Windows
.\.venv\Scripts\pyinstaller --noconsole --onefile --name ColonialCommand src/main.py

# macOS / Linux
.venv/bin/pyinstaller --windowed --onefile --name ColonialCommand src/main.py
```

The resulting build will be placed in `dist/`.
