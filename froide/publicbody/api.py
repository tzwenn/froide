from django.conf.urls.defaults import url
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404

from haystack.query import SearchQuerySet
from tastypie.resources import ModelResource
from tastypie.paginator import Paginator as TastyPaginator
from tastypie import fields, utils
from tastypie.authorization import DjangoAuthorization

from froide.helper.api_utils import AnonymousGetAuthentication

from .models import PublicBody, Jurisdiction, FoiLaw


class JurisdictionResource(ModelResource):
    class Meta:
        # allowed_methods = ['get']
        queryset = Jurisdiction.objects.get_visible()
        resource_name = 'jurisdiction'
        fields = ['name', 'rank', 'description', 'slug']
        authentication = AnonymousGetAuthentication()
        authorization = DjangoAuthorization()


class FoiLawResource(ModelResource):
    combined = fields.ToManyField('froide.publicbody.api.FoiLawResource',
        'combined')
    jurisdiction = fields.ToOneField(JurisdictionResource,
        'jurisdiction', null=True)
    mediator = fields.ToOneField('froide.publicbody.api.PublicBodyResource',
        'mediator', null=True)

    class Meta:
        queryset = FoiLaw.objects.all()
        resource_name = 'law'
        fields = ['name', 'slug', 'description', 'long_description',
            'created', 'updated', 'request_note', 'meta',
            'combined', 'letter_start', 'letter_end', 'jurisdiction',
            'priority', 'url', 'max_response_time',
            'max_response_time_unit', 'refusal_reasons', 'mediator'
        ]
        authentication = AnonymousGetAuthentication()
        authorization = DjangoAuthorization()


class PublicBodyResource(ModelResource):
    laws = fields.ToManyField(FoiLawResource, 'laws',
        full=True)
    jurisdiction = fields.ToOneField(JurisdictionResource,
        'jurisdiction', full=True, null=True)
    parent = fields.ToOneField('froide.publicbody.api.PublicBodyResource',
        'parent', null=True)
    root = fields.ToOneField('froide.publicbody.api.PublicBodyResource',
        'parent', null=True)

    class Meta:
        queryset = PublicBody.objects.all()
        resource_name = 'publicbody'
        fields = ['name', 'slug', 'other_names',
            'description', 'url', 'parent', 'root',
            'depth', 'classification', 'classification_slug',
            'email', 'contact', 'address', 'website_dump',
            'request_note', 'number_of_requests',
            'laws', 'jurisdiction'
        ]
        paginator_class = TastyPaginator
        authentication = AnonymousGetAuthentication()
        authorization = DjangoAuthorization()

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/search%s$" % (self._meta.resource_name, utils.trailing_slash()), self.wrap_view('get_search'), name="api_get_search"),
        ]

    def get_search(self, request, **kwargs):
        self.method_check(request, allowed=['get'])

        # Do the query.
        sqs = SearchQuerySet().models(PublicBody).load_all().auto_query(request.GET.get('q', ''))
        paginator = Paginator(sqs, 20)

        try:
            page = paginator.page(int(request.GET.get('page', 1)))
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        for result in page.object_list:
            bundle = self.build_bundle(obj=result.object, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)

        object_list = {
            'objects': objects,
        }

        return self.create_response(request, object_list)
