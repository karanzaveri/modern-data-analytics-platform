{% macro cohort_observation_end_date() %}
    {% set cutoff = var('cohort_observation_end_date', '2018-08-31') %}

    {% if cutoff is not string or not modules.re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', cutoff) %}
        {{ exceptions.raise_compiler_error('cohort_observation_end_date must be a quoted YYYY-MM-DD month-end date.') }}
    {% endif %}

    {% set year = cutoff[0:4] | int %}
    {% set month = cutoff[5:7] | int %}
    {% set day = cutoff[8:10] | int %}
    {% if year < 1 or month < 1 or month > 12 %}
        {{ exceptions.raise_compiler_error('cohort_observation_end_date must be a valid YYYY-MM-DD month-end date.') }}
    {% endif %}

    {% set leap_year = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) %}
    {% set month_lengths = [31, 29 if leap_year else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] %}
    {% if day != month_lengths[month - 1] %}
        {{ exceptions.raise_compiler_error('cohort_observation_end_date must be a calendar month-end; partial activity months are not supported.') }}
    {% endif %}

    {{ return(cutoff) }}
{% endmacro %}
