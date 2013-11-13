import datetime
from haystack import indexes
from popit_resolver.models import EntityName

class EntityNameIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.CharField(
        document=True, 
        model_attr='name')
    start_date = indexes.DateField(
        model_attr='start_date', 
        null=True)
    end_date = indexes.DateField(
        model_attr='end_date', 
        null=True)
    person = indexes.IntegerField(
        model_attr='person__id', 
        null=True)

    def get_model(self):
        return EntityName

    #def index_queryset(self, using=None):
        #"""Used when the entire index for model is updated."""
        #return self.get_model().objects # .filter(pub_date__lte=datetime.datetime.now())
