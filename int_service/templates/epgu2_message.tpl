{% if params %}
{% for key, value in params.items() %}
<{{ key }}>
{% if key == 'params' %}
    {% for k, v in value.items() %}
        <param name="{{ k }}">{{ v }}</param>
    {% endfor %}
{% else %}
    {{ value }}
{% endif %}
</{{ key }}>
{% endfor %}
{% endif %}