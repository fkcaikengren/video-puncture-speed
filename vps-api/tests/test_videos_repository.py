import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from app.api.videos.repository import VideoRepository


@pytest.mark.asyncio
async def test_repository_get_videos_uploader_exact_match():
    executed = []

    async def _execute(query):
        executed.append(query)
        if len(executed) == 1:
            return SimpleNamespace(scalar=lambda: 0)
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)

    repo = VideoRepository(session)
    await repo.get_videos(page=1, page_size=20, uploader="alice")

    assert len(executed) == 2
    sql = str(executed[1].compile(dialect=postgresql.dialect()))
    assert "ILIKE" not in sql.upper()
    assert re.search(r"\buploader\b\s*=\s*", sql) is not None
