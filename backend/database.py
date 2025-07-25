from supabase import create_client, Client
from config import settings
from typing import List, Optional, Dict, Any
import asyncio

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def _select(table: str, columns: str = "*", filters: Optional[List] = None, order: Optional[str] = None, desc: bool = False, limit: int = None):
    def query():
        query_builder = supabase.table(table).select(columns)
        if filters:
            for column, value in filters:
                query_builder = query_builder.eq(column, value)
        if order:
            query_builder = query_builder.order(order, desc=desc)
        if limit:
            query_builder = query_builder.limit(limit)
        return query_builder.execute()

    res = await asyncio.to_thread(query)
    return res

async def _insert(table: str, data: dict):
    def insert_fn():
        return supabase.table(table).insert(data).execute()
    res = await asyncio.to_thread(insert_fn)
    return res

async def _upsert(table: str, data: List[dict]):
    def upsert_fn():
        return supabase.table(table).upsert(data).execute()
    res = await asyncio.to_thread(upsert_fn)
    return res