from rest_framework import mixins, viewsets


class ListRetrieve(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin, viewsets.GenericViewSet):
    ...


class CreateDestroy(mixins.CreateModelMixin,
                    mixins.DestroyModelMixin, viewsets.GenericViewSet):
    ...
