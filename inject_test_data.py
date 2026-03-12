import os
from src.core.database import Ticket, init_db

# Ensure the data directory exists before touching the database
os.makedirs("data", exist_ok=True)

# 1. Use the Architect's initialization logic (This creates the tables)
SessionLocal = init_db("sqlite:///data/tickets.db")
db = SessionLocal()

try:
    # 2. Prepare the synthetic payload
    test_tickets = [
        Ticket(user_id="test1", description="Mi monitor no enciende", urgency="Low", status="Pending"),
        Ticket(user_id="test2", description="No puedo acceder a la VPN desde casa", urgency="High", status="Pending"),
        Ticket(user_id="test3", description="La pantalla de mi ordenador está negra y no da señal", urgency="Medium", status="Pending")
    ]

    # 3. Surgical Injection
    db.add_all(test_tickets)
    db.commit()
    print("✅ 3 test tickets injected successfully. Schema validated.")

except Exception as e:
    db.rollback()
    print(f"❌ Injection failed: {e}")
finally:
    db.close()