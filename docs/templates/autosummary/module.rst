{{ fullname | escape | underline}}

.. automodule:: {{ fullname }}

   {% block classes %}
   {% if classes + exceptions %}
   .. rubric:: Classes

   .. autosummary::
      :toctree:
   {% for item in classes + exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if functions %}
   .. rubric:: Functions

   .. autosummary::
      :toctree: api
   {% for item in functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

{% block modules %}
{% if modules %}
.. rubric:: Modules

.. autosummary::
   :toctree:
   :recursive:
{% for item in modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
