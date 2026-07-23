"""
Media Quality Evaluator

Provides automated quality evaluation for images, voice, and storyboards.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from aicf.app.media.evaluation.models import (
    MediaQualityScore, 
    ApprovalStatus, 
    QualityEvaluationType
)
from database.models import Asset, Episode
from services.exceptions import NotFoundError, ValidationError


class MediaQualityEvaluator:
    """
    Evaluator for media quality assessment.
    
    Evaluates different media types with specific criteria:
    - Images: prompt adherence, resolution, style consistency
    - Voice: duration, quality, pronunciation metadata
    - Storyboard: completeness, consistency
    """
    
    # Default scoring weights
    DEFAULT_WEIGHTS = {
        QualityEvaluationType.IMAGE: {
            "prompt_adherence": 0.4,
            "resolution": 0.3,
            "style_consistency": 0.3,
        },
        QualityEvaluationType.VOICE: {
            "duration": 0.2,
            "audio_quality": 0.5,
            "pronunciation": 0.3,
        },
        QualityEvaluationType.STORYBOARD: {
            "completeness": 0.5,
            "consistency": 0.5,
        },
    }
    
    # Thresholds for approval
    APPROVAL_THRESHOLDS = {
        "auto_approve": 85.0,  # Score >= 85 auto-approved
        "requires_review": 60.0,  # Score >= 60 requires human review
        "auto_reject": 60.0,  # Score < 60 auto-rejected
    }
    
    def __init__(self, db: Session):
        """
        Initialize evaluator with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def evaluate_image(
        self,
        asset_id: int,
        organization_id: int,
        prompt: Optional[str] = None,
        expected_resolution: Optional[Tuple[int, int]] = None,
        style_reference: Optional[Dict[str, Any]] = None,
        evaluator_type: str = "automated",
        evaluator_id: Optional[int] = None,
        evaluator_name: Optional[str] = None,
    ) -> MediaQualityScore:
        """
        Evaluate an image asset for quality.
        
        Args:
            asset_id: Asset ID
            organization_id: Organization ID
            prompt: Original prompt used for generation
            expected_resolution: Expected (width, height)
            style_reference: Style reference data
            evaluator_type: Type of evaluator
            evaluator_id: Evaluator ID
            evaluator_name: Evaluator name
            
        Returns:
            MediaQualityScore with evaluation results
            
        Raises:
            NotFoundError: If asset not found
        """
        asset = self._get_asset(asset_id, organization_id)
        
        if asset is None:
            raise NotFoundError(resource_type="asset", resource_id=asset_id)
        
        # Extract metrics from asset metadata
        metadata = asset.metadata or {}
        processing_metadata = asset.processing_metadata or {}
        
        # Evaluate prompt adherence (if prompt provided)
        prompt_adherence_score = self._evaluate_prompt_adherence(
            asset, prompt, metadata, processing_metadata
        )
        
        # Evaluate resolution
        resolution_score = self._evaluate_resolution(
            asset, expected_resolution, metadata
        )
        
        # Evaluate style consistency
        style_consistency_score = self._evaluate_style_consistency(
            asset, style_reference, metadata
        )
        
        # Calculate weighted overall score
        weights = self.DEFAULT_WEIGHTS[QualityEvaluationType.IMAGE]
        quality_score = (
            prompt_adherence_score * weights["prompt_adherence"] +
            resolution_score * weights["resolution"] +
            style_consistency_score * weights["style_consistency"]
        )
        
        # Identify issues
        issues = self._identify_image_issues(
            asset, 
            prompt_adherence_score, 
            resolution_score, 
            style_consistency_score
        )
        
        # Generate recommendations
        recommendations = self._generate_image_recommendations(
            asset, issues, quality_score
        )
        
        # Determine approval status
        approval_status = self._determine_approval_status(quality_score)
        
        # Create quality score record
        quality_score_obj = MediaQualityScore(
            asset_id=asset_id,
            organization_id=organization_id,
            evaluation_type=QualityEvaluationType.IMAGE,
            quality_score=quality_score,
            prompt_adherence_score=prompt_adherence_score,
            resolution_score=resolution_score,
            style_consistency_score=style_consistency_score,
            issues=issues,
            recommendations=recommendations,
            approval_status=approval_status,
            evaluator_type=evaluator_type,
            evaluator_id=evaluator_id,
            evaluator_name=evaluator_name,
            evaluation_criteria={
                "prompt": prompt,
                "expected_resolution": expected_resolution,
                "style_reference": style_reference,
            },
            evaluation_data={
                "metadata": metadata,
                "processing_metadata": processing_metadata,
            }
        )
        
        self.db.add(quality_score_obj)
        self.db.commit()
        self.db.refresh(quality_score_obj)
        
        return quality_score_obj
    
    def evaluate_voice(
        self,
        asset_id: int,
        organization_id: int,
        expected_duration: Optional[float] = None,
        language: Optional[str] = None,
        pronunciation_model: Optional[str] = None,
        evaluator_type: str = "automated",
        evaluator_id: Optional[int] = None,
        evaluator_name: Optional[str] = None,
    ) -> MediaQualityScore:
        """
        Evaluate a voice/audio asset for quality.
        
        Args:
            asset_id: Asset ID
            organization_id: Organization ID
            expected_duration: Expected duration in seconds
            language: Language code
            pronunciation_model: Pronunciation evaluation model
            evaluator_type: Type of evaluator
            evaluator_id: Evaluator ID
            evaluator_name: Evaluator name
            
        Returns:
            MediaQualityScore with evaluation results
        """
        asset = self._get_asset(asset_id, organization_id)
        
        if asset is None:
            raise NotFoundError(resource_type="asset", resource_id=asset_id)
        
        metadata = asset.metadata or {}
        processing_metadata = asset.processing_metadata or {}
        
        # Evaluate duration
        duration_score = self._evaluate_duration(
            asset, expected_duration, metadata
        )
        
        # Evaluate audio quality
        audio_quality_score = self._evaluate_audio_quality(asset, metadata)
        
        # Evaluate pronunciation (if metadata available)
        pronunciation_score = self._evaluate_pronunciation(
            asset, language, pronunciation_model, metadata
        )
        
        # Calculate weighted overall score
        weights = self.DEFAULT_WEIGHTS[QualityEvaluationType.VOICE]
        quality_score = (
            duration_score * weights["duration"] +
            audio_quality_score * weights["audio_quality"] +
            pronunciation_score * weights["pronunciation"]
        )
        
        # Identify issues
        issues = self._identify_voice_issues(
            asset, duration_score, audio_quality_score, pronunciation_score
        )
        
        # Generate recommendations
        recommendations = self._generate_voice_recommendations(
            asset, issues, quality_score
        )
        
        # Determine approval status
        approval_status = self._determine_approval_status(quality_score)
        
        # Create quality score record
        quality_score_obj = MediaQualityScore(
            asset_id=asset_id,
            organization_id=organization_id,
            evaluation_type=QualityEvaluationType.VOICE,
            quality_score=quality_score,
            duration_score=duration_score,
            audio_quality_score=audio_quality_score,
            pronunciation_score=pronunciation_score,
            issues=issues,
            recommendations=recommendations,
            approval_status=approval_status,
            evaluator_type=evaluator_type,
            evaluator_id=evaluator_id,
            evaluator_name=evaluator_name,
            evaluation_criteria={
                "expected_duration": expected_duration,
                "language": language,
                "pronunciation_model": pronunciation_model,
            },
            evaluation_data={
                "metadata": metadata,
                "processing_metadata": processing_metadata,
            }
        )
        
        self.db.add(quality_score_obj)
        self.db.commit()
        self.db.refresh(quality_score_obj)
        
        return quality_score_obj
    
    def evaluate_storyboard(
        self,
        episode_id: int,
        organization_id: int,
        expected_scenes: Optional[int] = None,
        style_guide: Optional[Dict[str, Any]] = None,
        evaluator_type: str = "automated",
        evaluator_id: Optional[int] = None,
        evaluator_name: Optional[str] = None,
    ) -> MediaQualityScore:
        """
        Evaluate a storyboard for completeness and consistency.
        
        Args:
            episode_id: Episode ID
            organization_id: Organization ID
            expected_scenes: Expected number of scenes
            style_guide: Style guide reference
            evaluator_type: Type of evaluator
            evaluator_id: Evaluator ID
            evaluator_name: Evaluator name
            
        Returns:
            MediaQualityScore with evaluation results
        """
        episode = self._get_episode(episode_id, organization_id)
        
        if episode is None:
            raise NotFoundError(resource_type="episode", resource_id=episode_id)
        
        # Get storyboard assets for this episode
        storyboard_assets = self.db.query(Asset).filter(
            Asset.episode_id == episode_id,
            Asset.asset_type.in_(["image", "document"]),
            Asset.organization_id == organization_id
        ).all()
        
        metadata = episode.extra_data or {}
        
        # Evaluate completeness
        completeness_score = self._evaluate_completeness(
            storyboard_assets, expected_scenes, metadata
        )
        
        # Evaluate consistency
        consistency_score = self._evaluate_storyboard_consistency(
            storyboard_assets, style_guide, metadata
        )
        
        # Calculate weighted overall score
        weights = self.DEFAULT_WEIGHTS[QualityEvaluationType.STORYBOARD]
        quality_score = (
            completeness_score * weights["completeness"] +
            consistency_score * weights["consistency"]
        )
        
        # Identify issues
        issues = self._identify_storyboard_issues(
            storyboard_assets, completeness_score, consistency_score
        )
        
        # Generate recommendations
        recommendations = self._generate_storyboard_recommendations(
            storyboard_assets, issues, quality_score
        )
        
        # Determine approval status
        approval_status = self._determine_approval_status(quality_score)
        
        # Create quality score record
        quality_score_obj = MediaQualityScore(
            episode_id=episode_id,
            organization_id=organization_id,
            evaluation_type=QualityEvaluationType.STORYBOARD,
            quality_score=quality_score,
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            issues=issues,
            recommendations=recommendations,
            approval_status=approval_status,
            evaluator_type=evaluator_type,
            evaluator_id=evaluator_id,
            evaluator_name=evaluator_name,
            evaluation_criteria={
                "expected_scenes": expected_scenes,
                "style_guide": style_guide,
            },
            evaluation_data={
                "asset_count": len(storyboard_assets),
                "metadata": metadata,
            }
        )
        
        self.db.add(quality_score_obj)
        self.db.commit()
        self.db.refresh(quality_score_obj)
        
        return quality_score_obj
    
    def _get_asset(self, asset_id: int, organization_id: int) -> Optional[Asset]:
        """Get asset with tenant isolation."""
        return self.db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.organization_id == organization_id
        ).first()
    
    def _get_episode(self, episode_id: int, organization_id: int) -> Optional[Episode]:
        """Get episode with tenant isolation."""
        return self.db.query(Episode).filter(
            Episode.id == episode_id,
            Episode.organization_id == organization_id
        ).first()
    
    def _evaluate_prompt_adherence(
        self, 
        asset: Asset, 
        prompt: Optional[str], 
        metadata: Dict, 
        processing_metadata: Dict
    ) -> float:
        """Evaluate how well an image adheres to the prompt."""
        if not prompt:
            return 75.0  # Default score if no prompt
        
        # Check if generation metadata includes similarity score
        gen_metadata = processing_metadata.get("generation", {})
        similarity = gen_metadata.get("prompt_similarity", 0.75)
        
        return min(100.0, max(0.0, similarity * 100))
    
    def _evaluate_resolution(
        self, 
        asset: Asset, 
        expected_resolution: Optional[Tuple[int, int]], 
        metadata: Dict
    ) -> float:
        """Evaluate image resolution quality."""
        dimensions = asset.dimensions or metadata.get("dimensions", "")
        
        if not dimensions:
            return 50.0  # Unknown resolution
        
        try:
            width, height = map(int, dimensions.split("x"))
            
            if expected_resolution:
                exp_width, exp_height = expected_resolution
                # Score based on how close to expected
                width_ratio = min(width / exp_width, exp_width / width)
                height_ratio = min(height / exp_height, exp_height / height)
                return min(100.0, (width_ratio + height_ratio) / 2 * 100)
            else:
                # Score based on absolute quality
                if width >= 1920 and height >= 1080:
                    return 100.0
                elif width >= 1280 and height >= 720:
                    return 85.0
                elif width >= 800 and height >= 600:
                    return 70.0
                else:
                    return 50.0
        except (ValueError, AttributeError):
            return 50.0
    
    def _evaluate_style_consistency(
        self, 
        asset: Asset, 
        style_reference: Optional[Dict], 
        metadata: Dict
    ) -> float:
        """Evaluate style consistency against reference."""
        if not style_reference:
            # Check if asset has style metadata
            style_metadata = metadata.get("style", {})
            if style_metadata:
                return 80.0  # Has style info but no reference
            return 70.0  # No style info
        
        # Compare against style reference
        asset_style = metadata.get("style", {})
        
        matches = 0
        total = len(style_reference)
        
        for key, value in style_reference.items():
            if asset_style.get(key) == value:
                matches += 1
        
        return (matches / total * 100) if total > 0 else 70.0
    
    def _evaluate_duration(
        self, 
        asset: Asset, 
        expected_duration: Optional[float], 
        metadata: Dict
    ) -> float:
        """Evaluate audio duration against expected."""
        actual_duration = asset.duration_seconds or metadata.get("duration", 0)
        
        if not actual_duration:
            return 50.0
        
        if expected_duration:
            # Score based on how close to expected (within 20% is perfect)
            ratio = actual_duration / expected_duration
            if 0.8 <= ratio <= 1.2:
                return 100.0
            elif 0.5 <= ratio < 0.8 or 1.2 < ratio <= 1.5:
                return 75.0
            else:
                return 50.0
        
        # No expected duration - score based on reasonable range
        if 5 <= actual_duration <= 300:
            return 100.0
        elif 1 <= actual_duration < 5 or 300 < actual_duration <= 600:
            return 75.0
        else:
            return 50.0
    
    def _evaluate_audio_quality(self, asset: Asset, metadata: Dict) -> float:
        """Evaluate audio quality from metadata."""
        audio_metadata = metadata.get("audio", {})
        
        # Check for quality indicators
        sample_rate = audio_metadata.get("sample_rate", 0)
        bit_depth = audio_metadata.get("bit_depth", 0)
        channels = audio_metadata.get("channels", 1)
        
        score = 50.0
        
        if sample_rate >= 44100:
            score += 20
        elif sample_rate >= 22050:
            score += 10
        
        if bit_depth >= 16:
            score += 20
        elif bit_depth >= 8:
            score += 10
        
        if channels >= 2:
            score += 10
        
        return min(100.0, score)
    
    def _evaluate_pronunciation(
        self, 
        asset: Asset, 
        language: Optional[str], 
        pronunciation_model: Optional[str], 
        metadata: Dict
    ) -> float:
        """Evaluate pronunciation quality."""
        pronunciation_metadata = metadata.get("pronunciation", {})
        
        if not pronunciation_metadata:
            return 70.0  # Default if no pronunciation data
        
        accuracy = pronunciation_metadata.get("accuracy", 0.7)
        fluency = pronunciation_metadata.get("fluency", 0.7)
        
        return min(100.0, (accuracy + fluency) / 2 * 100)
    
    def _evaluate_completeness(
        self, 
        assets: List[Asset], 
        expected_scenes: Optional[int], 
        metadata: Dict
    ) -> float:
        """Evaluate storyboard completeness."""
        if not assets:
            return 0.0
        
        actual_count = len(assets)
        
        if expected_scenes:
            ratio = min(actual_count / expected_scenes, 1.0)
            return ratio * 100
        
        # Default: expect at least 3 scenes
        if actual_count >= 5:
            return 100.0
        elif actual_count >= 3:
            return 80.0
        else:
            return 50.0
    
    def _evaluate_storyboard_consistency(
        self, 
        assets: List[Asset], 
        style_guide: Optional[Dict], 
        metadata: Dict
    ) -> float:
        """Evaluate storyboard visual consistency."""
        if not assets:
            return 50.0
        
        # Check if all assets have consistent style tags
        styles = set()
        for asset in assets:
            tags = asset.tags or []
            style_tags = [t for t in tags if t.startswith("style:")]
            styles.update(style_tags)
        
        if len(styles) <= 2:
            return 100.0  # Very consistent
        elif len(styles) <= 4:
            return 80.0
        else:
            return 60.0
    
    def _identify_image_issues(
        self, 
        asset: Asset, 
        prompt_score: float, 
        resolution_score: float, 
        style_score: float
    ) -> List[str]:
        """Identify issues with an image asset."""
        issues = []
        
        if prompt_score < 70:
            issues.append("Low prompt adherence - generated image may not match requirements")
        
        if resolution_score < 70:
            issues.append(f"Resolution may be insufficient: {asset.dimensions}")
        
        if style_score < 70:
            issues.append("Style inconsistency detected")
        
        return issues
    
    def _identify_voice_issues(
        self, 
        asset: Asset, 
        duration_score: float, 
        quality_score: float, 
        pronunciation_score: float
    ) -> List[str]:
        """Identify issues with a voice asset."""
        issues = []
        
        if duration_score < 70:
            issues.append(f"Duration ({asset.duration_seconds}s) may not meet requirements")
        
        if quality_score < 70:
            issues.append("Audio quality below acceptable threshold")
        
        if pronunciation_score < 70:
            issues.append("Pronunciation accuracy needs improvement")
        
        return issues
    
    def _identify_storyboard_issues(
        self, 
        assets: List[Asset], 
        completeness_score: float, 
        consistency_score: float
    ) -> List[str]:
        """Identify issues with a storyboard."""
        issues = []
        
        if completeness_score < 70:
            issues.append(f"Storyboard incomplete - only {len(assets)} scenes")
        
        if consistency_score < 70:
            issues.append("Visual style inconsistent across scenes")
        
        return issues
    
    def _generate_image_recommendations(
        self, 
        asset: Asset, 
        issues: List[str], 
        quality_score: float
    ) -> List[str]:
        """Generate recommendations for improving image quality."""
        recommendations = []
        
        if quality_score < 85:
            recommendations.append("Consider regenerating with more detailed prompt")
        
        if asset.dimensions:
            try:
                w, h = map(int, asset.dimensions.split("x"))
                if w < 1920 or h < 1080:
                    recommendations.append("Increase resolution to at least 1920x1080")
            except ValueError:
                pass
        
        return recommendations
    
    def _generate_voice_recommendations(
        self, 
        asset: Asset, 
        issues: List[str], 
        quality_score: float
    ) -> List[str]:
        """Generate recommendations for improving voice quality."""
        recommendations = []
        
        if quality_score < 85:
            recommendations.append("Consider using higher quality voice model")
        
        if asset.duration_seconds and asset.duration_seconds < 5:
            recommendations.append("Audio too short - consider adding pauses or extending content")
        
        return recommendations
    
    def _generate_storyboard_recommendations(
        self, 
        assets: List[Asset], 
        issues: List[str], 
        quality_score: float
    ) -> List[str]:
        """Generate recommendations for improving storyboard."""
        recommendations = []
        
        if len(assets) < 5:
            recommendations.append("Add more scenes for complete story coverage")
        
        if quality_score < 85:
            recommendations.append("Review style guide compliance across all scenes")
        
        return recommendations
    
    def _determine_approval_status(self, quality_score: float) -> ApprovalStatus:
        """Determine approval status based on quality score."""
        if quality_score >= self.APPROVAL_THRESHOLDS["auto_approve"]:
            return ApprovalStatus.APPROVED
        elif quality_score >= self.APPROVAL_THRESHOLDS["requires_review"]:
            return ApprovalStatus.PENDING
        else:
            return ApprovalStatus.REJECTED
    
    def get_quality_score(
        self, 
        asset_id: Optional[int] = None, 
        episode_id: Optional[int] = None
    ) -> Optional[MediaQualityScore]:
        """Get the latest quality score for an asset or episode."""
        query = self.db.query(MediaQualityScore)
        
        if asset_id:
            query = query.filter(MediaQualityScore.asset_id == asset_id)
        elif episode_id:
            query = query.filter(MediaQualityScore.episode_id == episode_id)
        else:
            return None
        
        return query.order_by(MediaQualityScore.created_at.desc()).first()
