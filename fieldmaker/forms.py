from django import forms
from django.forms.formsets import formset_factory, BaseFormSet

from resource import field_registry
from spec_widget import FormWidget

class FieldEntryForm(forms.Form):
    name = forms.CharField()
    field = forms.ChoiceField(choices=[])
    field_spec = forms.CharField(required=False, widget=FormWidget)
    widget = forms.ChoiceField(choices=[])
    widget_spec = forms.CharField(required=False, widget=FormWidget)
    
    def __init__(self, *args, **kwargs):
        super(FieldEntryForm, self).__init__(*args, **kwargs)
        self.populate_field_choices()
        self.populate_widget_choices()
        self.load_field_form()
        self.load_widget_form()
    
    def populate_field_choices(self):
        choices = field_registry.fields.keys()
        self.fields['field'].choices = [('', 'Select Field')] + zip(choices, choices)
    
    def populate_widget_choices(self):
        choices = field_registry.widgets.keys()
        self.fields['widget'].choices = [('', 'Select Widget')] + zip(choices, choices)
    
    def get_active_field_value(self, field_name):
        key = field_name
        if self.prefix:
            key = '%s-%s' % (self.prefix, key)
        
        value = mapping = None
        if field_name == 'widget':
            mapping = field_registry.widgets
        elif field_name == 'field':
            mapping = field_registry.fields
        
        if hasattr(self, 'cleaned_data') and value in self.cleaned_data:
            value = self.cleaned_data[field_name]
        elif self.data and key in self.data:
            value = self.data.get(key)
        if self.initial:
            value = self.initial.get(field_name)
        if value and mapping:
            value = mapping[value]
        return value
    
    def create_field_form(self):
        field = self.get_active_field_value('field')
        if not field: return
        form_cls = field.get_form()
        if self.prefix:
            prefix = '%s-field_spec' % self.prefix
        else:
            prefix = 'field_spec'
        
        self.fields['widget'].choices = field.widget_choices()
        self.fields['widget'].initial = field.default_widget
        return form_cls(data=self.data or None, prefix=prefix, initial=self.initial.get('field_spec'))
    
    def create_widget_form(self):
        field = self.get_active_field_value('widget')
        if not field: return
        form_cls = field.get_form()
        if self.prefix:
            prefix = '%s-widget_spec' % self.prefix
        else:
            prefix = 'widget_spec'
        return form_cls(data=self.data or None, prefix=prefix, initial=self.initial.get('widget_spec'))
    
    def load_field_form(self):
        self.field_form = self.create_field_form()
        self.fields['field_spec'].widget.form = self.field_form
    
    def load_widget_form(self):
        self.widget_form = self.create_widget_form()
        self.fields['widget_spec'].widget.form = self.widget_form
    
    def clean(self):
        self.load_field_form()
        
        self.load_widget_form()
        if self.field_form:
            if self.field_form.is_valid():
                self.cleaned_data['field_spec'] = self.field_form.cleaned_data
            else:
                raise forms.ValidationError('Please fix your field')
        if self.widget_form:
            if self.widget_form.is_valid():
                self.cleaned_data['widget_spec'] = self.widget_form.cleaned_data
            else:
                raise forms.ValidationError('Please fix your widget')
        return self.cleaned_data


class BaseFieldEntryFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.queryset = kwargs.pop('queryset', None)
        kwargs.pop('save_as_new', None)
        if self.instance:
            form_spec = self.instance.get_form_specification()
            initial = form_spec.data_to_field_form_set_initial(self.instance.get_data())
            kwargs.setdefault('initial', initial)
        super(BaseFieldEntryFormSet, self).__init__(*args, **kwargs)
    
    def save(self, commit=True):
        form_spec = self.instance.get_form_specification()
        data = form_spec.bound_field_form_set_to_data(self)
        self.instance.set_data(data)
        if commit:
            self.instance.save()
        
        #TODO populate the following
        #CONSIDER: django admin requires these attributes
        self.new_objects = list()
        self.changed_objects = list()
        self.deleted_objects = list()
    
    def get_queryset(self, request=None):
        #CONSIDER: django admin requires we return an iterable of model instances
        return [self.instance for i in range(len(self.instance.get_fields()))]
    
    def widget_forms(self): #helper function for displaying templated forms in admin
        forms = dict()
        for key, value in field_registry.widgets.iteritems():
            forms[key] = value.get_form()(prefix='prefix-widget_spec')
        return forms
    
    def field_forms(self):
        forms = dict()
        for key, value in field_registry.fields.iteritems():
            forms[key] = value.get_form()(prefix='prefix-field_spec')
        return forms

FieldEntryFormSet = formset_factory(FieldEntryForm, formset=BaseFieldEntryFormSet)
