import sims4.log
import services
from sims4.resources import Types
from sims4.tuning.instances import HashedTunedInstanceMetaclass
from sims4.tuning.tunable import HasTunableReference, TunableVariant, TunableList, TunableTuple, Tunable
import traceback

from temporal_module_injector import factory_variants
from temporal_module_injector import add_to_tuning

logger = sims4.log.Logger('TemporalModuleInjector')


class TemporalModuleInjector(
    HasTunableReference, 
    metaclass=HashedTunedInstanceMetaclass, 
    manager=services.get_instance_manager(Types.SNIPPET)
):
    INSTANCE_TUNABLES = {
        'add_items_to_list': TunableList(
            description='A list of new items and injection target pairings.',
            tunable=TunableTuple(
                new_items=TunableVariant(
                    pregnancy_origin_modifiers=factory_variants.PregnancyOriginModifiers.TunableFactory(),
                    baby_bassinet_definition_map=factory_variants.BabyBassinetDefinitionMap.TunableFactory(),
                    baby_cloth_state_map=factory_variants.BabyClothStateMap.TunableFactory(),
                    baby_default_bassinets=factory_variants.BabyDefaultBassinets.TunableFactory(),
                    buck_type_to_tracker_map=factory_variants.BuckTypeToTrackerMap.TunableFactory(),
                    club_traits=factory_variants.ClubTraits.TunableFactory(),
                    club_seeds_secondary=factory_variants.ClubSeedsSecondary.TunableFactory(),
                    bucket_scoring_rules=factory_variants.BucketScoringRules.TunableFactory(),
                    ensemble_priorities=factory_variants.EnsemblePriorities.TunableFactory(),
                    lifestyles=factory_variants.Lifestyles.TunableFactory(),
                    hidden_lifestyles=factory_variants.HiddenLifestyles.TunableFactory(),
                    default_away_action=factory_variants.DefaultAwayAction.TunableFactory(),
                    teleport_data_mapping=factory_variants.TeleportDataMapping.TunableFactory(),
                    trait_inheritance=factory_variants.TraitInheritance.TunableFactory(),
                    satisfaction_store_items=factory_variants.SatisfactionStoreItems.TunableFactory(),
                    buff_loot_on_instance=factory_variants.BuffLootOnInstance.TunableFactory(),
                    buff_loot_on_addition=factory_variants.BuffLootOnAdd.TunableFactory(),
                    buff_loot_on_removal=factory_variants.BuffLootOnRemove.TunableFactory(),
                    trait_loot_on_trait_add=factory_variants.TraitLootOnAdd.TunableFactory(),
                    trait_buffs=factory_variants.TraitBuffs.TunableFactory(),
                    trait_buff_replacements=factory_variants.TraitBuffReplacements.TunableFactory(),
                    interaction_static_commodities=factory_variants.InteractionStaticCommodities.TunableFactory(),
                    interaction_false_advertisements=factory_variants.InteractionFalseAdvertisements.TunableFactory(),
                    interaction_hidden_false_advertisements=factory_variants.InteractionHiddenFalseAdvertisements.TunableFactory()
                )
            )
        ),
        'add_items_to_existing_list_item': TunableList(
            description='A list of new items and injection target pairings.',
            tunable=TunableTuple(
                new_items=TunableVariant(
                    baby_default_bassinets=factory_variants.BabyDefaultBassinetsExistingTraitAsKey.TunableFactory(),
                    away_actions=factory_variants.AwayActionsExistingKey.TunableFactory(),
                )
            )
        )
    }

    @classmethod
    def _tuning_loaded_callback(cls):
        logger.info('Processing {}', str(cls))
        try:
            for entry in cls.add_items_to_list:
                if entry.new_items.item_list is None:
                    logger.warn('Tuning warning, missing or invalid items')
                else:
                    add_to_tuning.add_items_to_list(entry.new_items)
            for entry in cls.add_items_to_existing_list_item:
                if entry.new_items.item_list is None:
                    logger.warn('Tuning warning, missing or invalid items')
                else:
                    add_to_tuning.add_items_to_existing_list_item(
                        entry.new_items.item_list, 
                        entry.new_items.key_ref, 
                        entry.new_items.key_str, 
                        entry.new_items.value_str, 
                        entry.new_items.injection_target_str
                    )
        except:
            logger.error('Exception occurred processing TemporalModuleInjector tuning instance {}', str(cls))
            logger.error(traceback.format_exc())

    def __repr__(self):
        return '<TemporalModuleInjector:({})>'.format(self.__name__)

    def __str__(self):
        return '{}'.format(self.__name__)
