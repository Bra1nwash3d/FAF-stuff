import persistent.dict
import transaction


class Item(persistent.Persistent):
    """ An item, given to a ChatEntity """

    def __init__(self, id_: int, item_id: str, name: str, description: str, visible: bool=True):
        super(Item, self).__init__()
        self.id = id_
        self.item_id = item_id
        self.name = name
        self.description = description
        self.visible = visible
        self.save()

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        # self.x = self.__dict__.get('x', 'oh a new self.x!')
        pass

    def save(self):
        self._p_changed = True
        transaction.commit()

    def has_id(self, id_: str, is_name=False):
        if is_name:
            return id_ == self.name
        return id_ == self.item_id

    @staticmethod
    def split_visible_hidden(items: list) -> ([], []):
        visible, hidden = [], []
        for item in items:
            if item.visible:
                visible.append(item)
            else:
                hidden.append(item)
        return visible, hidden


class UsableItem(Item):
    """ A consumable item, given to a ChatEntity, consumed on use. """

    def __init__(self, id_: int, item_id: str, name: str, description: str, visible: bool=True, uses: int=1):
        super(UsableItem, self).__init__(id_, item_id, name, description, visible)
        self.uses = uses
        self.save()

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        super(UsableItem, self).migrate()
        # self.x = self.__dict__.get('x', 'oh a new self.x!')
        pass

    def use(self, user, target) -> str:
        """ uses an item from user on target, both are ChatEntities, but due to circular dependencies...
            updates 'uses' count, saves, and informs the user of usage
        """
        self.uses -= 1
        self.save()
        user.update_usable_items()
        return 'Used item!'

    def merge(self, other) -> bool:
        """ merge uses of the other item into this, 'consume' the other item thereby, return if it worked """
        if other is None:
            return True
        if other.item_id != self.item_id:
            return False
        self.uses += other.uses
        self.visible = self.visible or other.visible
        self.save()
        other.uses = 0
        other.save()
