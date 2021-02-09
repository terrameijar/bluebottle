from rest_framework import permissions
from bluebottle.utils.permissions import IsOwner, BasePermission


class SlotParticipantPermission(IsOwner):
    def has_object_action_permission(self, action, user, obj):
        return user == obj.participant.user

    def has_action_permission(self, action, user, model_cls):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user == obj.participant.user


class DateSlotActivityStatusPermission(BasePermission):
    def has_object_action_permission(self, action, user, obj):
        return action == 'GET' or obj.activity.status in ['draft', 'needs_work', 'submitted']

    def has_action_permission(self, action, user, model_cls):
        return True

    def has_object_permission(self, request, view, obj):
        return request.method == 'GET' or obj.activity.status in ['draft', 'needs_work', 'submitted']


class ParticipantDocumentPermission(permissions.DjangoModelPermissions):

    def has_object_permission(self, request, view, obj):
        if not obj:
            return True
        if obj and request.user in [
            obj.user,
            obj.activity.owner,
            obj.activity.initiative.activity_manager
        ]:
            return True
        return False
