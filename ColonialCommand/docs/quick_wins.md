# Quick Win Enhancements

Below are fifteen small, low-risk improvements that can be tackled individually to polish **Colonial Command** without deep refactors.

1. **Add a keyboard shortcut hint strip** to the bottom HUD so players can quickly see hotkeys like `H` for help or `U` for undo.
2. **Display recruit/build tooltips** with upkeep and build time details when hovering over action buttons.
3. **Persist the last-used save slot** in `config.json` to preselect it on the load screen.
4. **Animate message log entries** with a brief fade-in to draw attention to new events.
5. **Show faction emblems** (simple colored icons) beside region owners in the campaign view tooltip.
6. **Highlight valid movement paths** when an army is selected by flashing adjacent regions.
7. **Add a quick treasury change summary** to the end-turn report showing income vs. upkeep deltas.
8. **Include a “Skip AI moves” toggle** in settings to speed up turns during testing.
9. **Add ambient harbor/crowd bleeps** on the campaign screen when audio is enabled, looping quietly.
10. **Implement a simple autosave timestamp display** on the main menu load panel.
11. **Color-code diplomacy statuses** (peace/trade/war) in the faction list for easier scanning.
12. **Add an “Are you sure?” prompt** before deleting or overwriting save slots.
13. **Provide a minimal tutorial popup** on the first turn with two or three guidance tips.
14. **Expose the RNG seed in the pause/debug overlay** so testers can note exact scenarios.
15. **Add a windowed/fullscreen toggle hotkey** (e.g., `Alt+Enter`) wired to the existing display manager.

Each task should fit within a short development session and improve usability or feedback without touching core simulation code.
