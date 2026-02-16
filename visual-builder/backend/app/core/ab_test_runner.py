"""A/B Test execution and statistics."""

import json
import random
import uuid
from datetime import UTC, datetime
from io import StringIO
import csv
from typing import AsyncGenerator

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ab_test import ABTest, ABTestResult
from app.models.workflow import Workflow
from app.dtos.ab_test import ABTestStats


class ABTestRunner:
    """A/B Test execution and statistics manager."""

    def __init__(self, db: AsyncSession):
        """Initialize runner with database session.

        Args:
            db: Database session
        """
        self.db = db

    async def run(self, test_id: str, input_data: str) -> tuple[str, str]:
        """Run A/B test with traffic split.

        Args:
            test_id: A/B test ID
            input_data: Input for workflow execution

        Returns:
            Tuple of (variant, execution_id)

        Raises:
            ValueError: If test not found or not running
        """
        # Get test
        result = await self.db.execute(
            select(ABTest).where(ABTest.id == test_id)
        )
        test = result.scalar_one_or_none()
        if not test:
            raise ValueError(f"Test {test_id} not found")

        if test.status != "running":
            raise ValueError(f"Test {test_id} is not running")

        # Select variant based on traffic split
        rand = random.random()
        variant = "A" if rand < test.traffic_split else "B"
        workflow_id = test.workflow_a_id if variant == "A" else test.workflow_b_id

        # Create execution record (would trigger actual workflow execution)
        execution_id = str(uuid.uuid4())

        return variant, execution_id

    async def record_result(
        self,
        test_id: str,
        variant: str,
        execution_id: str,
        duration_ms: int | None,
        success: bool,
    ) -> None:
        """Record A/B test result.

        Args:
            test_id: A/B test ID
            variant: Variant (A or B)
            execution_id: Execution ID
            duration_ms: Duration in milliseconds
            success: Whether execution succeeded
        """
        result = ABTestResult(
            id=str(uuid.uuid4()),
            test_id=test_id,
            variant=variant,
            execution_id=execution_id,
            duration_ms=duration_ms,
            success=success,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.db.add(result)
        await self.db.commit()

    async def get_stats(self, test_id: str) -> dict[str, ABTestStats]:
        """Get statistics for both variants.

        Args:
            test_id: A/B test ID

        Returns:
            Dictionary mapping variant to statistics
        """
        stats = {}

        for variant in ["A", "B"]:
            # Count total executions
            count_result = await self.db.execute(
                select(func.count(ABTestResult.id))
                .where(ABTestResult.test_id == test_id)
                .where(ABTestResult.variant == variant)
            )
            count = count_result.scalar() or 0

            if count == 0:
                stats[variant] = ABTestStats(
                    variant=variant,
                    count=0,
                    success_rate=0.0,
                    avg_duration_ms=0.0,
                )
                continue

            # Calculate success rate
            success_result = await self.db.execute(
                select(func.count(ABTestResult.id))
                .where(ABTestResult.test_id == test_id)
                .where(ABTestResult.variant == variant)
                .where(ABTestResult.success == True)
            )
            success_count = success_result.scalar() or 0
            success_rate = success_count / count if count > 0 else 0.0

            # Calculate average duration
            avg_result = await self.db.execute(
                select(func.avg(ABTestResult.duration_ms))
                .where(ABTestResult.test_id == test_id)
                .where(ABTestResult.variant == variant)
                .where(ABTestResult.duration_ms.isnot(None))
            )
            avg_duration = avg_result.scalar() or 0.0

            stats[variant] = ABTestStats(
                variant=variant,
                count=count,
                success_rate=success_rate,
                avg_duration_ms=float(avg_duration),
            )

        return stats

    async def export_csv(self, test_id: str) -> str:
        """Export results to CSV string.

        Args:
            test_id: A/B test ID

        Returns:
            CSV string with results
        """
        # Get all results
        result = await self.db.execute(
            select(ABTestResult)
            .where(ABTestResult.test_id == test_id)
            .order_by(ABTestResult.created_at)
        )
        results = result.scalars().all()

        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "variant",
            "execution_id",
            "duration_ms",
            "success",
            "created_at",
        ])

        # Data rows
        for r in results:
            writer.writerow([
                r.variant,
                r.execution_id,
                r.duration_ms or "",
                r.success,
                r.created_at.isoformat(),
            ])

        return output.getvalue()

    async def list_results(
        self, test_id: str, limit: int = 100, offset: int = 0
    ) -> AsyncGenerator[ABTestResult, None]:
        """List results for a test.

        Args:
            test_id: A/B test ID
            limit: Maximum number of results
            offset: Offset for pagination

        Yields:
            ABTestResult instances
        """
        result = await self.db.execute(
            select(ABTestResult)
            .where(ABTestResult.test_id == test_id)
            .order_by(ABTestResult.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        for row in result.scalars():
            yield row
