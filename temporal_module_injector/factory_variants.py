import services
import sims4.resources
from sims4.resources import Types
from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableMapping, TunableList, \
    TunableTuple, TunableEnumEntry, OptionalTunable, TunablePercent, Tunable, TunableReference, TunableSet, \
    TunableRange, TunableVariant, TunableSimMinute
from sims4.tuning.tunable_base import GroupNames
from sims.pregnancy.pregnancy_enums import PregnancyOrigin
from relationships.relationship_tracker_tuning import DefaultGenealogyLink
from traits.traits import Trait
from objects.components.state import ObjectStateValue
from bucks.bucks_enums import BucksType, BucksTrackerType
from drama_scheduler.drama_node import DramaNodeScoringBucket
from scheduler_utils import TunableDayAvailability
from drama_scheduler.drama_scheduler import NodeSelectionOption
from statistics.commodity import Commodity
from away_actions.away_actions import AwayAction
from teleport.teleport_enums import TeleportStyle
from interactions.utils.animation_reference import TunableAnimationReference
from sims4.tuning.geometric import TunableDistanceSquared
from tunable_multiplier import TunableMultiplier
from tunable_utils.tested_list import TunableTestedList
from vfx import PlayEffect
from interactions.utils.loot import LootActions
from sims4.localization import TunableLocalizedString
from traits.traits import TraitBuffReplacementPriority
from buffs.tunable import TunableBuffReference
from whims.whims_tracker import WhimsTracker
from interactions.utils.tunable import TunableStatisticAdvertisements
import enum


# Injection target can be a module path (e.g. class name/attr/etc.)
# And can be a tuning reference (ex: to a buff) with an attr target
# (ex: _loot_on_instance)
class InjectionTargetType(enum.Int):
    INVALID = 0
    MODULE_PATH = 1
    TUNING_REF_ATTR = 2


class FactoryVariantBase(HasTunableSingletonFactory, AutoFactoryInit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._injection_target_type = InjectionTargetType.INVALID
    
    def get_injection_target_type(self):
        return self._injection_target_type
    
    FACTORY_TUNABLES = {
        'is_xml_usable_variant': Tunable(
            description='Design safeguard for determining whether a variant should be something you can use '
                        'in the XML. Most variants will be True, but some are just parent classes to reduce '
                        'boilerplate. This is mainly to make it clearer at a glance which variants should be '
                        'supported in snippet tuning. That I think this makes sense to implement is probably '
                        'a sign of poor design, but that is for future me to get mad about when he later wonders '
                        'what I was thinking. [Addendum: Its true, idk what I was thinking.]',
            tunable_type=bool, 
            default=False
        )
    }


# Base factory class used for module variants
# Each derived variant should lock injection_target_str
# with a path, if relevant, or '' if no path to use.
# This is so the xml doesn't need to take in an open-ended str,
# which is kind of dangerous to do, partly for security
# reasons and partly for human error reasons.
# While still allowing flexible paths for modules and their attrs.
# (without needing lots of boilerplate enum and dict, or the like)
class ModuleVariantBase(FactoryVariantBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._injection_target_type = InjectionTargetType.MODULE_PATH
    
    FACTORY_TUNABLES = {
        'injection_target_str': Tunable(
            description='The target path of the injection, including module path, class name, and class attribute. '
                        'Pieces of path are separated by a :, i.e. '
                        'sims.pregnancy.pregnancy_tracker:PregnancyTracker:PREGNANCY_ORIGIN_MODIFIERS. '
                        'Sometimes a path may need to go into layers of attributes, but we have to account for various'
                        ' scenarios for this in the code if so.',
            tunable_type=str, 
            default=''
        )
    }


# Base factory class for tuning ref variants
# Each derived variant should lock injection_target_attr_str
# with an attr, if relevant, or '' if no attr to use.
# If attr paths are desired (ex: outcome > actions > loot_list)
# this needs to be supported in the code. Currently, the code only
# supports a top-level attr in a tuning ref (ex: _loot_on_instance in a buff).
class TuningRefVariantBase(FactoryVariantBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._injection_target_type = InjectionTargetType.TUNING_REF_ATTR
    
    FACTORY_TUNABLES = {
        'injection_target_attr_str': Tunable(
            description='The attr to be modified within the tuning ref (ex: _loot_on_instance in a Buff).',
            tunable_type=str, 
            default=''
        )
    }


# sims.pregnancy.pregnancy_tracker.PregnancyTracker

class PregnancyOriginModifiers(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='Define any modifiers that, given the origination of the pregnancy, affect certain aspects'
                        ' of the generated offspring.',
            key_type=TunableEnumEntry(
                description='The origin of the pregnancy.', 
                tunable_type=PregnancyOrigin, 
                default=PregnancyOrigin.DEFAULT, 
                pack_safe=True
            ), 
            value_type=TunableTuple(
                description='The aspects of the pregnancy modified specifically for the specified origin.', 
                default_relationships=TunableTuple(
                    description='Override default relationships for the parents.', 
                    father_override=OptionalTunable(
                        description='If set, override default relationships for the father.', 
                        tunable=TunableEnumEntry(
                            description='The default relationships for the father.', 
                            tunable_type=DefaultGenealogyLink, 
                            default=DefaultGenealogyLink.FamilyMember
                        )
                    ), 
                    mother_override=OptionalTunable(
                        description='If set, override default relationships for the mother.', 
                        tunable=TunableEnumEntry(
                            description='The default relationships for the mother.', 
                            tunable_type=DefaultGenealogyLink, 
                            default=DefaultGenealogyLink.FamilyMember
                        )
                    )
                ), 
                trait_entries=TunableList(
                    description='Sets of traits that might be randomly applied to each generated offspring. '
                                'Each group is individually randomized.',
                    tunable=TunableTuple(
                        description='A set of random traits. Specify a chance that a trait from the group is selected,'
                                    ' and then specify a set of traits. Only one trait from this group may be '
                                    'selected. If the chance is less than 100%, no traits could be selected.',
                        chance=TunablePercent(
                            description='The chance that a trait from this set is selected.', 
                            default=100
                        ), 
                        traits=TunableList(
                            description='The set of traits that might be applied to each generated offspring. '
                                        'Specify a weight for each trait compared to other traits in the same set.',
                            tunable=TunableTuple(
                                description='A weighted trait that might be applied to the generated offspring. '
                                            'The weight is relative to other entries within the same set.',
                                weight=Tunable(
                                    description='The relative weight of this trait compared to other traits '
                                                'within the same set.',
                                    tunable_type=float, 
                                    default=1
                                ), 
                                trait=Trait.TunableReference(
                                    description='A trait that might be applied to the generated offspring.', 
                                    pack_safe=True
                                )
                            )
                        )
                    )
                )
            )
        ),
        'locked_args': {
            'injection_target_str': 'sims.pregnancy.pregnancy_tracker:PregnancyTracker:PREGNANCY_ORIGIN_MODIFIERS',
            'is_xml_usable_variant': True
        }
    }


# sims.baby.baby_tuning.BabyTuning

class BabyBassinetDefinitionMap(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='The corresponding mapping for each definition pair of empty bassinet and bassinet with baby'
                        ' inside. The reason we need to have two of definitions is one is deletable and the other '
                        'one is not.',
            key_name='Baby', 
            key_type=TunableReference(
                description='The definition of an object that is a bassinet containing a fully functioning baby.', 
                manager=services.definition_manager(), 
                pack_safe=True
            ), 
            value_name='EmptyBassinet', 
            value_type=TunableReference(
                description='The definition of an object that is an empty bassinet.', 
                manager=services.definition_manager(), 
                pack_safe=True
            )
        ),
        'locked_args': {
            'injection_target_str': 'sims.baby.baby_tuning:BabyTuning:BABY_BASSINET_DEFINITION_MAP',
            'is_xml_usable_variant': True
        }
    }


class BabyClothStateMap(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='A mapping from current BABY_CLOTH_STATE value to cloth string.', 
            key_type=ObjectStateValue.TunableReference(
                description='The state value that will be looked for on the baby.', 
                pack_safe=True
            ), 
            value_type=Tunable(
                description='The cloth that will be used if the state value key is present.', 
                tunable_type=str, 
                default=''
            )
        ),
        'locked_args': {
            'injection_target_str': 'sims.baby.baby_tuning:BabyTuning:BABY_CLOTH_STATE_MAP',
            'is_xml_usable_variant': True
        }
    }


class BabyDefaultBassinets(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='A list of trait to default bassinet definitions. This is used when generating default '
                        'bassinets for specific babies. The list is evaluated in order. Should no element be selected, '
                        'an entry from BABY_BASSINET_DEFINITION_MAP is selected instead.',
            tunable=TunableTuple(
                description='Should the baby have any of the specified traits, select a bassinet from the list'
                            ' of bassinets.',
                traits=TunableList(
                    description='This entry is selected should the Sim have any of these traits.', 
                    tunable=Trait.TunableReference(pack_safe=True)
                ), 
                bassinets=TunableList(
                    description='Should this entry be selected, a random bassinet from this list is chosen.', 
                    tunable=TunableReference(manager=services.definition_manager(), pack_safe=True)
                )
            )
        ),
        'locked_args': {
            'injection_target_str': 'sims.baby.baby_tuning:BabyTuning:BABY_DEFAULT_BASSINETS',
            'is_xml_usable_variant': True
        }
    }


class BabyDefaultBassinetsExistingTraitAsKey(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='Bassinet definitions that should be added to an existing default bassinet mapping based '
                        'on the tuned trait.',
            tunable=TunableReference(manager=services.definition_manager(), pack_safe=True)
        ),
        'key_ref': Trait.TunableReference(
            description='Reference to a Trait tuning instance used to determine which default bassinet mapping '
                        'should be injected to.',
            pack_safe=True
        ),
        'key_str': Tunable(
            description='Name of key, if needed (e.g. in case of ImmutableSlots), to be parsed into attr name.',
            tunable_type=str, 
            default=''
        ),
        'value_str': Tunable(
            description='Name of value, if needed (e.g. in case of ImmutableSlots), to be parsed into attr name.',
            tunable_type=str, 
            default=''
        ),
        'locked_args': {
            'injection_target_str': 'sims.baby.baby_tuning:BabyTuning:BABY_DEFAULT_BASSINETS', 
            'key_str': 'traits', 
            'value_str': 'bassinets',
            'is_xml_usable_variant': True
        }
    }


# bucks.bucks_utils.BucksUtils

class BuckTypeToTrackerMap(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='Maps a buck type to the tracker that uses that bucks type.', 
            key_type=TunableEnumEntry(
                tunable_type=BucksType, 
                default=BucksType.INVALID, 
                invalid_enums=BucksType.INVALID, 
                pack_safe=True
            ), 
            key_name='Bucks Type', 
            value_type=BucksTrackerType, 
            value_name='Bucks Tracker'
        ),
        'locked_args': {
            'injection_target_str': 'bucks.bucks_utils:BucksUtils:BUCK_TYPE_TO_TRACKER_MAP',
            'is_xml_usable_variant': True
        }
    }


# clubs.club_tuning.ClubTunables

class ClubTraits(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableSet(
            description='A set of traits available for use with club rules and admission criteria. '
                        'Consumed by UI when populating options for club modification.',
            tunable=Trait.TunableReference(pack_safe=True), 
            tuning_group=GroupNames.UI
        ),
        'locked_args': {
            'injection_target_str': 'clubs.club_tuning:ClubTunables:CLUB_TRAITS',
            'is_xml_usable_variant': True
        }
    }


class ClubSeedsSecondary(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableSet(
            description='A set of ClubSeeds that will be used to create new Clubs when there are fewer than the '
                        'minimum number left in the world.',
            tunable=TunableReference(
                manager=services.get_instance_manager(sims4.resources.Types.CLUB_SEED), 
                pack_safe=True
            )
        ),
        'locked_args': {
            'injection_target_str': 'clubs.club_tuning:ClubTunables:CLUB_SEEDS_SECONDARY',
            'is_xml_usable_variant': True
        }
    }


# drama_scheduler.drama_scheduler.DramaScheduleService

class BucketScoringRules(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='A mapping between the different possible scoring buckets, and rules about scheduling '
                        'nodes in that bucket.',
            key_type=TunableEnumEntry(
                description='The bucket that we are going to score on startup.', 
                tunable_type=DramaNodeScoringBucket, 
                default=DramaNodeScoringBucket.DEFAULT
            ), 
            value_type=TunableTuple(
                description='Rules about scheduling this drama node.', 
                days=TunableDayAvailability(), 
                score_if_no_nodes_are_scheduled=Tunable(
                    description='If checked then if no drama nodes are scheduled from this bucket then we will try and '
                                'score and schedule this bucket even if we are not expected to score nodes on this '
                                'day.',
                    tunable_type=bool, 
                    default=False
                ), 
                number_to_schedule=TunableVariant(
                    description='How many actual nodes should we schedule from this bucket.', 
                    based_on_household=TunableTuple(
                        description='Select the number of nodes based on the number of Sims in the active household.', 
                        locked_args={'option': NodeSelectionOption.BASED_ON_HOUSEHOLD}
                    ), 
                    fixed_amount=TunableTuple(
                        description='Select the number of nodes based on a static number.', 
                        number_of_nodes=TunableRange(
                            description='The number of nodes that we will always try and schedule from this bucket.', 
                            tunable_type=int, default=1, 
                            minimum=0
                        ), 
                        locked_args={'option': NodeSelectionOption.STATIC_AMOUNT}
                    )
                ), 
                refresh_nodes_on_scheduling=Tunable(
                    description='If checked, any existing scheduled nodes for this particular scoring bucket will be'
                                ' canceled before scheduling new nodes.',
                    tunable_type=bool, 
                    default=False
                )
            )
        ),
        'locked_args': {
            'injection_target_str': 'drama_scheduler.drama_scheduler:DramaScheduleService:BUCKET_SCORING_RULES',
            'is_xml_usable_variant': True
        }
    }


# ensemble.ensemble.Ensemble

class EnsemblePriorities(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='A list of ensembles by priority.  Those with higher guids will be considered more important '
                        'than those with lower guids. IMPORTANT: All ensemble types must be referenced in this list.',
            tunable=TunableReference(
                description='A single ensemble.', 
                manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE), 
                pack_safe=True
            )
        ),
        'locked_args': {
            'injection_target_str': 'ensemble.ensemble:Ensemble:ENSEMBLE_PRIORITIES',
            'is_xml_usable_variant': True
        }
    }


# statistics.lifestyle_service.LifestyleService

class TraitReferenceList(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='A list of trait references.', 
            tunable=TunableReference(
                description='A reference to a trait tuning.', 
                manager=services.get_instance_manager(Types.TRAIT), 
                pack_safe=True
            )
        ),
        'locked_args': {
            'injection_target_str': ''
        }
    }


class Lifestyles(TraitReferenceList):
    FACTORY_TUNABLES = {
        'locked_args': {
            'injection_target_str': 'statistics.lifestyle_service:LifestyleService:LIFESTYLES',
            'is_xml_usable_variant': True
        }
    }


class HiddenLifestyles(TraitReferenceList):
    FACTORY_TUNABLES = {
        'locked_args': {
            'injection_target_str': 'statistics.lifestyle_service:LifestyleService:HIDDEN_LIFESTYLES',
            'is_xml_usable_variant': True
        }
    }


# sims.sim_info.SimInfo

class DefaultAwayAction(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='Map of commodities to away action. When the default away action is asked for we look at the'
                        ' ad data of each commodity and select the away action linked to the commodity that is '
                        'advertising the highest.',
            key_type=Commodity.TunableReference(
                description='The commodity that we will look at the advertising value for.', 
                pack_safe=True
            ), 
            value_type=AwayAction.TunableReference(
                description='The away action that will applied if the key is the highest advertising commodity of '
                            'the ones listed.',
                pack_safe=True
            )
        ),
        'locked_args': {
            'injection_target_str': 'sims.sim_info:SimInfo:DEFAULT_AWAY_ACTION',
            'is_xml_usable_variant': True
        }
    }


class AwayActionsExistingKey(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='A list of away actions that are available for the player to select from and apply to the sim.', 
            tunable=AwayAction.TunableReference(pack_safe=True)
        ),
        'key_ref': TunableReference(
            description='The interaction key that is used to determine which set of away actions should be added to.', 
            manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)
        ),
        'key_str': Tunable(
            description='Name of key, if needed (e.g. in case of ImmutableSlots), to be parsed into attr name.',
            tunable_type=str, 
            default=''
        ),
        'value_str': Tunable(
            description='Name of value, if needed (e.g. in case of ImmutableSlots), to be parsed into attr name.',
            tunable_type=str, 
            default=''
        ),
        'locked_args': {
            'injection_target_str': 'sims.sim_info:SimInfo:AWAY_ACTIONS',
            'key_str': '',
            'value_str': '',
            'is_xml_usable_variant': True
        }
    }


# teleport.teleport_tuning.TeleportTuning

class TeleportDataMapping(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='A mapping from a a teleport style to the animation, xevt and vfx data that the Sim will '
                        'use when a teleport is triggered.',
            key_type=TunableEnumEntry(
                description='Teleport style.', 
                tunable_type=TeleportStyle, 
                default=TeleportStyle.NONE, 
                pack_safe=True, 
                invalid_enums=(TeleportStyle.NONE,)
            ), 
            value_type=TunableTuple(
                description='Animation and vfx data data to be used when the teleport is triggered.', 
                animation_outcomes=TunableList(
                    description='One of these animations will be played when the teleport happens, and '
                                'weights + modifiers can be used to determine exactly which animation is '
                                'played based on tests.',
                    tunable=TunableTuple(
                        description='A pairing of animation and weights that determine which animation is played '
                                    'when using this teleport style.  Any tests in the multipliers will be using '
                                    'the context from the interaction that plays the teleportStyle.',
                        animation=TunableAnimationReference(
                            description='Reference of the animation to be played when the teleport is triggered.', 
                            pack_safe=True, 
                            callback=None
                        ), 
                        weight=TunableMultiplier.TunableFactory(
                            description='A tunable list of tests and multipliers to apply to the weight of the '
                                        'animation that is selected for the teleport.'
                        )
                    )
                ), 
                start_teleport_vfx_xevt=Tunable(
                    description='Xevent when the Sim starts teleporting to play the fade out VFX.', 
                    tunable_type=int, 
                    default=100
                ), 
                start_teleport_fade_sim_xevt=Tunable(
                    description='Xevent when the sim starts teleporting to start the fading of the Sim.', 
                    tunable_type=int, 
                    default=100
                ), 
                fade_out_effect=OptionalTunable(
                    description='If enabled, play an additional VFX on the specified  fade_out_xevt when fading out '
                                'the Sim.',
                    tunable=PlayEffect.TunableFactory(
                        description='The effect to play when the Sim fades out before actual changing its position. '
                                    'This effect will not be parented to the Sim, but instead will play on the '
                                    'bone position without attachment.  This will guarantee the VFX will not become '
                                    'invisible as the Sim disappears. i.e. Vampire bat teleport spawns VFX on the '
                                    'Sims position'
                    ), 
                    enabled_name='play_effect', 
                    disabled_name='no_effect'
                ), 
                tested_fade_out_effect=TunableTestedList(
                    description='A list of possible fade out effects to play tested against the Sim that is '
                                'teleporting.',
                    tunable_type=PlayEffect.TunableFactory(
                        description='The effect to play when the Sim fades out before actual changing its position. '
                                    'This effect will not be parented to the Sim, but instead will play on the bone '
                                    'position without attachment.  This will guarantee the VFX will not become '
                                    'invisible as the Sim disappears. i.e. Vampire bat teleport spawns VFX on '
                                    'the Sims position'
                    )
                ), 
                teleport_xevt=Tunable(
                    description='Xevent where the teleport should happen.', 
                    tunable_type=int, 
                    default=100
                ), 
                teleport_effect=OptionalTunable(
                    description='If enabled, play an additional VFX on the specified teleport_xevt when the teleport '
                                '(actual movement of the position of the Sim) happens.',
                    tunable=PlayEffect.TunableFactory(
                        description='The effect to play when the Sim is teleported.'
                    ), 
                    enabled_name='play_effect', 
                    disabled_name='no_effect'
                ), 
                teleport_min_distance=TunableDistanceSquared(
                    description='Minimum distance between the Sim and its target to trigger a teleport.  If the '
                                'distance is lower than this value, the Sim will run a normal route.',
                    default=5.0
                ), 
                teleport_cost=OptionalTunable(
                    description='If enabled, the teleport will have an statistic cost every time its triggered.', 
                    tunable=TunableTuple(
                        description='Cost and statistic to charge for a teleport event.', 
                        teleport_statistic=TunableReference(
                            description='The statistic we are operating on when a teleport happens.', 
                            manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), 
                            pack_safe=True
                        ), 
                        cost=TunableRange(
                            description='On teleport, subtract the teleport_statistic by this amount.', 
                            tunable_type=int, 
                            default=1, 
                            minimum=0
                        ), 
                        cost_is_additive=Tunable(
                            description='If checked, the cost is additive.  Rather than deducting the cost, it will be '
                                        'added to the specified teleport statistic.  Additionally, cost will be '
                                        'checked against the max value of the statistic rather than the minimum value '
                                        'when determining if the cost is affordable',
                            tunable_type=bool, 
                            default=False
                        )
                    ), 
                    disabled_name='no_teleport_cost', 
                    enabled_name='specify_cost'
                ), 
                fade_duration=TunableSimMinute(
                    description='Default fade time (in sim minutes) for the fading of the Sim to happen.', 
                    default=0.5
                )
            )
        ),
        'locked_args': {
            'injection_target_str': 'teleport.teleport_tuning:TeleportTuning:TELEPORT_DATA_MAPPING',
            'is_xml_usable_variant': True
        }
    }


# traits.trait_tracker.TraitTracker

class TraitInheritance(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='Define how specific traits are transferred to offspring. Define keys of sets of traits '
                        'resulting in the assignment of another trait, weighted against other likely outcomes.',
            tunable=TunableTuple(
                description='A set of trait requirements and outcomes.', 
                parent_a_whitelist=TunableList(
                    description='Parent A must have ALL these traits in order to generate this outcome.', 
                    tunable=Trait.TunableReference(pack_safe=True)
                ), 
                parent_a_blacklist=TunableList(
                    description='Parent A must not have ANY of these traits in order to generate this outcome.', 
                    tunable=Trait.TunableReference(pack_safe=True)
                ), 
                parent_b_whitelist=TunableList(
                    description='Parent B must have ALL these traits in order to generate this outcome.', 
                    tunable=Trait.TunableReference(pack_safe=True)
                ), 
                parent_b_blacklist=TunableList(
                    description='Parent B must not have ANY of these traits in order to generate this outcome.', 
                    tunable=Trait.TunableReference(pack_safe=True)
                ), 
                outcomes=TunableList(
                    description='A weighted list of potential outcomes given that the requirements have been '
                                'satisfied.',
                    tunable=TunableTuple(
                        description='A weighted outcome. The weight is relative to other entries within this '
                                    'outcome set.',
                        weight=Tunable(
                            description='The relative weight of this outcome versus other outcomes in this same set.', 
                            tunable_type=float, default=1
                        ), 
                        trait=Trait.TunableReference(
                            description='The potential inherited trait.', 
                            allow_none=True, pack_safe=True
                        )
                    )
                )
            )
        ),
        'locked_args': {
            'injection_target_str': 'traits.trait_tracker:TraitTracker:TRAIT_INHERITANCE',
            'is_xml_usable_variant': True
        }
    }


# whims.whims_tracker.WhimsTracker

class SatisfactionStoreItems(ModuleVariantBase):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='A list of Sim based Tunable Rewards offered from the Satisfaction Store.',
            key_type=TunableReference(
                description='SimReward instance ID',
                manager=services.get_instance_manager(Types.REWARD),
                class_restrictions=('SimReward',),
                allow_none=False,
                pack_safe=True
            ),
            value_type=TunableTuple(
                award_type=TunableEnumEntry(WhimsTracker.WhimAwardTypes, WhimsTracker.WhimAwardTypes.MONEY),
                cost=Tunable(tunable_type=int, default=100)
            )
        ),
        'locked_args': {
            'injection_target_str': 'whims.whims_tracker:WhimsTracker:SATISFACTION_STORE_ITEMS',
            'is_xml_usable_variant': True
        }
    }


# buffs.buff.Buff

class BuffTarget(TuningRefVariantBase):
    FACTORY_TUNABLES = {
        'target_tuning_list': TunableList(
            description='List of buff tuning references.', 
            tunable=TunableReference(manager=services.get_instance_manager(Types.BUFF))
        )
    }


class BuffLootListTarget(BuffTarget):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='List of loot tuning references.', 
            tunable=LootActions.TunableReference(pack_safe=True)
        )
    }


class BuffLootOnInstance(BuffLootListTarget):
    FACTORY_TUNABLES = {
        'locked_args': {
            'injection_target_attr_str': '_loot_on_instance',
            'is_xml_usable_variant': True
        }
    }


class BuffLootOnAdd(BuffLootListTarget):
    FACTORY_TUNABLES = {
        'locked_args': {
            'injection_target_attr_str': '_loot_on_addition',
            'is_xml_usable_variant': True
        }
    }


class BuffLootOnRemove(BuffLootListTarget):
    FACTORY_TUNABLES = {
        'locked_args': {
            'injection_target_attr_str': '_loot_on_removal',
            'is_xml_usable_variant': True
        }
    }


# trait.traits.Trait

class TraitTarget(TuningRefVariantBase):
    FACTORY_TUNABLES = {
        'target_tuning_list': TunableList(
            description='List of trait tuning references.', 
            tunable=Trait.TunableReference(pack_safe=True)
        )
    }


class TraitLootOnAdd(TraitTarget):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='List of loot tuning references.', 
            tunable=LootActions.TunableReference(pack_safe=True)
        ),
        'locked_args': {
            'injection_target_attr_str': 'loot_on_trait_add',
            'is_xml_usable_variant': True
        }
    }


class TraitBuffs(TraitTarget):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='Buffs that should be added to the Sim whenever this trait is equipped.', 
            tunable=TunableBuffReference(pack_safe=True), 
            unique_entries=True
        ),
        'locked_args': {
            'injection_target_attr_str': 'buffs',
            'is_xml_usable_variant': True
        }
    }


class TraitBuffReplacements(TraitTarget):
    FACTORY_TUNABLES = {
        'item_list': TunableMapping(
            description='A mapping of buff replacement. If Sim has this trait on, whenever he get the buff tuned in'
                        ' the key of the mapping, it will get replaced by the value of the mapping.',
            key_type=TunableReference(
                description='Buff that will get replaced to apply on Sim by this trait.', 
                manager=services.buff_manager(), 
                reload_dependent=True, 
                pack_safe=True
            ), 
            value_type=TunableTuple(
                description='Data specific to this buff replacement.', 
                buff_type=TunableReference(
                    description='Buff used to replace the buff tuned as key.', 
                    manager=services.buff_manager(), 
                    reload_dependent=True, 
                    pack_safe=True
                ), 
                buff_reason=OptionalTunable(
                    description='If enabled, override the buff reason.', 
                    tunable=TunableLocalizedString(description='The overridden buff reason.')
                ), 
                buff_replacement_priority=TunableEnumEntry(
                    description="The priority of this buff replacement, relative to other replacements. Tune this to "
                                "be a higher value if you want this replacement to take precedence. e.g. (NORMAL) "
                                "trait_HatesChildren (buff_FirstTrimester -> buff_FirstTrimester_HatesChildren) "
                                "(HIGH) trait_Male (buff_FirstTrimester -> buff_FirstTrimester_Male) In this case, "
                                "both traits have overrides on the pregnancy buffs. However, we don't want males "
                                "impregnated by aliens that happen to hate children to lose their alien-specific "
                                "buffs. Therefore we tune the male replacement at a higher priority.",
                    tunable_type=TraitBuffReplacementPriority, 
                    default=TraitBuffReplacementPriority.NORMAL
                )
            )
        ),
        'locked_args': {
            'injection_target_attr_str': 'buff_replacements',
            'is_xml_usable_variant': True
        }
    }


# interactions.base.interaction.Interaction

class InteractionTarget(TuningRefVariantBase):
    FACTORY_TUNABLES = {
        'target_tuning_list': TunableList(
            description='List of interaction tuning references.', 
            tunable=TunableReference(
                description='Reference to an interaction tuning instance',
                manager=services.affordance_manager(),
                allow_none=False,
                pack_safe=True
            )
        )
    }


class InteractionStaticCommodities(InteractionTarget):
    FACTORY_TUNABLES = {
        'item_list': TunableList(
            description='The list of static commodities to which this affordance will advertise.', 
            tunable=TunableTuple(
                description='A single chunk of static commodity scoring data.', 
                static_commodity=TunableReference(
                    description='The type of static commodity offered by this affordance.', 
                    manager=services.get_instance_manager(sims4.resources.Types.STATIC_COMMODITY), 
                    pack_safe=True, 
                    reload_dependent=True
                ), 
                desire=Tunable(
                    description='The autonomous desire to fulfill this static commodity. This is how much of '
                                'the static commodity the Sim thinks they will get.  This is, of course, '
                                'a blatant lie.',
                    tunable_type=float, default=1
                )
            ), 
            tuning_group=GroupNames.AUTONOMY
        ),
        'locked_args': {
            'injection_target_attr_str': '_static_commodities',
            'is_xml_usable_variant': True
        }
    }


class InteractionFalseAdvertisements(InteractionTarget):
    FACTORY_TUNABLES = {
        'item_list': TunableStatisticAdvertisements(
            description='Fake advertisements make the interaction more enticing to autonomy by promising '
                        'things it will not deliver.',
            tuning_group=GroupNames.AUTONOMY
        ),
        'locked_args': {
            'injection_target_attr_str': '_false_advertisements',
            'is_xml_usable_variant': True
        }
    }


class InteractionHiddenFalseAdvertisements(InteractionTarget):
    FACTORY_TUNABLES = {
        'item_list': TunableStatisticAdvertisements(
            description="Fake advertisements that are hidden from the Sim.  These ads will not be used"
                        " when determining which interactions solve for a commodity, but it will be used"
                        " to calculate the final score. For example: You can tune the bubble bath to "
                        "provide hygiene as normal, but to also have a hidden ad for fun. Sims will "
                        "prefer a bubble bath when they want to solve hygiene and their fun is low, "
                        "but they won't choose to take a bubble bath just to solve for fun.",
            tuning_group=GroupNames.AUTONOMY
        ),
        'locked_args': {
            'injection_target_attr_str': '_hidden_false_advertisements',
            'is_xml_usable_variant': True
        }
    }
