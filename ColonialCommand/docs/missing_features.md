# Previously Unused Features

The features called out in earlier audits now contribute directly to gameplay:

- **Technology bonuses now apply.** Research completion feeds the corresponding bonuses into faction modifiers, updating income, trade, combat, and naval performance. 【F:src/core/state.py†L178-L213】【F:src/core/state.py†L256-L283】
- **Faction traits are honoured.** Trade and naval modifiers influence diplomacy checks, trade revenue, and sea-lane movement. 【F:src/core/state.py†L86-L111】【F:src/systems/diplomacy.py†L22-L47】【F:src/systems/movement.py†L8-L32】
- **Region resources matter.** Resource tags affect regional income and unlock additional recruitment options, including artillery, cavalry, and naval units. 【F:src/data/regions.py†L35-L93】【F:src/core/state.py†L215-L251】
- **Unit speed affects campaigns.** Army movement allowances derive from unit speed (and naval assets), enabling faster forces to cover more ground. 【F:src/core/state.py†L27-L44】【F:src/systems/movement.py†L27-L53】
- **Naval units are recruitable and useful.** Ports and naval tech unlock sloops and frigates, which enable ocean travel and contribute to battles. 【F:src/core/state.py†L215-L251】【F:src/scenes/campaign.py†L197-L244】
- **Diplomatic relations have teeth.** War status cancels trade, neutral/allied standings modify trade chances, and bonuses adjust payouts. 【F:src/systems/diplomacy.py†L14-L47】

No additional unused feature definitions are currently known. Re-open this document if new dead code paths are discovered.
