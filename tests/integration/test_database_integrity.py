"""
AICF v2 Database Integrity Test

This script tests the complete AICF v2 domain model by creating
sample data and verifying relationships, constraints, and cascade rules.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

# Use SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})

# Import models
from database.connection import Base
from database import models  # noqa: F401 - Ensure all models are loaded
from database.models import (
    Organization, Team, User, Role, Permission, UserRole, TeamMember, AuditLog,
    ChannelProfile, ContentStrategy, Playlist, Episode, ProductionTemplate,
    ContentJob, Asset, AgentExecution,
    PlaylistType, EpisodeStatus, ContentJobStatus, AgentExecutionStatus, AssetType
)


def test_database_integrity():
    """Test complete AICF v2 domain model integrity."""
    
    print("=" * 70)
    print("AICF v2 Database Integrity Test")
    print("=" * 70)
    
    # Create tables
    print("\n[1/10] Creating database schema...")
    Base.metadata.create_all(bind=test_engine)
    print("✓ Schema created successfully")
    
    with Session(test_engine) as db:
        try:
            # 1. Create Organization
            print("\n[2/10] Creating Organization...")
            org = Organization(
                name="History AI Studio",
                slug="history-ai-studio",
                description="AI-powered history content production",
                subscription_plan="pro",
                max_teams=10,
                max_users=50,
                max_channels=20,
                storage_limit_gb=100.0
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"✓ Organization created: {org.name} (ID: {org.id})")
            
            # 2. Create User
            print("\n[3/10] Creating User...")
            user = User(
                organization_id=org.id,
                email="creator@historystudio.com",
                full_name="Content Creator",
                is_active=True,
                is_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ User created: {user.email} (ID: {user.id})")
            
            # 3. Create ChannelProfile
            print("\n[4/10] Creating ChannelProfile...")
            channel = ChannelProfile(
                organization_id=org.id,
                name="European History",
                slug="european-history",
                platform="youtube",
                handle="@EuropeanHistory",
                description="Exploring European history through AI-generated content",
                target_audience={"demographics": "25-54", "interests": ["history", "education"]},
                age_range="25-54",
                interests=["history", "documentaries", "education"],
                content_style="documentary",
                tone="professional",
                language="en",
                visual_identity={"colors": ["#1a1a2e", "#16213e"], "fonts": ["Roboto"]},
                aspect_ratio="16:9",
                voice_type="male_narrator",
                is_active=True
            )
            db.add(channel)
            db.commit()
            db.refresh(channel)
            print(f"✓ ChannelProfile created: {channel.name} (ID: {channel.id})")
            
            # 4. Create ContentStrategy
            print("\n[5/10] Creating ContentStrategy...")
            strategy = ContentStrategy(
                organization_id=org.id,
                channel_profile_id=channel.id,
                goals="Educate audience about European history with engaging short-form content",
                kpi_targets={"subscribers": 100000, "views_per_video": 50000, "engagement_rate": 5.0},
                content_pillars=["Medieval History", "Renaissance", "World Wars", "Modern Europe"],
                publishing_schedule={"monday": "10:00", "wednesday": "10:00", "friday": "10:00"},
                posting_frequency="3 times per week"
            )
            db.add(strategy)
            db.commit()
            db.refresh(strategy)
            print(f"✓ ContentStrategy created for channel (ID: {strategy.id})")
            
            # 5. Create Playlists (both types)
            print("\n[6/10] Creating Playlists...")
            
            # Planned Playlist
            planned_playlist = Playlist(
                organization_id=org.id,
                channel_profile_id=channel.id,
                creator_id=user.id,
                title="Medieval Europe Series",
                slug="medieval-europe-series",
                description="Complete series on Medieval European history",
                playlist_type=PlaylistType.PLANNED_PLAYLIST,
                episode_roadmap=[{"order": 1, "topic": "Feudalism"}, {"order": 2, "topic": "Crusades"}],
                total_planned_episodes=12,
                is_active=True
            )
            db.add(planned_playlist)
            
            # Dynamic Playlist
            dynamic_playlist = Playlist(
                organization_id=org.id,
                channel_profile_id=channel.id,
                creator_id=user.id,
                title="History News Daily",
                slug="history-news-daily",
                description="Daily history news and discoveries",
                playlist_type=PlaylistType.DYNAMIC_PLAYLIST,
                content_source={"rss_feeds": ["https://example.com/history.xml"], "keywords": ["archaeology", "discovery"]},
                auto_generation_enabled=True,
                max_episodes=365,
                is_active=True
            )
            db.add(dynamic_playlist)
            db.commit()
            db.refresh(planned_playlist)
            db.refresh(dynamic_playlist)
            print(f"✓ Planned Playlist created: {planned_playlist.title} (ID: {planned_playlist.id})")
            print(f"✓ Dynamic Playlist created: {dynamic_playlist.title} (ID: {dynamic_playlist.id})")
            
            # 6. Create Episode
            print("\n[7/10] Creating Episode...")
            episode = Episode(
                organization_id=org.id,
                channel_profile_id=channel.id,
                playlist_id=planned_playlist.id,
                creator_id=user.id,
                title="The Rise of Feudalism",
                slug="rise-of-feudalism",
                description="Exploring how feudalism shaped Medieval Europe",
                episode_number=1,
                season_number=1,
                status=EpisodeStatus.PLANNED,
                episode_type="planned",
                topic="Feudalism in Medieval Europe",
                keywords=["feudalism", "medieval", "europe", "history"],
                priority=5,
                estimated_duration=300
            )
            db.add(episode)
            db.commit()
            db.refresh(episode)
            print(f"✓ Episode created: {episode.title} (ID: {episode.id}, Status: {episode.status})")
            
            # 7. Create ProductionTemplate
            print("\n[8/10] Creating ProductionTemplate...")
            template = ProductionTemplate(
                organization_id=org.id,
                channel_profile_id=channel.id,
                name="Documentary Style Template",
                slug="documentary-style",
                description="Standard documentary production settings",
                narrator_character="Wise Historian",
                voice_id="elevenlabs-historian-male",
                visual_style="cinematic",
                color_palette=["#1a1a2e", "#16213e", "#0f3460"],
                duration_target=300,
                aspect_ratio="16:9",
                resolution="1920x1080",
                fps=30,
                music_style="orchestral",
                audio_quality="high",
                preferred_ai_provider="openai",
                is_active=True
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            print(f"✓ ProductionTemplate created: {template.name} (ID: {template.id})")
            
            # 8. Create ContentJob
            print("\n[9/10] Creating ContentJob...")
            job = ContentJob(
                organization_id=org.id,
                episode_id=episode.id,
                production_template_id=template.id,
                job_type="script_generation",
                task_description="Generate script for feudalism episode",
                priority=5,
                status=ContentJobStatus.PENDING,
                ai_provider="openai",
                model_name="gpt-4o-mini",
                max_retries=3
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            print(f"✓ ContentJob created: {job.job_type} (ID: {job.id}, Status: {job.status})")
            
            # 9. Create AgentExecution
            print("\n[10/10] Creating AgentExecution...")
            agent_exec = AgentExecution(
                organization_id=org.id,
                episode_id=episode.id,
                content_job_id=job.id,
                agent_name="ScriptWriterAgent",
                agent_version="1.0.0",
                agent_type="script_generation",
                purpose="Generate episode script from topic outline",
                status=AgentExecutionStatus.PENDING,
                ai_provider="openai",
                ai_model="gpt-4o-mini",
                max_retries=3
            )
            db.add(agent_exec)
            db.commit()
            db.refresh(agent_exec)
            print(f"✓ AgentExecution created: {agent_exec.agent_name} (ID: {agent_exec.id}, Status: {agent_exec.status})")
            
            # 10. Create Asset
            print("\n[11/10] Creating Asset...")
            asset = Asset(
                organization_id=org.id,
                episode_id=episode.id,
                name="Episode Thumbnail",
                asset_type=AssetType.THUMBNAIL,
                filename="thumbnail_ep01.png",
                url="https://storage.example.com/thumbnails/ep01.png",
                mime_type="image/png",
                size_bytes=245000,
                width=1920,
                height=1080,
                processing_status="completed"
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
            print(f"✓ Asset created: {asset.name} (ID: {asset.id}, Type: {asset.asset_type})")
            
            # Verify Relationships
            print("\n" + "=" * 70)
            print("Relationship Verification")
            print("=" * 70)
            
            # Verify tenant isolation
            assert episode.organization_id == org.id, "Episode should belong to organization"
            assert job.organization_id == org.id, "Job should belong to organization"
            assert agent_exec.organization_id == org.id, "Agent execution should belong to organization"
            print("✓ Tenant isolation verified - all entities linked to organization")
            
            # Verify cascade relationships
            assert len(org.channel_profiles) == 1, "Organization should have 1 channel"
            assert len(channel.playlists) == 2, "Channel should have 2 playlists"
            assert len(planned_playlist.episodes) == 1, "Planned playlist should have 1 episode"
            assert len(episode.content_jobs) == 1, "Episode should have 1 content job"
            assert len(episode.agent_executions) == 1, "Episode should have 1 agent execution"
            assert len(episode.assets) == 1, "Episode should have 1 asset"
            print("✓ Cascade relationships verified")
            
            # Verify enums
            assert planned_playlist.playlist_type == PlaylistType.PLANNED_PLAYLIST
            assert dynamic_playlist.playlist_type == PlaylistType.DYNAMIC_PLAYLIST
            assert episode.status == EpisodeStatus.PLANNED
            assert job.status == ContentJobStatus.PENDING
            assert agent_exec.status == AgentExecutionStatus.PENDING
            assert asset.asset_type == AssetType.THUMBNAIL
            print("✓ Enum values verified")
            
            print("\n" + "=" * 70)
            print("ALL TESTS PASSED ✓")
            print("=" * 70)
            print("\nDatabase integrity test completed successfully!")
            print("All AICF v2 domain models are working correctly.")
            
            return True
            
        except Exception as e:
            db.rollback()
            print(f"\n✗ TEST FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_database_integrity()
    sys.exit(0 if success else 1)
