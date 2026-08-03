from abc import ABC, abstractmethod, abstractproperty
from typing import Callable
import requests
from deprecated import deprecated
from labfreed.labfreed_infrastructure import LabFREED_ValidationError
from labfreed.pac_attributes.api_data_models.response import Spec_Attribute, Spec_AttributeGroup
from labfreed.pac_cat.pac_cat import PAC_CAT


class AttributeGroupDataSource(ABC):

    def __init__(self, attribute_group_key:'str|list[str]', include_extensions:bool=False, is_static:bool=False,
                 uses_pac_cat_short_form:bool=True, pac_to_key:'Callable[[str], str]|None'=None):
        '''
        pac_to_key: maps a (canonicalized, where possible) subject_id onto whatever
            key/id this datasource actually needs - a local lookup key for a
            dict/spreadsheet-backed source, or the id a remote server understands for
            a proxying one. Defaults to using the canonicalized subject_id as-is. See
            _canonicalize/_lookup_keys for the shared canonicalize-then-map logic
            every datasource that keys off a PAC-CAT form can reuse.
        '''
        # a source whose groups aren't known ahead of time (e.g. a live remote proxy)
        # passes an empty list here - see attribute_group_keys and RemoteAttributeDataSource.
        self._attribute_group_keys = [attribute_group_key] if isinstance(attribute_group_key, str) else list(attribute_group_key)
        self._include_extensions = include_extensions
        self._is_static = is_static
        self._uses_pac_cat_short_form = uses_pac_cat_short_form
        self._pac_to_key = pac_to_key

    @property
    def is_static(self) -> bool:
        return self._is_static

    @property
    def attribute_group_keys(self) -> list[str]:
        '''Every group key this datasource can produce; empty if not known ahead of
        time (a live remote source only finds out once it's actually called).'''
        return self._attribute_group_keys

    @property
    def attribute_group_key(self):
        '''Convenience accessor for the common single-group case - the first (usually
        only) key. Multi-group sources should use attribute_group_keys instead.'''
        return self._attribute_group_keys[0]

    @property
    @abstractmethod
    def provides_attributes(self):
        pass

    @abstractmethod
    def attributes(self, subject_id: str) -> 'Spec_AttributeGroup|list[Spec_AttributeGroup]|None':
        pass

    def _canonicalize(self, subject_id: str) -> str:
        '''Best-effort PAC-CAT canonicalization, so pac_to_key gets a normalized form
        to work from regardless of how the id happened to be written on the wire -
        falls back to the raw subject_id unchanged if it doesn't parse as a valid
        PAC-CAT (e.g. a trailing-slash id, or a generic non-PAC-ID IRI).'''
        try:
            p = PAC_CAT.from_url(subject_id, suppress_validation_errors=True)
            if p.is_valid:
                return p.to_url(use_short_notation=self._uses_pac_cat_short_form, include_extensions=self._include_extensions)
        except LabFREED_ValidationError:
            pass  # might as well try to match the original input
        return subject_id

    def _lookup_keys(self, subject_id: str) -> list[str]:
        '''Keys to try, in order, for a *local* lookup (dict/spreadsheet row): the
        canonicalized form (through pac_to_key, if set) first, then the raw
        subject_id the same way if canonicalizing actually changed something -
        deduplicated. Canonicalizing can drop information a lookup is still keyed by
        (e.g. a tolerated trailing '/' - see design-choices.md "Empty id segments"),
        hence the fallback. Only sensible when trying a key is cheap (a local dict/
        row lookup) - a source with a live call per attempt (RemoteAttributeDataSource)
        canonicalizes once via _canonicalize() and sends a single request instead.'''
        canonical = self._canonicalize(subject_id)
        keys = [self._pac_to_key(canonical) if self._pac_to_key else canonical]
        if canonical != subject_id:
            raw_key = self._pac_to_key(subject_id) if self._pac_to_key else subject_id
            if raw_key not in keys:
                keys.append(raw_key)
        return keys


class Spec_Dict_DataSource(AttributeGroupDataSource):
    def __init__(self, data:dict[str, dict[str, Spec_Attribute]], *args, **kwargs):
        if not all([isinstance(e, dict) for e in data.values()]):
            raise ValueError('Invalid data')

        self._data = data
        super().__init__(*args, **kwargs)


    @property
    def provides_attributes(self):
        return list(set([a.key for attributes in self._data.values() for a in attributes.values()]))


    def attributes(self, subject_id: str) -> Spec_AttributeGroup:
        attributes = None
        for key in self._lookup_keys(subject_id):
            attributes = self._data.get(key)
            if attributes:
                break
        if not attributes:
            if 'default' in self._data.keys():
                attributes = self._data.get('default', None)
            else:
                return None

        return Spec_AttributeGroup(group_key=self.attribute_group_key,
                              attributes=attributes)


@deprecated("Use Spec_Dict_DataSource")
class Dict_DataSource(Spec_Dict_DataSource):
    '''Deprecated alias for Spec_Dict_DataSource - kept for backward compatibility.'''


class RemoteAttributeDataSource(AttributeGroupDataSource):
    '''Proxies attributes from a remote PAC-ID-Attributes-compliant server (e.g. an
    external, third-party attribute service), passing through whatever groups that
    server's response actually contains for a given subject_id.

    The remote server's own group breakdown is server/product-line-defined, so it
    isn't declared ahead of time (attribute_group_keys is empty) - the request handler
    always calls this source and filters its result afterward instead of pre-filtering
    on a declared key, see AttributeServerRequestHandler._get_attributes_for_pac_id.
    '''

    def __init__(self, base_url:str, session:requests.Session|None=None,
                 language_preferences:list[str]|str='en',
                 pac_to_key:'Callable[[str], str]|None'=None):
        '''
        pac_to_key: same concept as Dict_DataSource/_BaseExcelAttributeDataSource's
            pac_to_key - maps a (canonicalized) subject_id onto the id this datasource
            actually needs, here the id the remote server understands. Use this when
            this datasource is a facade in front of a different catalog - e.g. an
            issuer whose own PAC-IDs need mapping onto the underlying id scheme the
            remote server was actually built for. Defaults to sending the
            canonicalized subject_id unchanged (see AttributeGroupDataSource._canonicalize).
            Only the request sent to the remote server is affected; the response is
            still matched back to the original subject_id by the caller
            (AttributeServerRequestHandler builds the returned AttributesOfItem.id
            from the original pac_url, not the mapped one), so callers of this
            datasource never see the mapped id. Unlike the dict/excel sources, only
            one id is ever tried - a live call per attempt isn't worth the extra
            request, so there's no raw-subject_id fallback attempt here.
        '''
        # lazy import: client.client imports server.server, which imports this module -
        # importing it at module level here would be a circular import.
        from labfreed.pac_attributes.client.client import AttributeClient, http_attribute_request_default_callback_factory

        self._base_url = base_url.rstrip('/')
        self._language_preferences = [language_preferences] if isinstance(language_preferences, str) else language_preferences
        callback = http_attribute_request_default_callback_factory(session or requests.Session())
        self._client = AttributeClient(http_post_callback=callback)
        super().__init__(attribute_group_key=[], pac_to_key=pac_to_key)

    @property
    def provides_attributes(self):
        # the remote server's attribute keys are defined by that server, not known
        # ahead of time - nothing to declare for the translation-completeness check.
        return []

    def attributes(self, subject_id: str) -> list[Spec_AttributeGroup]:
        canonical = self._canonicalize(subject_id)
        remote_subject_id = self._pac_to_key(canonical) if self._pac_to_key else canonical
        return list(self._client.get_attributes(self._base_url, subject_id=remote_subject_id,
                                                  language_preferences=self._language_preferences))
        
        
        

    
    
