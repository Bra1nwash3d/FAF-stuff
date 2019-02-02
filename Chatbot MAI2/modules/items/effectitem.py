from modules.items.item import UsableItem
from modules.effects import PointsEffect
from modules.utils import get_logger

logger = get_logger('effectitem')


class EffectItem(UsableItem):
    """ A consumable item, given to a ChatEntity, grants an effect on use. """

    def __init__(self, id_: int, item_id: str, name: str, description: str, effect: PointsEffect, visible: bool=True,
                 uses: int=1):
        super(EffectItem, self).__init__(id_, item_id, name, description, visible, uses)
        self.effect = effect
        logger.debug('Created EffectItem %s/%s' % (item_id, name))
        self.save()

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        super(EffectItem, self).migrate()
        # self.x = self.__dict__.get('x', 'oh a new self.x!')
        pass

    def use(self, user, target) -> str:
        """ apply an effect on the target """
        logger.debug('Using item %s/%s on user %s/%s' % (self.item_id, self.name, user.id, user.nick))
        target.add_points_effect(self.effect)
        super().use(user, target)
        user.update_usable_items()
        return 'Used %s on %s!' % (self.name, target.nick)

    def to_str(self, show_hidden=False):
        """ used for listing items in chat """
        if not (self.visible or show_hidden):
            return 'Unknown item.'
        return '{name}: applies {effect} ({effects}), {n} uses remaining'.format(**{
            'name': self.name,
            'effect': self.effect.name,
            'effects': self.effect.affects_str(),
            'n': self.uses,
        })
