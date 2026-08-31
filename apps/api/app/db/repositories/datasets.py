"""Database repository for Dataset and DatasetProfile entities."""

from __future__ import annotations

from uuid import UUID

from app.db.models.entities import Dataset, DatasetProfile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class DatasetRepository:
    """Data access repository for workspace datasets and profiling metadata."""

    async def create_dataset(self, session: AsyncSession, dataset: Dataset) -> Dataset:
        session.add(dataset)
        await session.flush()
        return dataset

    async def get_dataset(self, session: AsyncSession, dataset_id: UUID) -> Dataset | None:
        result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
        return result.scalar_one_or_none()

    async def get_dataset_for_workspace(
        self, session: AsyncSession, workspace_id: UUID, dataset_id: UUID
    ) -> Dataset | None:
        result = await session.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_datasets_for_workspace(
        self, session: AsyncSession, workspace_id: UUID, offset: int, limit: int
    ) -> list[Dataset]:
        result = await session.execute(
            select(Dataset)
            .where(Dataset.workspace_id == workspace_id)
            .order_by(Dataset.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_profile(
        self, session: AsyncSession, profile: DatasetProfile
    ) -> DatasetProfile:
        session.add(profile)
        await session.flush()
        return profile

    async def get_profile_by_dataset_id(
        self, session: AsyncSession, dataset_id: UUID
    ) -> DatasetProfile | None:
        result = await session.execute(
            select(DatasetProfile).where(DatasetProfile.dataset_id == dataset_id)
        )
        return result.scalar_one_or_none()

    async def update_dataset_status(
        self,
        session: AsyncSession,
        dataset: Dataset,
        status: str,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> Dataset:
        dataset.status = status
        if row_count is not None:
            dataset.row_count = row_count
        if column_count is not None:
            dataset.column_count = column_count
        await session.flush()
        return dataset

    async def delete_dataset(self, session: AsyncSession, dataset: Dataset) -> None:
        await session.delete(dataset)
        await session.flush()
