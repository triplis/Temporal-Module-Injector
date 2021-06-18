import sims4.log
from sims4.collections import FrozenAttributeDict
from _sims4_collections import frozendict
from sims4.collections import _ImmutableSlotsBase
import sys

from temporal_module_injector import settings
from temporal_module_injector.factory_variants import InjectionTargetType

logger = sims4.log.Logger('TemporalModuleInjector')


def add_items_to_list(new_items):
    if not new_items.is_xml_usable_variant:
        logger.warn(
            '  new_items: {} is not supposed to be an available xml variant, ignoring its contents: {}', 
            type(new_items),
            new_items
        )
        return
    injection_target_type = new_items.get_injection_target_type()
    if injection_target_type == InjectionTargetType.MODULE_PATH:
        item_list = new_items.item_list
        injection_target_str = new_items.injection_target_str
        logger.info('  {}: adding items: {}', injection_target_str, item_list)
        # We expect that injection target str can be formatted
        # into module_name[0], class_name[1], and attr_name[2]
        injection_target_list = injection_target_str.split(':')
        injection_target_module_str = injection_target_list[0]
        injection_target_class_str = injection_target_list[1]
        injection_target_attr_str = injection_target_list[2]

        # We use sys.modules to get a reference to the given module
        # as it exists / has been loaded in the game.
        injection_target_class = getattr(
            sys.modules[injection_target_module_str], 
            injection_target_class_str
        )
        
        injected_result = add_list_items_by_type(
            item_list, 
            injection_target_str, 
            getattr(
                injection_target_class, 
                injection_target_attr_str
            )
        )

        # We want to use setattr to ensure that we are applying changes
        # to the reference of the module, not a copy of it. Modules are weird
        # and don't have dedicated tuning IDs you can call on to modify them.
        # This is why module injection usually involves importing the module and changing it directly,
        # but we can't depend on that as we're trying to be more generic in design.
        if injected_result is not None:
            setattr(
                injection_target_class, 
                injection_target_attr_str, 
                injected_result
            )
    elif injection_target_type == InjectionTargetType.TUNING_REF_ATTR:
        # This is more standard tuning injection, despite looking very vague.
        target_tuning_list = new_items.target_tuning_list
        item_list = new_items.item_list
        injection_target_attr_str = new_items.injection_target_attr_str
        logger.info('  {}: adding items: {} : at attr: {}', target_tuning_list, item_list, injection_target_attr_str)
        for tun in target_tuning_list:
            if not hasattr(tun, injection_target_attr_str):
                logger.warn(
                    '  {}: has no tunable attr: {}, this is probably due to class restrictions (ex: trying to '
                    'tune autonomy behavior in an interaction that has none, such as ImmediateSuperInteraction).',
                    tun,
                    injection_target_attr_str
                )
                continue
            injected_result = add_list_items_by_type(
                item_list,
                injection_target_attr_str,
                getattr(tun, injection_target_attr_str)
            )
            
            if injected_result is not None:
                setattr(
                    tun, 
                    injection_target_attr_str, 
                    injected_result
                )
    else:
        logger.warn(
            '  new_items: {} tried to use invalid or unprogrammed injection_target_type: {}', 
            new_items,  
            injection_target_type
        )


def add_list_items_by_type(item_list, injection_target_str, injection_target_ref):
    component_type = type(injection_target_ref)
    if component_type == tuple:
        if len(injection_target_ref) > 0:
            injection_target_ref += tuple(item_list,)
        else:
            injection_target_ref = tuple(item_list,)
    elif component_type == frozenset:
        injection_target_ref = frozenset(
            injection_target_ref.union(frozenset(item_list))
        )
    elif component_type == frozendict:
        injection_target_ref = frozendict(
            {**dict(injection_target_ref), **item_list}
        )
    elif component_type == FrozenAttributeDict:
        injection_target_ref = FrozenAttributeDict(
            {**dict(injection_target_ref), **item_list}
        )
    else:
        logger.warn(
            '  {}: type({}) not found in generic list injection options, this usually means a new injection needs'
            ' to be written',
            injection_target_str, 
            component_type
        )
        return None
    if settings.DEBUG_ON:
        logger.debug('  {}: with items added is now: {}', injection_target_str, injection_target_ref)
    return injection_target_ref


def add_items_to_existing_list_item(items, key_ref, key_str, value_str, injection_target):
    logger.info('  {}: adding items: {}', injection_target, items)
    # We expect that injection target str can be formatted
    # into module_name[0], class_name[1], and attr_name[2]
    injection_target_list = injection_target.split(':')
    injection_target_module_str = injection_target_list[0]
    injection_target_class_str = injection_target_list[1]
    injection_target_attr_str = injection_target_list[2]
    
    injection_target_class = getattr(
        sys.modules[injection_target_module_str], 
        injection_target_class_str
    )
    
    injected_result = modify_list_item_by_type(
        items, 
        injection_target, 
        getattr(
            injection_target_class, 
            injection_target_attr_str
        ),
        key_ref,
        key_str,
        value_str
    )
    
    if injected_result is not None:
        setattr(
            injection_target_class, 
            injection_target_attr_str, 
            injected_result
        )


def modify_list_item_by_type(new_items, injection_target_str, injection_target_ref, key_ref, key_str, value_str):
    component_type = type(injection_target_ref)
    if component_type == tuple:
        # Do type deduction voodoo to determine if it's a tuple of ImmutableSlots
        if isinstance(injection_target_ref[0], _ImmutableSlotsBase):
            for existing_item in injection_target_ref:
                if key_ref in getattr(existing_item, key_str):
                    index = injection_target_ref.index(existing_item)
                    # Change to list so we can modify the item
                    existing_as_list = list(injection_target_ref)
                    values = dict()
                    values[value_str] = getattr(existing_as_list[index], value_str) + tuple(new_items,)
                    existing_as_list[index] = existing_as_list[index].clone_with_overrides(**values)
                    # Change back into tuple when we're done
                    injection_target_ref = tuple(existing_as_list,)
                    if settings.DEBUG_ON:
                        logger.debug('  {}: with items added is now: {}', injection_target_str, injection_target_ref)
                    return injection_target_ref
    elif component_type == frozendict:
        existing_dict = dict(injection_target_ref)
        existing_value = existing_dict.get(key_ref)
        if existing_value is not None and isinstance(existing_value, tuple):
            modified_value = existing_value + tuple(new_items,)
            modified_dict = existing_dict
            modified_dict[key_ref] = modified_value
            injection_target_ref = frozendict(modified_dict)
            if settings.DEBUG_ON:
                logger.debug('  {}: with items added is now: {}', injection_target_str, injection_target_ref)
            return injection_target_ref
    return None
