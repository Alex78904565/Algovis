from .core.math import Function, ApplyFunction, ApplyDefinition, Substitute
from .core.trees import RecursiveTree, NodeState
from .core.induction import MonotonicVisualizer, InductionStep
from .core.dominoes import DominoGeometry
from .core.structures import (CellState, StateCell, StateRow, StateCellStyle, CallNode,
    DEFAULT_STATE_CELL_STYLE, DPTable, DPWorkflow, HashTable, GraphVis)
from .core.state_space import StateSpaceVisualizer, StateParameter, BinaryStateVector
from .core.pseudocode import PseudocodePanel
from .core.comparison import AlgorithmComparison, RecurrenceComparison, TopDownDPBridge
from .core.decisions import DecisionFanout
from .core.bellman import BellmanDerivation
from .core.correctness import InductiveProof, MonotoneCall
from .core.workflows import (
    BitLengthRuntime, ChoiceRecovery, RecursionMemoComparison, StateReframing,
    ValueScan,
)
from .core.story import (
    CapacityBag, CapacityChoiceStory, StoryBeat, StoryDecision, StoryItem,
    StoryItemSpec, ThiefCharacter,
)
from .theme import (
    AlgovisSpacing, AlgovisTheme, DEFAULT_SPACING, DEFAULT_THEME, LIGHT_THEME,
    WARM_THEME, NIGHTCLUB_THEME,
)
from .presentation import Slide, SlideLayout, SlideRegion, SlideScene, SlideSceneMixin, slide_scene
from .fitting import FitPolicy
from .composition import (SlideObject, SlideView, ColumnSlide, SplitSlide,
                          EquationSlide, ProofSlide, ViewTransition, LayoutOverrideWarning)
from .view_timeline import (CanvasSlide, ViewScene, ViewSceneMixin, Reveal, Retire, Move, CopyInto,
                            Replace, ReplaceShape, Draw, WriteView, Grow, DrawArrow,
                            Together, Then, Stagger, Later)
from .layout import ColumnLayout, LessonStyle, LessonTypography
from .frames import (
    DEFAULT_FRAME_STYLE, CaseEquation, ChapterMarker, ComparisonFrame, EquationFrame,
    LessonFrameStyle, PanelFrame, ProofFrame,
)
from .narration import NarrationCue, NarrationTrack
from .continuity import SectionHandoff
from .core.math_row import MathRow
from .core.proof import Proof, ProofRow
from .animation import LessonAnimation,SceneSequence
from .objects import TextObject, Equation
from .core.sequences import StateSequence, FloatingCharacter
from .core.teaching import MathStack,ObjectRow,BracedGroup,FixedGrowthPlot,LogRuntimeComparison,ServerRacks,Worksheet,TreeAnnotation,InductionChain
from .core.illustrated import IllustratedProp,IllustratedBag,CapacityMeter,IllustratedItem,ItemCollection
from .core.routes import CityMap,RoadTripSimulation,RouteTrace
from .core.recap import Checklist
from .scene_layouts import (CenteredScene, ListScene, BlockScene, SlotScene, DiagramScene, TreeScene, DefinitionScene,
                            MapScene,DerivationScene,RecurrenceScene, ComparisonScene,IllustratedProblemScene,PairedScene,SelectionScene,ConversionScene,AnalysisScene,RecapScene, StoryScene,TreeExplanationScene,TreeArrayScene)
from .semantics import SemanticProperties, SemanticChange, set_semantics
from .storyboard import (
    ACTION_VERBS, ATTENTION_STYLES, ENTRY_STYLES, EXIT_STYLES,
    SEMANTIC_ROLES, StoryAction, StoryAnimation,
    StoryBeat as AnimationBeat, StoryObject, Storyboard,
    StoryboardSyntaxError, parse_storyboard,
)
from .lesson import (
    AlgorithmLessonScene, BellmanSpec, ComparisonSpec, ProblemLesson, ProofSpec,
)
from .utils.effects import DeferredAnimation, FocusBox, Highlight, Pulse, ReplaceContent
from .utils.layout import PanelLayout, SmartBulletedList

__version__ = "0.1.0"
