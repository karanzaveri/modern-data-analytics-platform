{% macro calculate_growth_pct(current_value, previous_value, current_period, previous_period) %}

    case
        when {{ previous_value }} is not null
         and date_diff(
                {{ current_period }},
                {{ previous_period }},
                month
             ) = 1
        then round(
            safe_divide(
                {{ current_value }} - {{ previous_value }},
                {{ previous_value }}
            ) * 100,
            2
        )
    end

{% endmacro %}