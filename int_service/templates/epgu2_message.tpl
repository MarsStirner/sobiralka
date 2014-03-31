{% if params %}
{% for key, value in params.items() %}
<{{ key }}>
{% if key == 'params' %}
    {% for k, v in value.items() %}
        <{{ k }}>{{ v }}</{{ k }}>
    {% endfor %}
{% else %}
    {{ value }}
{% endif %}
</{{ key }}>
{% endfor %}
{% endif %}