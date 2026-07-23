"""
Scene Composition Engine

Combines video/image assets with effects, transitions, and camera movements.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class TransitionType(str, Enum):
    """Types of video transitions."""
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    CROSS_DISSOLVE = "cross_dissolve"
    CUT = "cut"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"


class EffectType(str, Enum):
    """Types of video effects."""
    ZOOM = "zoom"
    PAN = "pan"
    KEN_BURNS = "ken_burns"
    OVERLAY = "overlay"
    TEXT_OVERLAY = "text_overlay"
    COLOR_CORRECTION = "color_correction"


@dataclass
class CameraMovement:
    """Camera movement definition for Ken Burns effect."""
    
    movement_type: str  # zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down
    start_x: float = 0.0  # Normalized 0-1
    start_y: float = 0.0  # Normalized 0-1
    end_x: float = 1.0  # Normalized 0-1
    end_y: float = 1.0  # Normalized 0-1
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "movement_type": self.movement_type,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "end_x": self.end_x,
            "end_y": self.end_y,
            "duration": self.duration
        }


@dataclass
class VideoEffect:
    """Video effect definition."""
    
    effect_type: EffectType
    parameters: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_type": self.effect_type.value,
            "parameters": self.parameters,
            "start_time": self.start_time,
            "duration": self.duration
        }


@dataclass
class SceneTransition:
    """Transition between scenes."""
    
    transition_type: TransitionType
    duration: float = 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_type": self.transition_type.value,
            "duration": self.duration,
            "parameters": self.parameters
        }


@dataclass
class ComposedScene:
    """A scene with all composition elements applied."""
    
    scene_id: str
    asset_key: str
    duration: float
    resolution: str = "1920x1080"
    camera_movement: Optional[CameraMovement] = None
    effects: List[VideoEffect] = field(default_factory=list)
    transition_in: Optional[SceneTransition] = None
    transition_out: Optional[SceneTransition] = None
    overlay_elements: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "asset_key": self.asset_key,
            "duration": self.duration,
            "resolution": self.resolution,
            "camera_movement": self.camera_movement.to_dict() if self.camera_movement else None,
            "effects": [e.to_dict() for e in self.effects],
            "transition_in": self.transition_in.to_dict() if self.transition_in else None,
            "transition_out": self.transition_out.to_dict() if self.transition_out else None,
            "overlay_elements": self.overlay_elements
        }


class SceneComposer:
    """
    Composes video scenes with effects and transitions.
    
    Responsibilities:
    - Combine image/video assets
    - Apply camera movement simulation
    - Apply zoom/pan effects
    - Apply transitions
    - Generate FFmpeg filter graph
    """
    
    def __init__(self, default_resolution: str = "1920x1080"):
        self.default_resolution = default_resolution
        self.logger = logging.getLogger("rendering.composition")
    
    def compose_scene(
        self,
        scene_data: Dict[str, Any],
        asset_key: str
    ) -> ComposedScene:
        """
        Compose a single scene from configuration.
        
        Args:
            scene_data: Scene configuration dictionary
            asset_key: Storage key for the source asset
            
        Returns:
            ComposedScene with all effects applied
        """
        import uuid
        
        scene_id = scene_data.get("scene_id", str(uuid.uuid4()))
        duration = scene_data.get("duration", 5.0)
        resolution = scene_data.get("resolution", self.default_resolution)
        
        composed = ComposedScene(
            scene_id=scene_id,
            asset_key=asset_key,
            duration=duration,
            resolution=resolution
        )
        
        # Apply camera movement if specified
        if "camera_movement" in scene_data:
            composed.camera_movement = self._parse_camera_movement(
                scene_data["camera_movement"]
            )
        
        # Apply effects
        for effect_data in scene_data.get("effects", []):
            effect = self._parse_effect(effect_data)
            if effect:
                composed.effects.append(effect)
        
        # Apply transitions
        if "transition_in" in scene_data:
            composed.transition_in = self._parse_transition(scene_data["transition_in"])
        if "transition_out" in scene_data:
            composed.transition_out = self._parse_transition(scene_data["transition_out"])
        
        # Add overlay elements
        composed.overlay_elements = scene_data.get("overlays", [])
        
        return composed
    
    def generate_filter_graph(
        self,
        scenes: List[ComposedScene],
        output_resolution: str = "1920x1080"
    ) -> str:
        """
        Generate FFmpeg filter complex string for scene composition.
        
        Args:
            scenes: List of composed scenes
            output_resolution: Target output resolution
            
        Returns:
            FFmpeg filter_complex string
        """
        filters = []
        inputs = []
        current_output = "[0:v]"
        
        width, height = self._parse_resolution(output_resolution)
        
        for idx, scene in enumerate(scenes):
            scene_filters = []
            
            # Scale input if needed
            if idx == 0:
                scene_filters.append(f"scale={width}:{height}")
            
            # Apply camera movement (Ken Burns effect)
            if scene.camera_movement:
                zoom_filter = self._generate_zoom_filter(scene.camera_movement, scene.duration)
                if zoom_filter:
                    scene_filters.append(zoom_filter)
            
            # Apply effects
            for effect in scene.effects:
                effect_filter = self._generate_effect_filter(effect, scene.duration)
                if effect_filter:
                    scene_filters.append(effect_filter)
            
            # Apply fade transitions
            if scene.transition_in:
                fade_filter = self._generate_fade_filter(
                    scene.transition_in,
                    "in",
                    0
                )
                if fade_filter:
                    scene_filters.append(fade_filter)
            
            if scene.transition_out:
                fade_filter = self._generate_fade_filter(
                    scene.transition_out,
                    "out",
                    scene.duration - scene.transition_out.duration
                )
                if fade_filter:
                    scene_filters.append(fade_filter)
            
            if scene_filters:
                filter_str = ",".join(scene_filters)
                if idx < len(scenes) - 1:
                    next_input = f"[v{idx}]"
                    filters.append(f"{current_output}{filter_str}{next_input}")
                    current_output = next_input
                else:
                    filters.append(f"{current_output}{filter_str}[out]")
        
        # Handle cross-dissolve transitions between scenes
        if len(scenes) > 1:
            filters = self._add_cross_dissolves(filters, scenes)
        
        return ";".join(filters) if filters else ""
    
    def _parse_camera_movement(self, data: Dict[str, Any]) -> CameraMovement:
        """Parse camera movement from configuration."""
        return CameraMovement(
            movement_type=data.get("type", "zoom_in"),
            start_x=data.get("start_x", 0.0),
            start_y=data.get("start_y", 0.0),
            end_x=data.get("end_x", 1.0),
            end_y=data.get("end_y", 1.0),
            duration=data.get("duration", 0.0)
        )
    
    def _parse_effect(self, data: Dict[str, Any]) -> Optional[VideoEffect]:
        """Parse video effect from configuration."""
        effect_type_str = data.get("type", "")
        try:
            effect_type = EffectType(effect_type_str)
        except ValueError:
            self.logger.warning(f"Unknown effect type: {effect_type_str}")
            return None
        
        return VideoEffect(
            effect_type=effect_type,
            parameters=data.get("parameters", {}),
            start_time=data.get("start_time", 0.0),
            duration=data.get("duration", 0.0)
        )
    
    def _parse_transition(self, data: Dict[str, Any]) -> SceneTransition:
        """Parse transition from configuration."""
        transition_type_str = data.get("type", "cut")
        try:
            transition_type = TransitionType(transition_type_str)
        except ValueError:
            transition_type = TransitionType.CUT
        
        return SceneTransition(
            transition_type=transition_type,
            duration=data.get("duration", 1.0),
            parameters=data.get("parameters", {})
        )
    
    def _parse_resolution(self, resolution: str) -> Tuple[int, int]:
        """Parse resolution string to width x height."""
        parts = resolution.split("x")
        if len(parts) != 2:
            return 1920, 1080
        return int(parts[0]), int(parts[1])
    
    def _generate_zoom_filter(
        self,
        movement: CameraMovement,
        duration: float
    ) -> str:
        """Generate FFmpeg zoompan filter for camera movement."""
        # Simplified zoompan filter generation
        zoom_start = 1.0
        zoom_end = 1.5 if movement.movement_type.startswith("zoom_in") else (
            0.7 if movement.movement_type.startswith("zoom_out") else 1.0
        )
        
        d_expr = f"if(lte(t,{duration}),{zoom_start}+({zoom_end}-{zoom_start})*t/{duration},{zoom_end})"
        
        return f"zoompan=z='{d_expr}':d=1:x='iw/2':y='ih/2'"
    
    def _generate_effect_filter(
        self,
        effect: VideoEffect,
        scene_duration: float
    ) -> Optional[str]:
        """Generate FFmpeg filter for a specific effect."""
        if effect.effect_type == EffectType.COLOR_CORRECTION:
            params = effect.parameters
            brightness = params.get("brightness", 0)
            contrast = params.get("contrast", 1)
            saturation = params.get("saturation", 1)
            return f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
        
        elif effect.effect_type == EffectType.OVERLAY:
            # Overlay handled separately
            return None
        
        return None
    
    def _generate_fade_filter(
        self,
        transition: SceneTransition,
        fade_type: str,
        start_time: float
    ) -> Optional[str]:
        """Generate FFmpeg fade filter."""
        if transition.transition_type not in [
            TransitionType.FADE_IN,
            TransitionType.FADE_OUT
        ]:
            return None
        
        color = transition.parameters.get("color", "black")
        return f"fade={fade_type}:start_time={start_time}:duration={transition.duration}:color={color}"
    
    def _add_cross_dissolves(
        self,
        filters: List[str],
        scenes: List[ComposedScene]
    ) -> List[str]:
        """Add cross-dissolve transitions between scenes."""
        # Simplified implementation - full implementation would use
        # xfade filter with proper timing
        result = filters.copy()
        
        for idx in range(len(scenes) - 1):
            scene_a = scenes[idx]
            scene_b = scenes[idx + 1]
            
            # Check if cross-dissolve is needed
            if scene_a.transition_out and \
               scene_a.transition_out.transition_type == TransitionType.CROSS_DISSOLVE:
                # Would add xfade filter here
                duration = scene_a.transition_out.duration
                self.logger.debug(
                    f"Cross-dissolve between scene {idx} and {idx + 1}, "
                    f"duration: {duration}s"
                )
        
        return result


__all__ = [
    "TransitionType",
    "EffectType",
    "CameraMovement",
    "VideoEffect",
    "SceneTransition",
    "ComposedScene",
    "SceneComposer",
]
