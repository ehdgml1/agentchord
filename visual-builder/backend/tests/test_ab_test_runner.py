"""Tests for A/B test runner."""
import pytest
import uuid
from datetime import datetime
from app.core.ab_test_runner import ABTestRunner
from app.models.ab_test import ABTest, ABTestResult
from app.dtos.ab_test import ABTestStats


class TestABTestRunner:
    """Tests for A/B test runner."""

    @pytest.mark.asyncio
    async def test_traffic_split_respects_ratio(self, db_session):
        """Traffic split should respect the configured ratio."""
        runner = ABTestRunner(db_session)

        # Create test workflows
        workflow_a_id = str(uuid.uuid4())
        workflow_b_id = str(uuid.uuid4())

        # Create AB test with 70/30 split
        test = ABTest(
            id=str(uuid.uuid4()),
            name="Traffic Split Test",
            workflow_a_id=workflow_a_id,
            workflow_b_id=workflow_b_id,
            traffic_split=0.7,  # 70% A, 30% B
            status="running",
        )
        db_session.add(test)
        await db_session.commit()

        # Run 100 times and count variants
        variant_counts = {"A": 0, "B": 0}
        for _ in range(100):
            variant, _ = await runner.run(test.id, "test input")
            variant_counts[variant] += 1

        # Check approximately correct split (with tolerance for randomness)
        # 70% should be between 60-80%, 30% should be between 20-40%
        assert 60 <= variant_counts["A"] <= 80, f"Variant A count {variant_counts['A']} outside expected range"
        assert 20 <= variant_counts["B"] <= 40, f"Variant B count {variant_counts['B']} outside expected range"

    @pytest.mark.asyncio
    async def test_traffic_split_50_50(self, db_session):
        """50/50 traffic split should be balanced."""
        runner = ABTestRunner(db_session)

        # Create test workflows
        workflow_a_id = str(uuid.uuid4())
        workflow_b_id = str(uuid.uuid4())

        # Create AB test with 50/50 split
        test = ABTest(
            id=str(uuid.uuid4()),
            name="Balanced Split Test",
            workflow_a_id=workflow_a_id,
            workflow_b_id=workflow_b_id,
            traffic_split=0.5,
            status="running",
        )
        db_session.add(test)
        await db_session.commit()

        # Run 100 times
        variant_counts = {"A": 0, "B": 0}
        for _ in range(100):
            variant, _ = await runner.run(test.id, "test input")
            variant_counts[variant] += 1

        # Should be roughly 50/50 (35-65% range due to randomness)
        assert 35 <= variant_counts["A"] <= 65
        assert 35 <= variant_counts["B"] <= 65

    @pytest.mark.asyncio
    async def test_record_and_retrieve_results(self, db_session):
        """Results should be recorded and retrievable."""
        runner = ABTestRunner(db_session)

        # Create test
        test = ABTest(
            id=str(uuid.uuid4()),
            name="Result Recording Test",
            workflow_a_id=str(uuid.uuid4()),
            workflow_b_id=str(uuid.uuid4()),
            traffic_split=0.5,
            status="running",
        )
        db_session.add(test)
        await db_session.commit()

        # Record some results
        await runner.record_result(
            test_id=test.id,
            variant="A",
            execution_id=str(uuid.uuid4()),
            duration_ms=100,
            success=True,
        )
        await runner.record_result(
            test_id=test.id,
            variant="A",
            execution_id=str(uuid.uuid4()),
            duration_ms=150,
            success=True,
        )
        await runner.record_result(
            test_id=test.id,
            variant="B",
            execution_id=str(uuid.uuid4()),
            duration_ms=200,
            success=False,
        )

        # Get stats
        stats = await runner.get_stats(test.id)

        # Verify stats
        assert stats["A"].count == 2
        assert stats["A"].success_rate == 1.0
        assert stats["A"].avg_duration_ms == 125.0

        assert stats["B"].count == 1
        assert stats["B"].success_rate == 0.0
        assert stats["B"].avg_duration_ms == 200.0

    @pytest.mark.asyncio
    async def test_stats_calculation(self, db_session):
        """Stats should be calculated correctly."""
        runner = ABTestRunner(db_session)

        # Create test
        test = ABTest(
            id=str(uuid.uuid4()),
            name="Stats Calculation Test",
            workflow_a_id=str(uuid.uuid4()),
            workflow_b_id=str(uuid.uuid4()),
            traffic_split=0.5,
            status="running",
        )
        db_session.add(test)
        await db_session.commit()

        # Record mixed results for variant A
        for i in range(10):
            await runner.record_result(
                test_id=test.id,
                variant="A",
                execution_id=str(uuid.uuid4()),
                duration_ms=100 + i * 10,
                success=i < 7,  # 70% success rate
            )

        # Get stats
        stats = await runner.get_stats(test.id)

        assert stats["A"].count == 10
        assert stats["A"].success_rate == 0.7
        assert stats["A"].avg_duration_ms == 145.0  # (100+110+120+...+190) / 10

    @pytest.mark.asyncio
    async def test_stats_with_no_results(self, db_session):
        """Stats should handle empty results gracefully."""
        runner = ABTestRunner(db_session)

        # Create test with no results
        test = ABTest(
            id=str(uuid.uuid4()),
            name="Empty Stats Test",
            workflow_a_id=str(uuid.uuid4()),
            workflow_b_id=str(uuid.uuid4()),
            traffic_split=0.5,
            status="running",
        )
        db_session.add(test)
        await db_session.commit()

        # Get stats without recording any results
        stats = await runner.get_stats(test.id)

        assert stats["A"].count == 0
        assert stats["A"].success_rate == 0.0
        assert stats["A"].avg_duration_ms == 0.0

        assert stats["B"].count == 0
        assert stats["B"].success_rate == 0.0
        assert stats["B"].avg_duration_ms == 0.0

    @pytest.mark.asyncio
    async def test_csv_export(self, db_session):
        """CSV export should format results correctly."""
        runner = ABTestRunner(db_session)

        # Create test
        test = ABTest(
            id=str(uuid.uuid4()),
            name="CSV Export Test",
            workflow_a_id=str(uuid.uuid4()),
            workflow_b_id=str(uuid.uuid4()),
            traffic_split=0.5,
            status="running",
        )
        db_session.add(test)
        await db_session.commit()

        # Record some results
        exec_id_a = str(uuid.uuid4())
        exec_id_b = str(uuid.uuid4())

        await runner.record_result(
            test_id=test.id,
            variant="A",
            execution_id=exec_id_a,
            duration_ms=100,
            success=True,
        )
        await runner.record_result(
            test_id=test.id,
            variant="B",
            execution_id=exec_id_b,
            duration_ms=200,
            success=False,
        )

        # Export to CSV
        csv_data = await runner.export_csv(test.id)

        # Verify CSV format
        lines = csv_data.strip().split("\n")
        assert len(lines) == 3  # Header + 2 data rows

        # Check header
        assert "variant" in lines[0]
        assert "execution_id" in lines[0]
        assert "duration_ms" in lines[0]
        assert "success" in lines[0]

        # Check data rows contain expected values
        csv_content = "\n".join(lines)
        assert exec_id_a in csv_content
        assert exec_id_b in csv_content
        assert "100" in csv_content
        assert "200" in csv_content

    @pytest.mark.asyncio
    async def test_run_requires_running_status(self, db_session):
        """Run should only work with running status."""
        runner = ABTestRunner(db_session)

        # Create test with draft status
        test = ABTest(
            id=str(uuid.uuid4()),
            name="Draft Test",
            workflow_a_id=str(uuid.uuid4()),
            workflow_b_id=str(uuid.uuid4()),
            traffic_split=0.5,
            status="draft",  # Not running
        )
        db_session.add(test)
        await db_session.commit()

        # Should raise error
        with pytest.raises(ValueError, match="not running"):
            await runner.run(test.id, "test input")

    @pytest.mark.asyncio
    async def test_run_with_nonexistent_test(self, db_session):
        """Run should fail with nonexistent test."""
        runner = ABTestRunner(db_session)

        # Try to run nonexistent test
        with pytest.raises(ValueError, match="not found"):
            await runner.run("nonexistent-id", "test input")

    @pytest.mark.asyncio
    async def test_stats_with_null_durations(self, db_session):
        """Stats should handle null durations gracefully."""
        runner = ABTestRunner(db_session)

        # Create test
        test = ABTest(
            id=str(uuid.uuid4()),
            name="Null Duration Test",
            workflow_a_id=str(uuid.uuid4()),
            workflow_b_id=str(uuid.uuid4()),
            traffic_split=0.5,
            status="running",
        )
        db_session.add(test)
        await db_session.commit()

        # Record results with some null durations
        await runner.record_result(
            test_id=test.id,
            variant="A",
            execution_id=str(uuid.uuid4()),
            duration_ms=None,
            success=True,
        )
        await runner.record_result(
            test_id=test.id,
            variant="A",
            execution_id=str(uuid.uuid4()),
            duration_ms=100,
            success=True,
        )

        # Get stats
        stats = await runner.get_stats(test.id)

        # Should calculate average from non-null values only
        assert stats["A"].count == 2
        assert stats["A"].avg_duration_ms == 100.0
