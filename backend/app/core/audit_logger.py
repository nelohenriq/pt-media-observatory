# audit_logger.py - Tamper-proof audit log

import hashlib
import json
from datetime import datetime
import uuid
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

class AuditLog:
    @staticmethod
    async def record(session: AsyncSession, entity_type: str, entity_id: uuid.UUID,
                     action: str, old_value: str = None, new_value: str = None,
                     user_id: uuid.UUID = None):
        """
        Record an immutable audit entry with chain hashing for tamper-proofing.
        """
        # Get previous hash from audit_log table
        result = await session.execute(
            "SELECT chain_hash FROM audit_log ORDER BY created_at DESC LIMIT 1"
        )
        prev = result.scalar() or "0" * 64

        # Build entry dictionary
        entry = {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "user_id": str(user_id) if user_id else None,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": None,
            "previous_hash": prev,
        }

        # Calculate chain hash
        entry_json = json.dumps(entry, sort_keys=True)
        entry["chain_hash"] = hashlib.sha256((prev + entry_json).encode()).hexdigest()

        # Insert into audit_log table
        stmt = insert().values(**entry)
        await session.execute(stmt)
        await session.commit()