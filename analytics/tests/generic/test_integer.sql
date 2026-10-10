{% test integer(model, column_name) %}

select *
from {{ model }}
where mod({{ column_name }}, 1) != 0

{% endtest %}
